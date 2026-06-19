from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import AuthHandler
from core.redis_client import get_redis_client
from dependencies import get_session
from models.user import LoginRecord, User
from repository.user_repo import UserRepository
from schemas.response import ResponseOut
from schemas.user_center import (
    AccountCancelIn,
    LoginRecordOut,
    PasswordUpdateIn,
    ProfileUpdateIn,
    UserCenterOut,
)
from schemas.user_schemas import UserSchema

router = APIRouter(prefix="/users", tags=["users"])
auth_handler = AuthHandler()


@router.get("/me", response_model=UserCenterOut)
async def get_user_center(
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    login_count, last_login_at = (
        await session.execute(
            select(func.count(LoginRecord.id), func.max(LoginRecord.login_at))
            .where(LoginRecord.user_id == user.id)
        )
    ).one()
    return UserCenterOut(
        user=UserSchema.model_validate(user),
        login_count=login_count or 0,
        last_login_at=last_login_at,
    )


@router.patch("/me/profile", response_model=UserSchema)
async def update_profile(
        data: ProfileUpdateIn,
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session),
        redis_client: Redis = Depends(get_redis_client)):
    repo = UserRepository(session)

    if data.username is not None:
        user.username = data.username.strip()

    new_email = str(data.email) if data.email is not None else user.email
    if new_email != user.email:
        if not data.current_password or not user.check_password(data.current_password):
            raise HTTPException(status_code=400, detail="当前密码错误")
        if not data.email_code:
            raise HTTPException(status_code=400, detail="修改邮箱需要验证码")
        stored_code = await redis_client.get(new_email)
        if stored_code != data.email_code:
            raise HTTPException(status_code=400, detail="验证码错误或已过期")
        if await repo.email_belongs_to_other_user(new_email, user.id):
            raise HTTPException(status_code=400, detail="该邮箱已被其他账号使用")
        user.email = new_email
        await redis_client.delete(new_email)

    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/me/password", response_model=ResponseOut)
async def update_password(
        data: PasswordUpdateIn,
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    if not user.check_password(data.current_password):
        raise HTTPException(status_code=400, detail="当前密码错误")
    user.password = data.new_password
    await session.commit()
    return ResponseOut(message="密码修改成功")


@router.get("/me/login-records", response_model=list[LoginRecordOut])
async def get_login_records(
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    records = await UserRepository(session).list_login_records(user.id)
    return [
        LoginRecordOut(
            id=record.id,
            login_at=record.login_at,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
        )
        for record in records
    ]


@router.delete("/me", response_model=ResponseOut)
async def cancel_account(
        data: AccountCancelIn,
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    if data.confirmation != "DELETE":
        raise HTTPException(status_code=400, detail="请输入 DELETE 确认注销")
    if not user.check_password(data.password):
        raise HTTPException(status_code=400, detail="密码错误")
    await UserRepository(session).cancel_account(user)
    return ResponseOut(message="账号已注销")
