from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import AuthHandler
from dependencies import get_session
from models.user import User
from repository.user_repo import UserRepository
from schemas.admin import AdminUserListOut, AdminUserOut, UserStatusIn

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
