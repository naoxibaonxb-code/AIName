import asyncio
import logging
from datetime import datetime

from sqlalchemy import delete, distinct, select

from core.database import AsyncSessionFactory
from core.workflow import delete_naming_thread
from models.history import NamingSession
from settings.config import settings

logger = logging.getLogger(__name__)


async def cleanup_naming_history() -> int:
    async with AsyncSessionFactory() as session:
        history_ids = set(await session.scalars(
            select(NamingSession.id).where(NamingSession.expires_at <= datetime.now())
        ))
        user_ids = await session.scalars(select(distinct(NamingSession.user_id)))
        for user_id in user_ids:
            excess = await session.scalars(
                select(NamingSession.id)
                .where(NamingSession.user_id == user_id)
                .order_by(NamingSession.updated_at.desc())
                .offset(settings.HISTORY_MAX_PER_USER)
            )
            history_ids.update(excess)

        if not history_ids:
            return 0
        for history_id in history_ids:
            try:
                await delete_naming_thread(history_id)
            except Exception:
                logger.exception("清理 LangGraph 历史失败: %s", history_id)
        await session.execute(
            delete(NamingSession).where(NamingSession.id.in_(history_ids))
        )
        await session.commit()
        logger.info("已清理 %s 条过期起名历史", len(history_ids))
        return len(history_ids)


async def history_cleanup_loop() -> None:
    while True:
        try:
            await cleanup_naming_history()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("定时清理起名历史失败")
        await asyncio.sleep(settings.HISTORY_CLEANUP_INTERVAL_SECONDS)
