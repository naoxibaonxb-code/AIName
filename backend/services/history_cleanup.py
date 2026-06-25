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
        candidate_ids = set(await session.scalars(
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
            candidate_ids.update(excess)

        if not candidate_ids:
            return 0

        deleted_checkpoint_ids = []
        for history_id in candidate_ids:
            try:
                await delete_naming_thread(history_id)
            except Exception:
                logger.exception("清理 LangGraph checkpoint 失败，保留历史等待重试: %s", history_id)
            else:
                deleted_checkpoint_ids.append(history_id)

        if not deleted_checkpoint_ids:
            logger.warning(
                "本轮发现 %s 条待清理历史，但 checkpoint 均未清理成功，跳过 MySQL 删除",
                len(candidate_ids),
            )
            return 0

        await session.execute(
            delete(NamingSession).where(NamingSession.id.in_(deleted_checkpoint_ids))
        )
        await session.commit()
        logger.info(
            "已清理 %s 条起名历史及对应 checkpoint，%s 条等待下次重试",
            len(deleted_checkpoint_ids),
            len(candidate_ids) - len(deleted_checkpoint_ids),
        )
        return len(deleted_checkpoint_ids)


async def history_cleanup_loop() -> None:
    while True:
        try:
            await cleanup_naming_history()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("定时清理起名历史失败")
        await asyncio.sleep(settings.HISTORY_CLEANUP_INTERVAL_SECONDS)
