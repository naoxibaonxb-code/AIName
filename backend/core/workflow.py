import asyncio
import uuid
from typing import TypedDict, List, Dict, Any, Literal

from langgraph.graph import StateGraph, END
from langchain_deepseek import ChatDeepSeek

from settings.config import settings
from schemas.name import NameIn, FeedBackIn
from schemas.agent import NameResultSchema
from core.rag_service import retrieve_user_knowledge
from core.tools import check_com_domain


class WorkFlowState(TypedDict):
    user_id: int
    category: str
    surname: str
    gender: str
    length: str
    other: str
    exclude: List[str]
    feedback: str
    history_names: str
    final_output: Dict[str, Any]


llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0.5,
)

structured_llm = llm.with_structured_output(NameResultSchema).with_retry(
    stop_after_attempt=3
)


# 定义超级智能体
async def supervisor_node(state: WorkFlowState) -> Dict[str, Any]:
    """主管节点：后续可在这里扩展意图清洗或记录日志"""
    return {}


async def human_naming_node(state: WorkFlowState) -> Dict[str, Any]:
    """人名专家节点"""
    prompt = f"""你是一位精通汉语言文学与传统文化的命名专家。请为用户创作富有文化底蕴的人名
    【姓氏】: {state['surname']}
    【性别倾向】: {state['gender']}
    【字数限制】: {state['length']}
    【其它具体要求】: {state['other']}
    【避讳排除字】: {'、'.join(state['exclude'])}
    原则：平仄协调，优先从《诗经》《楚辞》或唐诗宋词中汲取灵感。请给出 5 个候选方案。"""
    response = await structured_llm.ainvoke(prompt)
    if response is None:
        raise ValueError("大模型/命名节点未返回有效结果，response 为 None")
    return {"final_output": response.model_dump(mode="json")}


async def company_naming_node(state: WorkFlowState) -> Dict[str, Any]:
    """企业品牌节点"""
    current_user_id = state["user_id"]
    search_query = f"{state['other']} 品牌命名规范 行业词汇"
    rag_context = retrieve_user_knowledge(query=search_query, user_id=current_user_id)
    feedback_instruction = ""
    if state.get("feedback") and state.get("history_names"):
        feedback_instruction = f"""
            警告：这是一次微调请求！
            【上一轮你生成的名字是】：{state['history_names']}
            【用户的最新修改意见】：{state['feedback']}
            请严格保留上一轮中用户满意的部分，仅针对【修改意见】对这 5 个名字进行迭代优化！绝不能抛弃历史记录重新随机生成！
        """
    prompt = f"""你是一位精通商业品牌传播与工商命名的资深顾问。请创作符合商业规范的公司名。
    【用户需求】
    行业或核心诉求: {state['other']}
    字数限制: {state['length']}
    避讳排除字: {'、'.join(state['exclude'])}
    【用户的专属私有知识库参考】
    {rag_context}
    {feedback_instruction}
    核心纪律（最高优先级）：
    1. 必须遵守知识库和修改意见。
    2. 你必须为每个公司名构思一个绝佳的 .com 英文或拼音域名，填入 domain 字段（例如：hema.com 或 greenearth.com）。
    请给出 5 个候选方案。"""
    response = await structured_llm.ainvoke(prompt)
    if not response or not hasattr(response, "names"):
        return {
            "final_output": {"names": [{"name": "生成失败", "reference": "无",
                                        "moral": "大模型服务异常，请重试"}]},
            "history_names": ""
        }
    # ================= 🌟 挂载工具：并发执行域名校验 =================
    # 为了不让 5 个域名的查询排队，我们使用 asyncio.gather 进行并发查询（极速体验）
    tasks = [check_com_domain(n.domain) for n in response.names]
    statuses = await asyncio.gather(*tasks)

    # 将查询结果赋给大模型生成的对象
    for n, status in zip(response.names, statuses):
        n.domain_status = status

    names_str = ", ".join([n.name for n in response.names])
    return {"final_output": response.model_dump(), "history_names": names_str}


async def pet_naming_node(state: WorkFlowState) -> Dict[str, Any]:
    """宠物起名节点"""
    prompt = f"""你是一位充满创意的宠物达人。请为用户的宠物起一些富有灵性的名字。
    【宠物特征/性格】: {state['other']}
    【字数限制】: {state['length']}
    【避讳排除字】: {'、'.join(state['exclude'])}
    原则：亲切好记、富有画面感或软萌感。请给出 5 个候选方案。"""
    response = await structured_llm.ainvoke(prompt)
    return {"final_output": response.model_dump()}


def route_by_category(state: WorkFlowState) -> Literal["human", "company", "pet"]:
    """条件路由：根据前端传来的 category 决定走哪个节点"""
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

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from settings.config import settings
from psycopg_pool import AsyncConnectionPool

PG_URL = settings.pg_url
connection_pool = AsyncConnectionPool(PG_URL, max_size=10)
memory = AsyncPostgresSaver(connection_pool)

naming_graph = workflow.compile(checkpointer=memory)


async def get_name_v2(name_info: NameIn, user_id: int) -> Dict[str, Any]:
    """提供给 Router 调用的统一异步接口"""
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
    final_state = await naming_graph.ainvoke(initial_state, config=config)
    return {"thread_id": thread_id, "names": final_state["final_output"]}


async def feedback_names(feedback_info: FeedBackIn, user_id: int) -> Dict[str, Any]:
    """【多轮微调接口】根据 UUID 唤醒记忆"""
    update_state = {
        "feedback": feedback_info.feedback,
        "category": feedback_info.category,
    }
    config = {"configurable": {"thread_id": feedback_info.thread_id}}
    final_state = await naming_graph.ainvoke(update_state, config=config)
    return {"thread_id": feedback_info.thread_id,
            "names": final_state["final_output"]}
