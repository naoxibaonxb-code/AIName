import asyncio
import json
import logging
import re
import uuid
from typing import Any, Literal, TypedDict

from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from psycopg_pool import AsyncConnectionPool

from settings.config import settings
from schemas.name import NameIn, FeedBackIn
from schemas.agent import NameResultSchema
from core.long_term_memory import (
    close_memory_store,
    format_memory_context,
    initialize_memory_store,
    remember_text,
    retrieve_memories,
)
from core.rag_service import retrieve_user_knowledge
from core.tools import check_com_domain

logger = logging.getLogger(__name__)
NAMING_BUSY_MESSAGE = "当前访问人数较多，生成服务暂时繁忙，请稍后重新尝试。"
NAMING_TIMEOUT_SECONDS = 75


class NamingServiceError(RuntimeError):
    """模型超时、无有效结果或上游服务不可用。"""


def empty_token_usage() -> dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _extract_token_usage(result: Any) -> dict[str, int]:
    raw = result.get("raw") if isinstance(result, dict) else result
    usage = getattr(raw, "usage_metadata", None) or {}
    metadata = getattr(raw, "response_metadata", None) or {}
    provider_usage = metadata.get("token_usage") or metadata.get("usage") or {}
    prompt = usage.get("input_tokens", provider_usage.get("prompt_tokens", 0))
    completion = usage.get("output_tokens", provider_usage.get("completion_tokens", 0))
    total = usage.get("total_tokens", provider_usage.get("total_tokens", 0))
    return {
        "prompt_tokens": int(prompt or 0),
        "completion_tokens": int(completion or 0),
        "total_tokens": int(total or (prompt or 0) + (completion or 0)),
    }


def _add_token_usage(total: dict[str, int], current: dict[str, int]) -> None:
    for key in total:
        total[key] += current.get(key, 0)


class WorkFlowState(TypedDict):
    user_id: int
    category: str
    surname: str
    gender: str
    length: str
    other: str
    exclude: list[str]
    use_bazi: bool
    birth_info: str
    brand_tone: str
    target_audience: str
    competitors: str
    ip_setting: str
    ip_personality: str
    memory_context: str
    feedback: str
    history_names: str
    final_output: dict[str, Any]
    token_usage: dict[str, int]


llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0.5,
    timeout=45,
)

structured_llm = llm.with_structured_output(
    NameResultSchema,
    method="json_mode",
    include_raw=True,
)


JSON_OUTPUT_INSTRUCTION = """
输出要求：只返回一个合法 JSON 对象，不要使用 Markdown 代码块，也不要添加解释文字。
JSON 必须严格遵循以下结构：
{"names":[{"name":"名称","reference":"出处或创意来源","moral":"含义与寓意","analysis":"音律、五行、品牌调性或角色适配等推演说明","domain":"企业名对应的.com域名，非企业名可为空"}]}
必须返回 5 个名字，所有字段都使用以上英文键名。
"""


def build_length_instruction(category: str, length: str) -> str:
    if not length or length == "不限":
        return "不强制限制字数，但要符合中文日常使用习惯，避免过长、拗口。"

    if category == "人名":
        rules = {
            "单字": "名字部分只取 1 个汉字，不含姓氏。",
            "单字名": "名字部分只取 1 个汉字，不含姓氏。",
            "两字": "名字部分取 2 个汉字，不含姓氏。",
            "双字名": "名字部分取 2 个汉字，不含姓氏。",
        }
        return rules.get(length, f"名字部分按“{length}”理解，不含姓氏。")

    if category == "企业名":
        rules = {
            "两字": "企业名主体建议 2 个汉字，简短有记忆点。",
            "五字": "企业名主体控制在 5 个汉字左右，不能冗长。",
            "2-4字（推荐）": "企业名主体控制在 2 到 4 个汉字，优先简短、好读、好传播。",
            "3-5字": "企业名主体控制在 3 到 5 个汉字，允许更完整表达行业感。",
        }
        return rules.get(length, f"企业名主体按“{length}”控制，避免过长。")

    rules = {
        "单字": "宠物名控制在 1 个汉字，亲切好叫。",
        "两字": "宠物名控制在 2 个汉字，亲切好叫。",
        "1-2字": "宠物名控制在 1 到 2 个汉字，短促、好叫、容易记。",
        "2-3字": "宠物名控制在 2 到 3 个汉字，可爱、有画面感。",
    }
    if category == "虚拟IP":
        ip_rules = {
            "1-2字": "昵称控制在 1 到 2 个汉字，方便传播和二创。",
            "2-3字": "昵称控制在 2 到 3 个汉字，兼顾记忆点和角色感。",
        }
        return ip_rules.get(length, f"虚拟 IP 名称按“{length}”控制，避免过长。")
    return rules.get(length, f"宠物名按“{length}”控制，避免过长。")


