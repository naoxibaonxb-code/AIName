import csv
import io
import json
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import AuthHandler
from core.redis_client import redis_client
from core.workflow import (
    NAMING_BUSY_MESSAGE,
    NamingServiceError,
    delete_naming_thread,
    generate_names,
)
from dependencies import get_session
from models.user import User
from repository.history_repo import HistoryRepository, history_conditions
from repository.usage_repo import UsageRepository
from schemas.agent import NameSchema
from schemas.history import (
    FavoriteCreateIn,
    FavoriteNameOut,
    FavoritePageOut,
    NamingHistoryDetailOut,
    NamingHistoryPageOut,
    NamingHistorySummaryOut,
    NamingRoundOut,
)
from schemas.name import CategoryLiteral, NameWithThreadOut
from schemas.response import ResponseOut
from core.long_term_memory import remember_text
from services.favorite_export import favorite_pdf, favorite_png
from services.usage_control import acquire_generation_permit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/name", tags=["history"])
auth_handler = AuthHandler()


async def history_summary(
        repo: HistoryRepository, history, include_rounds: bool = False):
    rounds = await repo.get_rounds(history.id)
    round_outputs = [
        NamingRoundOut(
            id=item.id,
            round_number=item.round_number,
            feedback=item.feedback,
            names=[NameSchema.model_validate(name) for name in item.names],
            created_at=item.created_at,
        )
        for item in rounds
    ]
    common = dict(
        id=history.id,
        category=history.category,
        conditions=history_conditions(history),
        latest_names=round_outputs[-1].names if round_outputs else [],
        round_count=len(round_outputs),
        created_at=history.created_at,
        updated_at=history.updated_at,
        expires_at=history.expires_at,
    )
    if include_rounds:
        return NamingHistoryDetailOut(**common, rounds=round_outputs)
    return NamingHistorySummaryOut(**common)


