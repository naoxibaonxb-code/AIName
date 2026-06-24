import logging
import secrets
from typing import Annotated

from aiosmtplib import SMTPException, SMTPResponseException
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from redis.asyncio import Redis
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import AuthHandler
from core.redis_client import get_redis_client
from dependencies import get_mail, get_session
from models.user import User
from repository.user_repo import UserRepository
from schemas import ResponseOut
from schemas.user_schemas import LoginIn, LoginOut, RegisterIn, UserCreateSchema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
auth_handler = AuthHandler()


@router.get("/code", response_model=ResponseOut)
async def get_email_code(
        email: Annotated[EmailStr, Query(...)],
        mail: FastMail = Depends(get_mail),
        redis_client: Redis = Depends(get_redis_client)):
    code = f"{secrets.randbelow(10_000):04d}"
    message = MessageSchema(
        subject="【AIName】邮箱验证码",
        recipients=[email],
        body=f"您的验证码是：{code}，五分钟内有效。",
        subtype=MessageType.plain,
    )

    try:
        await mail.send_message(message)
    except SMTPResponseException as exc:
        error_text = str(exc)
        if exc.code != -1 or r"\x00" not in error_text:
            logger.exception("向 %s 发送验证码失败", email)
            raise HTTPException(status_code=502, detail="邮件发送失败") from exc
        logger.warning("SMTP 返回非标准关闭响应，邮件可能已成功发送")
    except SMTPException as exc:
        logger.exception("向 %s 发送验证码失败", email)
        raise HTTPException(status_code=502, detail="邮件发送失败") from exc

    await redis_client.set(str(email), code, ex=300)
    return ResponseOut()


@router.post("/register", response_model=ResponseOut)
async def register(
        userinfo: RegisterIn,
        session: AsyncSession = Depends(get_session),
        redis_client: Redis = Depends(get_redis_client)):
    user_repo = UserRepository(session)
    email = str(userinfo.email)

    if await user_repo.email_is_exist(email):
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    stored_code = await redis_client.get(email)
    if stored_code != userinfo.code:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    try:
        await user_repo.create_user(UserCreateSchema(
            email=email,
            username=userinfo.username,
            password=userinfo.password,
        ))
    except SQLAlchemyError as exc:
        logger.exception("创建用户失败")
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试") from exc

    await redis_client.delete(email)
    return ResponseOut()


@router.post("/login", response_model=LoginOut)
async def login(
        data: LoginIn,
        request: Request,
    session: AsyncSession = Depends(get_session)):
    user_repo = UserRepository(session)
    user: User | None = await user_repo.get_by_email(str(data.email))
    if not user or not user.check_password(data.password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    await user_repo.add_login_record(
        user_id=user.id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    token = auth_handler.encode_login_token(user.id)["access_token"]
    return {"token": token, "user": user}