def _load_json_payload(content: str) -> Any:
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    code_block = re.search(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.S)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    object_start, object_end = content.find("{"), content.rfind("}")
    if 0 <= object_start < object_end:
        try:
            return json.loads(content[object_start:object_end + 1])
        except json.JSONDecodeError:
            pass

    list_start, list_end = content.find("["), content.rfind("]")
    if 0 <= list_start < list_end:
        return json.loads(content[list_start:list_end + 1])
    raise json.JSONDecodeError("No JSON payload found", content, 0)


def _parse_raw_model_result(result: Any) -> NameResultSchema | None:
    if isinstance(result, NameResultSchema):
        return result
    if not isinstance(result, dict):
        return None

    parsed = result.get("parsed")
    if isinstance(parsed, NameResultSchema):
        return parsed

    raw = result.get("raw")
    content = getattr(raw, "content", "")
    if not isinstance(content, str) or not content.strip():
        return None

    try:
        payload = _load_json_payload(content)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    raw_names = payload.get("names") if isinstance(payload, dict) else payload
    if not isinstance(raw_names, list):
        return None

    names = []
    for item in raw_names:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        names.append({
            "name": item["name"],
            "reference": (
                item.get("reference") or item.get("source")
                or item.get("origin") or "文化与行业意象"
            ),
            "moral": (
                item.get("moral") or item.get("meaning")
                or item.get("explanation") or "寓意积极美好"
            ),
            "analysis": (
                item.get("analysis") or item.get("reasoning")
                or item.get("report") or ""
            ),
            "domain": item.get("domain") or item.get("domain_name") or "",
            "domain_status": item.get("domain_status", "正在查询..."),
        })
    return NameResultSchema.model_validate({"names": names}) if names else None


