from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import AuthHandler
from dependencies import get_session
from models.user import User
from repository.user_repo import UserRepository
from repository.usage_repo import UsageRepository
from schemas.admin import AdminUserListOut, AdminUserOut, UserStatusIn
from schemas.usage import AdminUsageCallsOut, AdminUsageSummaryOut, DailyUsageOut

router = APIRouter(prefix="/admin", tags=["admin"])
auth_handler = AuthHandler()


@router.get("/users", response_model=AdminUserListOut)
async def list_users(
        search: Annotated[str, Query(max_length=100)] = "",
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        _: User = Depends(auth_handler.admin_dependency),
        session: AsyncSession = Depends(get_session)):
    repo = UserRepository(session)
    users, total = await repo.list_regular_users(
        search=search.strip(), offset=(page - 1) * page_size, limit=page_size
    )
    return AdminUserListOut(
        items=users, total=total, page=page, page_size=page_size
    )


@router.patch("/users/{user_id}/status", response_model=AdminUserOut)
async def update_user_status(
        user_id: int,
        data: UserStatusIn,
        admin: User = Depends(auth_handler.admin_dependency),
        session: AsyncSession = Depends(get_session)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能禁用当前管理员账号")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role != "user":
        raise HTTPException(status_code=400, detail="此模块只能管理普通用户")
    return await repo.set_active(user, data.is_active)


@router.get("/usage/summary", response_model=AdminUsageSummaryOut)
async def usage_summary(
        days: Annotated[int, Query(ge=1, le=365)] = 30,
        _: User = Depends(auth_handler.admin_dependency),
        session: AsyncSession = Depends(get_session)):
    rows, totals = await UsageRepository(session).summary(days)
    daily = [DailyUsageOut(
        date=row.date,
        calls=int(row.calls or 0),
        successful_calls=int(row.successful_calls or 0),
        failed_calls=int(row.failed_calls or 0),
        prompt_tokens=int(row.prompt_tokens or 0),
        completion_tokens=int(row.completion_tokens or 0),
        total_tokens=int(row.total_tokens or 0),
    ) for row in rows]
    return AdminUsageSummaryOut(days=days, daily=daily, **totals)


@router.get("/usage/calls", response_model=AdminUsageCallsOut)
async def usage_calls(
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        user_id: Annotated[int | None, Query(ge=1)] = None,
        _: User = Depends(auth_handler.admin_dependency),
        session: AsyncSession = Depends(get_session)):
    calls, total = await UsageRepository(session).list_calls(
        offset=(page - 1) * page_size,
        limit=page_size,
        user_id=user_id,
    )
    return AdminUsageCallsOut(
        items=calls, total=total, page=page, page_size=page_size
    )
