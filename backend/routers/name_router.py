import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session
from repository.user_repo import UserRepository
from schemas.name import NameOut, NameIn, NameWithThreadOut, FeedBackIn
from core.auth import AuthHandler
from core.workflow import (
    NAMING_BUSY_MESSAGE,
    NamingServiceError,
    feedback_names,
    get_name_v2,
)

logger = logging.getLogger(__name__)

auth_handler = AuthHandler()
router = APIRouter(prefix="/name", tags=["name"])


@router.post("/get_name", response_model=NameOut)
async def get_name(name_info: NameIn,
                   user_id: int = Depends(auth_handler.auth_access_dependency),
                   session: AsyncSession = Depends(get_session)):
    try:
        name_result = await get_name_v2(name_info, user_id)
        response = NameOut(names=name_result["names"]["names"])
        await UserRepository(session).increment_usage(user_id)
        return response
    except NamingServiceError as exc:
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
    except Exception as exc:
        logger.exception("起名接口返回结果处理失败")
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc


@router.post("/generate", response_model=NameWithThreadOut)
async def take_names_first_time(name_info: NameIn,
                                user_id: int = Depends(auth_handler.auth_access_dependency),
                                session: AsyncSession = Depends(get_session)):
    try:
        name_result = await get_name_v2(name_info, user_id)
        response = NameWithThreadOut(
            thread_id=name_result["thread_id"],
            names=name_result["names"]["names"],
        )
        await UserRepository(session).increment_usage(user_id)
        return response
    except NamingServiceError as exc:
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
    except Exception as exc:
        logger.exception("起名接口返回结果处理失败")
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc


@router.post("/feedback", response_model=NameWithThreadOut)
async def take_names_feedback(
        data: FeedBackIn,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    """带有 Thread_ID 的多轮微调"""
    try:
        result = await feedback_names(data, user_id)
        response = NameWithThreadOut(
            thread_id=result["thread_id"],
            names=result["names"]["names"])
        await UserRepository(session).increment_usage(user_id)
        return response
    except NamingServiceError as exc:
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
    except Exception as exc:
        logger.exception("名字微调接口执行失败")
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