async def invoke_naming_model(prompt: str) -> tuple[NameResultSchema, dict[str, int]]:
    last_error = None
    token_usage = empty_token_usage()
    full_prompt = f"{prompt}\n{JSON_OUTPUT_INSTRUCTION}"
    for attempt in range(1, 4):
        try:
            result = await structured_llm.ainvoke(full_prompt)
            _add_token_usage(token_usage, _extract_token_usage(result))
            response = _parse_raw_model_result(result)
            if response and response.names:
                return response, token_usage
            parsing_error = result.get("parsing_error") if isinstance(result, dict) else None
            logger.warning(
                "第 %s 次模型响应无法解析: %s",
                attempt,
                type(parsing_error).__name__ if parsing_error else "empty result",
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            last_error = exc
            logger.warning("第 %s 次大模型调用失败: %s", attempt, type(exc).__name__)
        if attempt < 3:
            await asyncio.sleep(attempt)

    logger.error(
        "大模型连续三次未返回有效命名结果，最后错误类型: %s",
        type(last_error).__name__ if last_error else "empty result",
    )
    error = NamingServiceError(NAMING_BUSY_MESSAGE)
    error.token_usage = token_usage
    raise error from last_error


async def supervisor_node(_: WorkFlowState) -> dict[str, Any]:
    return {}


async def memory_context_for(state: WorkFlowState) -> str:
    query = " ".join([
        state.get("category", ""),
        state.get("surname", ""),
        state.get("gender", ""),
        state.get("length", ""),
        state.get("other", "") or "",
        state.get("birth_info", "") or "",
        state.get("brand_tone", "") or "",
        state.get("target_audience", "") or "",
        state.get("competitors", "") or "",
        state.get("ip_setting", "") or "",
        state.get("ip_personality", "") or "",
        state.get("feedback", "") or "",
    ])
    user_id = state.get("user_id")
    if not user_id:
        return format_memory_context([])
    try:
        memories = await retrieve_memories(
            user_id,
            state.get("category", "通用"),
            query,
        )
    except Exception:
        logger.warning("长期记忆上下文加载失败，已跳过", exc_info=True)
        memories = []
    return format_memory_context(memories)


async def human_naming_node(state: WorkFlowState) -> dict[str, Any]:
    """人名专家节点"""
    category = state.get("category", "人名")
    length = state.get("length", "不限")
    exclude = state.get("exclude") or []
    length_instruction = build_length_instruction(category, length)
    memory_context = await memory_context_for(state)
    bazi_instruction = "用户未启用八字五行，请不要编造出生盘。"
    if state.get("use_bazi"):
        bazi_instruction = f"""用户启用了八字五行参考。
    【出生与命理信息】: {state.get('birth_info') or '用户未填写详细出生信息'}
    请基于用户提供的信息做审慎、非绝对化的五行取向建议；信息不足时只做偏旁、意象和寓意层面的温和参考，不要编造精确八字。"""
    prompt = f"""你是一位精通汉语言文学与传统文化的命名专家。请为用户创作富有文化底蕴的人名
    【姓氏】: {state.get('surname') or '未填写'}
    【性别倾向】: {state.get('gender') or '不限'}
    【名字长度】: {length}。{length_instruction}
    【其它具体要求】: {state.get('other') or '无'}
    【避讳排除字】: {'、'.join(exclude) if exclude else '无'}
    【命理参考】: {bazi_instruction}
    【长期偏好记忆】
    {memory_context}
    原则：平仄协调，优先从《诗经》《楚辞》或唐诗宋词中汲取灵感。analysis 字段需说明音律、出处适配、寓意层次；如启用八字五行，也说明五行意象如何融入。请给出 5 个候选方案。"""
    response, token_usage = await invoke_naming_model(prompt)
    return {"final_output": response.model_dump(mode="json"), "token_usage": token_usage}


async def company_naming_node(state: WorkFlowState) -> dict[str, Any]:
    """企业品牌节点"""
    current_user_id = state.get("user_id", 0)
    category = state.get("category", "企业名")
    length = state.get("length", "不限")
    other = state.get("other") or "企业品牌"
    exclude = state.get("exclude") or []
    search_query = f"{other} 品牌命名规范 行业词汇"
    memory_context = await memory_context_for(state)
    rag_context = await asyncio.to_thread(
        retrieve_user_knowledge, search_query, current_user_id
    )
    feedback_instruction = ""
    if state.get("feedback") and state.get("history_names"):
        feedback_instruction = f"""
            警告：这是一次微调请求！
            【上一轮你生成的名字是】：{state['history_names']}
            【用户的最新修改意见】：{state['feedback']}
            请严格保留上一轮中用户满意的部分，仅针对【修改意见】对这 5 个名字进行迭代优化！绝不能抛弃历史记录重新随机生成！
        """
    length_instruction = build_length_instruction(category, length)
    prompt = f"""你是一位精通商业品牌传播与工商命名的资深顾问。请创作符合商业规范的公司名。
    【用户需求】
    行业或核心诉求: {other}
    品牌调性: {state.get('brand_tone') or '未填写'}
    目标客群: {state.get('target_audience') or '未填写'}
    竞品或相似品牌: {state.get('competitors') or '未填写'}
    名字长度: {length}。{length_instruction}
    避讳排除字: {'、'.join(exclude) if exclude else '无'}
    【用户的专属私有知识库参考】
    {rag_context}
    【长期偏好记忆】
    {memory_context}
    {feedback_instruction}
    核心纪律（最高优先级）：
    1. 必须遵守知识库和修改意见。
    2. 你必须为每个公司名构思一个绝佳的 .com 英文或拼音域名，填入 domain 字段（例如：hema.com 或 greenearth.com）。
    3. analysis 字段需说明品牌调性匹配、行业差异化、传播记忆点和竞品避让思路。
    请给出 5 个候选方案。"""
    response, token_usage = await invoke_naming_model(prompt)
    tasks = [
        check_com_domain(n.domain)
        if n.domain else asyncio.sleep(0, result="未提供域名")
        for n in response.names
    ]
    statuses = await asyncio.gather(*tasks, return_exceptions=True)

    for n, status in zip(response.names, statuses):
        n.domain_status = "查询失败" if isinstance(status, Exception) else status

    names_str = ", ".join(n.name for n in response.names)
    return {
        "final_output": response.model_dump(),
        "history_names": names_str,
        "token_usage": token_usage,
    }


async def pet_naming_node(state: WorkFlowState) -> dict[str, Any]:
    """宠物起名节点"""
    category = state.get("category", "宠物名")
    length = state.get("length", "不限")
    exclude = state.get("exclude") or []
    length_instruction = build_length_instruction(category, length)
    memory_context = await memory_context_for(state)
    prompt = f"""你是一位充满创意的宠物达人。请为用户的宠物起一些富有灵性的名字。
    【宠物特征/性格】: {state.get('other') or '未填写'}
    【名字长度】: {length}。{length_instruction}
    【避讳排除字】: {'、'.join(exclude) if exclude else '无'}
    【长期偏好记忆】
    {memory_context}
    原则：亲切好记、富有画面感或软萌感。analysis 字段需说明叫唤顺口度、性格贴合和记忆点。请给出 5 个候选方案。"""
    response, token_usage = await invoke_naming_model(prompt)
    return {"final_output": response.model_dump(), "token_usage": token_usage}


async def ip_naming_node(state: WorkFlowState) -> dict[str, Any]:
    """虚拟 IP 节点"""
    category = state.get("category", "虚拟IP")
    length = state.get("length", "不限")
    exclude = state.get("exclude") or []
    length_instruction = build_length_instruction(category, length)
    memory_context = await memory_context_for(state)
    prompt = f"""你是一位擅长角色设定、游戏与内容 IP 命名的创意策划。请为虚拟 IP 创作名字。
    【角色用途或内容方向】: {state.get('other') or '未填写'}
    【世界观/角色设定】: {state.get('ip_setting') or '未填写'}
    【性格、人设或口头禅】: {state.get('ip_personality') or '未填写'}
    【名字长度】: {length}。{length_instruction}
    【避讳排除字】: {'、'.join(exclude) if exclude else '无'}
    【长期偏好记忆】
    {memory_context}
    原则：名字要有辨识度、易传播、适合社媒头像/短视频账号/游戏或小说角色使用。analysis 字段需说明角色辨识度、传播性和世界观适配。请给出 5 个候选方案。"""
    response, token_usage = await invoke_naming_model(prompt)
    return {"final_output": response.model_dump(), "token_usage": token_usage}


def route_by_category(state: WorkFlowState) -> Literal["human", "company", "pet", "ip"]:
    category_map = {"人名": "human", "企业名": "company", "宠物名": "pet", "虚拟IP": "ip"}
    return category_map.get(state.get("category", "人名"), "human")


workflow = StateGraph(WorkFlowState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("human", human_naming_node)
workflow.add_node("company", company_naming_node)
workflow.add_node("pet", pet_naming_node)
workflow.add_node("ip", ip_naming_node)

workflow.set_entry_point("supervisor")
workflow.add_conditional_edges(
    "supervisor",
    route_by_category,
    {"human": "human", "company": "company", "pet": "pet", "ip": "ip"},
)

workflow.add_edge("human", END)
workflow.add_edge("company", END)
workflow.add_edge("pet", END)
workflow.add_edge("ip", END)

connection_pool = AsyncConnectionPool(settings.pg_url, max_size=10, open=False)
naming_graph = None
checkpoint_saver: AsyncPostgresSaver | None = None


async def initialize_naming_workflow() -> None:
    global checkpoint_saver, naming_graph
    await connection_pool.open(wait=True, timeout=10)
    try:
        await initialize_memory_store()
    except Exception:
        logger.warning("长期记忆初始化异常，命名工作流继续以无记忆模式启动", exc_info=True)
    checkpoint_saver = AsyncPostgresSaver(connection_pool)
    await checkpoint_saver.setup()
    naming_graph = workflow.compile(checkpointer=checkpoint_saver)


async def close_naming_workflow() -> None:
    await close_memory_store()
    if not connection_pool.closed:
        await connection_pool.close()


async def delete_naming_thread(thread_id: str) -> None:
    if checkpoint_saver is not None and not connection_pool.closed:
        await checkpoint_saver.adelete_thread(thread_id)


async def run_naming_graph(data: dict[str, Any], config: dict[str, Any]):
    if naming_graph is None:
        raise NamingServiceError(NAMING_BUSY_MESSAGE)
    try:
        final_state = await asyncio.wait_for(
            naming_graph.ainvoke(data, config=config),
            timeout=NAMING_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        logger.warning("命名工作流执行超过 %s 秒", NAMING_TIMEOUT_SECONDS)
        raise NamingServiceError(NAMING_BUSY_MESSAGE) from exc
    except NamingServiceError:
        raise
    except Exception as exc:
        logger.exception("命名工作流执行失败")
        raise NamingServiceError(NAMING_BUSY_MESSAGE) from exc

    output = final_state.get("final_output") if final_state else None
    if not isinstance(output, dict) or not output.get("names"):
        logger.warning("命名工作流未返回有效 names 列表")
        raise NamingServiceError(NAMING_BUSY_MESSAGE)
    return final_state


def _names_summary(names: dict[str, Any]) -> str:
    items = names.get("names") if isinstance(names, dict) else []
    if not isinstance(items, list):
        return ""
    parts = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        parts.append(
            f"{item.get('name', '')}（{item.get('moral') or item.get('analysis') or '无说明'}）"
        )
    return "；".join(part for part in parts if part.strip("；（）"))


async def remember_generation_result(
        user_id: int,
        thread_id: str,
        name_info: NameIn,
        names: dict[str, Any],
        source: str = "generation") -> None:
    summary = _names_summary(names)
    content = (
        f"用户在【{name_info.category}】场景中提出需求："
        f"姓氏={name_info.surname or '无'}，性别={name_info.gender}，"
        f"长度={name_info.length}，其他要求={name_info.other or '无'}，"
        f"避用={','.join(name_info.exclude) if name_info.exclude else '无'}。"
    )
    extras = []
    if name_info.use_bazi:
        extras.append(f"启用八字五行，出生信息：{name_info.birth_info or '未填写'}")
    if name_info.brand_tone:
        extras.append(f"品牌调性：{name_info.brand_tone}")
    if name_info.target_audience:
        extras.append(f"目标客群：{name_info.target_audience}")
    if name_info.competitors:
        extras.append(f"竞品/相似品牌：{name_info.competitors}")
    if name_info.ip_setting:
        extras.append(f"虚拟 IP 设定：{name_info.ip_setting}")
    if name_info.ip_personality:
        extras.append(f"虚拟 IP 性格：{name_info.ip_personality}")
    if extras:
        content += "增强条件：" + "；".join(extras) + "。"
    if summary:
        content += f" 本轮候选包括：{summary}。"
    await remember_text(
        user_id=user_id,
        category=name_info.category,
        source=source,
        source_id=thread_id,
        content=content,
        metadata={
            "thread_id": thread_id,
            "category": name_info.category,
            "generated_at": True,
        },
    )


async def generate_names(name_info: NameIn, user_id: int) -> dict[str, Any]:
    thread_id = str(uuid.uuid4())
    initial_state = {
        "user_id": user_id,
        "category": name_info.category,
        "surname": name_info.surname,
        "gender": name_info.gender,
        "length": name_info.length,
        "other": name_info.other,
        "exclude": name_info.exclude,
        "use_bazi": name_info.use_bazi,
        "birth_info": name_info.birth_info or "",
        "brand_tone": name_info.brand_tone or "",
        "target_audience": name_info.target_audience or "",
        "competitors": name_info.competitors or "",
        "ip_setting": name_info.ip_setting or "",
        "ip_personality": name_info.ip_personality or "",
        "final_output": {}
    }
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await run_naming_graph(initial_state, config)
    await remember_generation_result(
        user_id,
        thread_id,
        name_info,
        final_state["final_output"],
    )
    return {
        "thread_id": thread_id,
        "names": final_state["final_output"],
        "token_usage": final_state.get("token_usage", empty_token_usage()),
    }


async def feedback_names(feedback_info: FeedBackIn, user_id: int) -> dict[str, Any]:
    update_state = {
        "feedback": feedback_info.feedback,
        "category": feedback_info.category,
    }
    config = {"configurable": {"thread_id": feedback_info.thread_id}}
    final_state = await run_naming_graph(update_state, config)
    await remember_text(
        user_id=user_id,
        category=feedback_info.category,
        source="feedback",
        source_id=feedback_info.thread_id,
        content=(
            f"用户在【{feedback_info.category}】命名中提出调整偏好："
            f"{feedback_info.feedback}。调整后的候选："
            f"{_names_summary(final_state['final_output'])}"
        ),
        metadata={
            "thread_id": feedback_info.thread_id,
            "category": feedback_info.category,
            "feedback": feedback_info.feedback,
        },
    )
    return {
        "thread_id": feedback_info.thread_id,
        "names": final_state["final_output"],
        "token_usage": final_state.get("token_usage", empty_token_usage()),
    }
