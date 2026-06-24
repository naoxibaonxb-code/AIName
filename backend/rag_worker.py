import asyncio
import json
import logging
import signal
from typing import Any

import aio_pika

from core.database import AsyncSessionFactory, engine
from core.rag_service import delete_knowledge_vectors, index_knowledge_file
from models.knowledge import KnowledgeFile
from settings.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("rag_worker")


def _validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload.get("action")
    if action not in {"index", "delete"}:
        raise ValueError(f"不支持的知识库任务类型: {action}")

    record_id = int(payload["record_id"])
    user_id = int(payload["user_id"])
    scope = str(payload.get("scope") or "private")
    if scope not in {"private", "public"}:
        raise ValueError(f"不支持的知识库范围: {scope}")

    file_path = payload.get("file_path")
    if action == "index" and not file_path:
        raise ValueError("索引任务缺少 file_path")

    return {
        "action": action,
        "record_id": record_id,
        "user_id": user_id,
        "scope": scope,
        "file_path": file_path,
    }


async def _mark_delete_done(record_id: int) -> None:
    async with AsyncSessionFactory() as session:
        record = await session.get(KnowledgeFile, record_id)
        if not record:
            return
        record.chunk_count = 0
        record.error_message = None
        await session.commit()


async def handle_task(payload: dict[str, Any]) -> None:
    task = _validate_payload(payload)
    action = task["action"]
    record_id = task["record_id"]
    user_id = task["user_id"]
    scope = task["scope"]

    if action == "index":
        logger.info("开始索引知识库文件: record_id=%s scope=%s", record_id, scope)
        await index_knowledge_file(record_id, task["file_path"], user_id, scope)
        logger.info("知识库文件索引任务完成: record_id=%s", record_id)
        return

    logger.info("开始删除知识库向量: record_id=%s scope=%s", record_id, scope)
    await asyncio.to_thread(delete_knowledge_vectors, record_id, user_id, scope)
    await _mark_delete_done(record_id)
    logger.info("知识库向量删除任务完成: record_id=%s", record_id)


async def consume() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(
            settings.RABBITMQ_KNOWLEDGE_QUEUE,
            durable=True,
        )
        logger.info(
            "RAG worker 已启动，监听队列: %s", settings.RABBITMQ_KNOWLEDGE_QUEUE
        )

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for item in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(item, stop_event.set)
            except NotImplementedError:
                pass

        async with queue.iterator() as iterator:
            async for message in iterator:
                if stop_event.is_set():
                    break
                async with message.process(requeue=False):
                    try:
                        payload = json.loads(message.body.decode("utf-8"))
                        await handle_task(payload)
                    except Exception:
                        logger.exception("知识库任务处理失败，消息将被确认并记录错误")

                if stop_event.is_set():
                    break

        logger.info("RAG worker 正在退出...")


async def main() -> None:
    try:
        await consume()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
