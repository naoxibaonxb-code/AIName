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
{"names":[{"name":"名称","reference":"出处或创意来源","moral":"含义与寓意","domain":"企业名对应的.com域名，非企业名可为空"}]}
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
    return rules.get(length, f"宠物名按“{length}”控制，避免过长。")


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

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

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


async def human_naming_node(state: WorkFlowState) -> dict[str, Any]:
    """人名专家节点"""
    length_instruction = build_length_instruction(state["category"], state["length"])
    prompt = f"""你是一位精通汉语言文学与传统文化的命名专家。请为用户创作富有文化底蕴的人名
    【姓氏】: {state['surname']}
    【性别倾向】: {state['gender']}
    【名字长度】: {state['length']}。{length_instruction}
    【其它具体要求】: {state['other']}
    【避讳排除字】: {'、'.join(state['exclude'])}
    原则：平仄协调，优先从《诗经》《楚辞》或唐诗宋词中汲取灵感。请给出 5 个候选方案。"""
    response, token_usage = await invoke_naming_model(prompt)
    return {"final_output": response.model_dump(mode="json"), "token_usage": token_usage}


async def company_naming_node(state: WorkFlowState) -> dict[str, Any]:
    """企业品牌节点"""
    current_user_id = state["user_id"]
    search_query = f"{state['other']} 品牌命名规范 行业词汇"
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
    length_instruction = build_length_instruction(state["category"], state["length"])
    prompt = f"""你是一位精通商业品牌传播与工商命名的资深顾问。请创作符合商业规范的公司名。
    【用户需求】
    行业或核心诉求: {state['other']}
    名字长度: {state['length']}。{length_instruction}
    避讳排除字: {'、'.join(state['exclude'])}
    【用户的专属私有知识库参考】
    {rag_context}
    {feedback_instruction}
    核心纪律（最高优先级）：
    1. 必须遵守知识库和修改意见。
    2. 你必须为每个公司名构思一个绝佳的 .com 英文或拼音域名，填入 domain 字段（例如：hema.com 或 greenearth.com）。
    请给出 5 个候选方案。"""
    response, token_usage = await invoke_naming_model(prompt)
    tasks = [
        check_com_domain(n.domain)
        if n.domain else asyncio.sleep(0, result="未提供域名")
        for n in response.names
    ]
    statuses = await asyncio.gather(*tasks)

    for n, status in zip(response.names, statuses):
        n.domain_status = status

    names_str = ", ".join(n.name for n in response.names)
    return {
        "final_output": response.model_dump(),
        "history_names": names_str,
        "token_usage": token_usage,
    }


async def pet_naming_node(state: WorkFlowState) -> dict[str, Any]:
    """宠物起名节点"""
    length_instruction = build_length_instruction(state["category"], state["length"])
    prompt = f"""你是一位充满创意的宠物达人。请为用户的宠物起一些富有灵性的名字。
    【宠物特征/性格】: {state['other']}
    【名字长度】: {state['length']}。{length_instruction}
    【避讳排除字】: {'、'.join(state['exclude'])}
    原则：亲切好记、富有画面感或软萌感。请给出 5 个候选方案。"""
    response, token_usage = await invoke_naming_model(prompt)
    return {"final_output": response.model_dump(), "token_usage": token_usage}


def route_by_category(state: WorkFlowState) -> Literal["human", "company", "pet"]:
    category_map = {"人名": "human", "企业名": "company", "宠物名": "pet"}
    return category_map.get(state.get("category", "人名"), "human")


workflow = StateGraph(WorkFlowState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("human", human_naming_node)
workflow.add_node("company", company_naming_node)
workflow.add_node("pet", pet_naming_node)

workflow.set_entry_point("supervisor")
workflow.add_conditional_edges(
    "supervisor",
    route_by_category,
    {"human": "human", "company": "company", "pet": "pet"},
)

workflow.add_edge("human", END)
workflow.add_edge("company", END)
workflow.add_edge("pet", END)

connection_pool = AsyncConnectionPool(settings.pg_url, max_size=10, open=False)
naming_graph = None
checkpoint_saver: AsyncPostgresSaver | None = None


async def initialize_naming_workflow() -> None:
    global checkpoint_saver, naming_graph
    await connection_pool.open(wait=True, timeout=10)
    checkpoint_saver = AsyncPostgresSaver(connection_pool)
    naming_graph = workflow.compile(checkpointer=checkpoint_saver)


async def close_naming_workflow() -> None:
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
        "final_output": {}
    }
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await run_naming_graph(initial_state, config)
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
    return {
        "thread_id": feedback_info.thread_id,
        "names": final_state["final_output"],
        "token_usage": final_state.get("token_usage", empty_token_usage()),
    }
