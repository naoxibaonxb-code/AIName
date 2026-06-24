import json
import logging
from typing import Literal

from settings.config import settings

logger = logging.getLogger(__name__)

KnowledgeTaskAction = Literal["index", "delete"]


async def publish_knowledge_task(
        action: KnowledgeTaskAction,
        record_id: int,
        user_id: int,
        scope: str,
        file_path: str | None = None) -> None:
    try:
        import aio_pika
    except ImportError as exc:
        raise RuntimeError("缺少 aio-pika 依赖，无法发送知识库队列消息") from exc

    payload = {
        "action": action,
        "record_id": record_id,
        "user_id": user_id,
        "scope": scope,
        "file_path": file_path,
    }
    connection = None
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        queue = await channel.declare_queue(
            settings.RABBITMQ_KNOWLEDGE_QUEUE,
            durable=True,
        )
        message = aio_pika.Message(
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await channel.default_exchange.publish(message, routing_key=queue.name)
    except Exception:
        logger.exception("知识库队列消息发送失败: %s", payload)
        raise
    finally:
        if connection:
            await connection.close()
