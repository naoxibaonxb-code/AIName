import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import AuthHandler
from core.redis_client import redis_client
from core.workflow import (
    NAMING_BUSY_MESSAGE,
    NamingServiceError,
    feedback_names,
    generate_names,
)
from dependencies import get_session
from models.user import User
from repository.history_repo import HistoryRepository
from repository.usage_repo import UsageRepository
from schemas.name import FeedBackIn, NameIn, NameWithThreadOut
from schemas.usage import QuotaOut
from services.usage_control import acquire_generation_permit
from settings.config import settings

logger = logging.getLogger(__name__)
auth_handler = AuthHandler()
router = APIRouter(prefix="/name", tags=["name"])


def _empty_usage() -> dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


async def _record_failure(
        session: AsyncSession,
        user_id: int,
        endpoint: str,
        token_usage: dict[str, int],
        request_id: str | None,
        exc: Exception) -> None:
    try:
        await session.rollback()
        await UsageRepository(session).record_call(
            user_id=user_id,
            endpoint=endpoint,
            success=False,
            token_usage=token_usage,
            request_id=request_id,
            error_type=type(exc).__name__,
        )
    except Exception:
        logger.exception("记录大模型失败调用时发生异常")


@router.post("/generate", response_model=NameWithThreadOut)
async def take_names_first_time(
        name_info: NameIn,
        request: Request,
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    user_id = user.id
    client_ip = request.client.host if request.client else "unknown"
    permit = await acquire_generation_permit(
        redis_client, session, user_id, user.role, client_ip
    )
    token_usage = _empty_usage()
    request_id = None
    try:
        result = await generate_names(name_info, user_id)
        token_usage = result["token_usage"]
        request_id = result["thread_id"]
        response = NameWithThreadOut(
            thread_id=request_id,
            names=result["names"]["names"],
        )
        await HistoryRepository(session).create_history(
            request_id,
            user_id,
            name_info,
            [item.model_dump(mode="json") for item in response.names],
            commit=False,
        )
        await UsageRepository(session).record_call(
            user_id, "generate", True, token_usage, request_id=request_id
        )
        return response
    except NamingServiceError as exc:
        await _record_failure(
            session, user_id, "generate",
            getattr(exc, "token_usage", token_usage), request_id, exc,
        )
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
    except Exception as exc:
        await _record_failure(
            session, user_id, "generate", token_usage, request_id, exc
        )
        logger.exception("起名接口执行失败")
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
    finally:
        await permit.release()


@router.post("/feedback", response_model=NameWithThreadOut)
async def take_names_feedback(
        data: FeedBackIn,
        request: Request,
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    user_id = user.id
    history_repo = HistoryRepository(session)
    history = await history_repo.get_history(data.thread_id, user_id)
    if not history:
        raise HTTPException(status_code=404, detail="起名历史不存在或已过期")
    if history.category != data.category:
        raise HTTPException(status_code=400, detail="起名类型与历史记录不一致")

    client_ip = request.client.host if request.client else "unknown"
    permit = await acquire_generation_permit(
        redis_client, session, user_id, user.role, client_ip
    )
    token_usage = _empty_usage()
    try:
        result = await feedback_names(data, user_id)
        token_usage = result["token_usage"]
        response = NameWithThreadOut(
            thread_id=result["thread_id"],
            names=result["names"]["names"],
        )
        await history_repo.add_round(
            history,
            data.feedback,
            [item.model_dump(mode="json") for item in response.names],
            commit=False,
        )
        await UsageRepository(session).record_call(
            user_id, "feedback", True, token_usage, request_id=data.thread_id
        )
        return response
    except NamingServiceError as exc:
        await _record_failure(
            session, user_id, "feedback",
            getattr(exc, "token_usage", token_usage), data.thread_id, exc,
        )
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
    except Exception as exc:
        await _record_failure(
            session, user_id, "feedback", token_usage, data.thread_id, exc
        )
        logger.exception("名字微调接口执行失败")
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
    finally:
        await permit.release()


@router.get("/quota", response_model=QuotaOut)
async def get_quota(
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    today = date.today()
    used = await UsageRepository(session).daily_used(user.id, today)
    limit = settings.DAILY_FREE_GENERATIONS
    return QuotaOut(
        date=today,
        daily_limit=limit,
        used=used,
        remaining=max(0, limit - used),
    )