@router.get("/favorites", response_model=FavoritePageOut)
async def list_favorites(
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    favorites, total = await HistoryRepository(session).list_favorites(
        user_id, (page - 1) * page_size, page_size
    )
    return FavoritePageOut(
        items=[FavoriteNameOut.model_validate(item) for item in favorites],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/favorites", response_model=FavoriteNameOut)
async def create_favorite(
        data: FavoriteCreateIn,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    repo = HistoryRepository(session)
    history = await repo.get_history(data.session_id, user_id)
    if not history:
        raise HTTPException(status_code=404, detail="起名历史不存在或已过期")
    round_record = await repo.get_round(history.id, data.round_number)
    if not round_record:
        raise HTTPException(status_code=404, detail="该轮结果不存在")
    if data.name_index >= len(round_record.names):
        raise HTTPException(status_code=400, detail="名字序号超出范围")
    snapshot = NameSchema.model_validate(
        round_record.names[data.name_index]
    ).model_dump(mode="json")
    favorite = await repo.create_favorite(
        user_id, history, data.round_number, snapshot
    )
    await remember_text(
        user_id=user_id,
        category=history.category,
        source="favorite",
        source_id=str(favorite.id),
        content=(
            f"用户收藏了【{history.category}】名字“{snapshot.get('name', '')}”。"
            f"出处：{snapshot.get('reference', '')}。"
            f"寓意：{snapshot.get('moral', '')}。"
            f"推演：{snapshot.get('analysis', '')}。"
        ),
        metadata={
            "favorite_id": favorite.id,
            "session_id": history.id,
            "round_number": data.round_number,
        },
    )
    return FavoriteNameOut.model_validate(favorite)


@router.delete("/favorites/{favorite_id}", response_model=ResponseOut)
async def delete_favorite(
        favorite_id: int,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    repo = HistoryRepository(session)
    favorite = await repo.get_favorite(favorite_id, user_id)
    if not favorite:
        raise HTTPException(status_code=404, detail="收藏不存在")
    await repo.delete_favorite(favorite)
    return ResponseOut(message="收藏已删除")


@router.get("/favorites/{favorite_id}/export")
async def export_favorite(
        favorite_id: int,
        format: Literal["pdf", "png", "report"] = "pdf",
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    repo = HistoryRepository(session)
    favorite = await repo.get_favorite(favorite_id, user_id)
    if not favorite:
        raise HTTPException(status_code=404, detail="收藏不存在")

    if favorite.category == "企业名":
        if format not in {"report", "pdf"}:
            raise HTTPException(status_code=400, detail="企业名收藏请导出为报告")
        content = favorite_pdf(favorite, report=True)
        media_type = "application/pdf"
        extension = "pdf"
        suffix = "company-report"
    else:
        if format == "report":
            raise HTTPException(status_code=400, detail="人名和宠物名可导出为 PDF 或图片")
        if format == "png":
            content = favorite_png(favorite)
            media_type = "image/png"
            extension = "png"
        else:
            content = favorite_pdf(favorite)
            media_type = "application/pdf"
            extension = "pdf"
        suffix = "favorite"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="ainame-{suffix}-{favorite.id}.{extension}"'
            )
        },
    )


@router.get("/history", response_model=NamingHistoryPageOut)
async def list_history(
        category: CategoryLiteral | None = None,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    repo = HistoryRepository(session)
    histories, total = await repo.list_histories(
        user_id, category, (page - 1) * page_size, page_size
    )
    items = [await history_summary(repo, item) for item in histories]
    return NamingHistoryPageOut(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/history/{history_id}", response_model=NamingHistoryDetailOut)
async def get_history(
        history_id: str,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    repo = HistoryRepository(session)
    history = await repo.get_history(history_id, user_id)
    if not history:
        raise HTTPException(status_code=404, detail="起名历史不存在或已过期")
    return await history_summary(repo, history, include_rounds=True)


@router.delete("/history/{history_id}", response_model=ResponseOut)
async def delete_history(
        history_id: str,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    repo = HistoryRepository(session)
    history = await repo.get_history(history_id, user_id)
    if not history:
        raise HTTPException(status_code=404, detail="起名历史不存在")
    try:
        await delete_naming_thread(history.id)
    except Exception as exc:
        logger.exception("删除 LangGraph 会话失败: %s", history.id)
        raise HTTPException(
            status_code=503,
            detail="历史清理暂时失败，请稍后重试",
        ) from exc
    await repo.delete_history(history)
    return ResponseOut(message="起名历史已删除")


@router.post("/history/{history_id}/regenerate", response_model=NameWithThreadOut)
async def regenerate_history(
        history_id: str,
        request: Request,
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    user_id = user.id
    repo = HistoryRepository(session)
    history = await repo.get_history(history_id, user_id)
    if not history:
        raise HTTPException(status_code=404, detail="起名历史不存在或已过期")
    conditions = history_conditions(history)
    client_ip = request.client.host if request.client else "unknown"
    permit = await acquire_generation_permit(
        redis_client, session, user_id, user.role, client_ip
    )
    token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    request_id = None
    try:
        result = await generate_names(conditions, user_id)
        token_usage = result["token_usage"]
        request_id = result["thread_id"]
        names = [NameSchema.model_validate(item) for item in result["names"]["names"]]
        await repo.create_history(
            request_id,
            user_id,
            conditions,
            [item.model_dump(mode="json") for item in names],
            commit=False,
        )
        await UsageRepository(session).record_call(
            user_id, "regenerate", True, token_usage, request_id=request_id,
            count_daily=permit.quota_source == "free",
        )
        return NameWithThreadOut(thread_id=request_id, names=names)
    except NamingServiceError as exc:
        await session.rollback()
        await permit.refund_paid_credit(session)
        await UsageRepository(session).record_call(
            user_id, "regenerate", False,
            getattr(exc, "token_usage", token_usage),
            request_id=request_id, error_type=type(exc).__name__,
        )
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
    except Exception as exc:
        await session.rollback()
        await permit.refund_paid_credit(session)
        try:
            await UsageRepository(session).record_call(
                user_id, "regenerate", False, token_usage,
                request_id=request_id, error_type=type(exc).__name__,
            )
        except Exception:
            logger.exception("记录重新生成失败调用时发生异常")
        raise HTTPException(status_code=503, detail=NAMING_BUSY_MESSAGE) from exc
    finally:
        await permit.release()


@router.get("/history/{history_id}/export")
async def export_history(
        history_id: str,
        format: Literal["json", "csv"] = "json",
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    repo = HistoryRepository(session)
    history = await repo.get_history(history_id, user_id)
    if not history:
        raise HTTPException(status_code=404, detail="起名历史不存在或已过期")
    detail = await history_summary(repo, history, include_rounds=True)

    if format == "json":
        content = json.dumps(
            detail.model_dump(mode="json"), ensure_ascii=False, indent=2
        )
        media_type = "application/json; charset=utf-8"
        extension = "json"
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["轮次", "反馈", "名字", "出处", "寓意", "推演", "域名", "域名状态"])
        for round_item in detail.rounds:
            for name in round_item.names:
                writer.writerow([
                    round_item.round_number,
                    round_item.feedback or "",
                    name.name,
                    name.reference,
                    name.moral,
                    name.analysis,
                    name.domain,
                    name.domain_status,
                ])
        content = "\ufeff" + output.getvalue()
        media_type = "text/csv; charset=utf-8"
        extension = "csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="naming-history-{history.id}.{extension}"'
            )
        },
    )
