import asyncio
import logging
from datetime import datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from settings.config import settings

logger = logging.getLogger(__name__)

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:  # pragma: no cover - optional enhancement dependency
    OllamaEmbeddings = None

memory_pool = AsyncConnectionPool(settings.pg_url, max_size=5, open=False)
embedding_model = (
    OllamaEmbeddings(model=settings.MEMORY_EMBEDDING_MODEL)
    if OllamaEmbeddings is not None else None
)
_memory_ready = False


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{float(item):.8f}" for item in vector) + "]"


async def initialize_memory_store() -> None:
    global _memory_ready
    if not settings.MEMORY_ENABLED:
        return
    if embedding_model is None:
        logger.warning("长期记忆已跳过：未安装 langchain-ollama")
        return
    try:
        await memory_pool.open(wait=True, timeout=10)
        async with memory_pool.connection() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS agent_long_term_memory (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    category VARCHAR(20) NOT NULL,
                    source VARCHAR(30) NOT NULL,
                    source_id VARCHAR(80),
                    content TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    embedding vector({settings.MEMORY_EMBEDDING_DIM}) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_agent_memory_user_category_created
                ON agent_long_term_memory (user_id, category, created_at DESC)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_agent_memory_embedding
                ON agent_long_term_memory
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
                """
            )
            await conn.commit()
        _memory_ready = True
    except Exception:
        _memory_ready = False
        logger.warning("长期记忆初始化失败，已降级为无记忆模式", exc_info=True)
        if not memory_pool.closed:
            await memory_pool.close()


async def close_memory_store() -> None:
    global _memory_ready
    _memory_ready = False
    if not memory_pool.closed:
        await memory_pool.close()


async def _embed_text(text: str) -> list[float]:
    if embedding_model is None:
        return []
    return await asyncio.to_thread(embedding_model.embed_query, text)


def _memory_available() -> bool:
    return settings.MEMORY_ENABLED and _memory_ready and not memory_pool.closed


async def remember_text(
        user_id: int,
        category: str,
        source: str,
        source_id: str | None,
        content: str,
        metadata: dict[str, Any] | None = None) -> None:
    if not _memory_available():
        return
    content = " ".join((content or "").split())
    if not content:
        return
    try:
        embedding = await asyncio.wait_for(
            _embed_text(content), timeout=settings.MEMORY_TIMEOUT_SECONDS
        )
        if len(embedding) != settings.MEMORY_EMBEDDING_DIM:
            logger.warning(
                "长期记忆向量维度不匹配: expected=%s actual=%s",
                settings.MEMORY_EMBEDDING_DIM, len(embedding),
            )
            return
        async with memory_pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_long_term_memory
                    (user_id, category, source, source_id, content, metadata, embedding)
                VALUES
                    (%s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                """,
                (
                    user_id,
                    category,
                    source,
                    source_id,
                    content,
                    Jsonb(metadata or {}),
                    _vector_literal(embedding),
                ),
            )
            await conn.commit()
    except Exception:
        logger.warning("写入长期记忆失败: user_id=%s category=%s", user_id, category, exc_info=True)


async def retrieve_memories(
        user_id: int,
        category: str,
        query: str,
        top_k: int | None = None) -> list[dict[str, Any]]:
    if not _memory_available():
        return []
    query = " ".join((query or "").split())
    if not query:
        return []
    try:
        embedding = await asyncio.wait_for(
            _embed_text(query), timeout=settings.MEMORY_TIMEOUT_SECONDS
        )
        async with memory_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT id, category, source, source_id, content, metadata, created_at,
                           1 - (embedding <=> %s::vector) AS score
                    FROM agent_long_term_memory
                    WHERE user_id = %s
                      AND category IN (%s, '通用')
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (
                        _vector_literal(embedding),
                        user_id,
                        category,
                        _vector_literal(embedding),
                        top_k or settings.MEMORY_TOP_K,
                    ),
                )
                return [dict(row) async for row in cur]
    except Exception:
        logger.warning("检索长期记忆失败: user_id=%s category=%s", user_id, category, exc_info=True)
        return []


def format_memory_context(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return "暂无可用的长期偏好记忆。"
    blocks = []
    for item in memories:
        created_at = item.get("created_at")
        if isinstance(created_at, datetime):
            date_text = created_at.strftime("%Y-%m-%d")
        else:
            date_text = ""
        prefix = f"{item.get('source', 'memory')}"
        if date_text:
            prefix = f"{prefix} / {date_text}"
        blocks.append(f"- 【{prefix}】{item.get('content', '')}")
    return "\n".join(blocks)
