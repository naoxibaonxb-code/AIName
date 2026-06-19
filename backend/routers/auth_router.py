import logging
import random
import string
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from fastapi.params import Query, Depends
from fastapi_mail import MessageSchema, MessageType
from pydantic import EmailStr
from redis.asyncio import Redis

from dependencies import get_mail
from fastapi_mail import FastMail
from sqlalchemy.ext.asyncio.session import AsyncSession
from dependencies import get_session
from aiosmtplib import SMTPResponseException, SMTPException
from repository.user_repo import EmailCodeRepository
from schemas import ResponseOut
from core.redis_client import get_redis_client

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.get("/code", response_model=ResponseOut)
async def get_email_code(email: Annotated[EmailStr, Query(...)],
                         mail: FastMail = Depends(get_mail),
                         session: AsyncSession = Depends(get_session),
                         redis_client: Redis = Depends(get_redis_client)):
    # 1、生成验证码
    source = string.digits * 4
    code = "".join(random.sample(source, 4))
    # 2、发送邮件
    message = MessageSchema(
        subject="【AIName】邮箱验证码",
        recipients=[email],
        body=f"您的验证码是：{code},五分钟内有效！",
        subtype=MessageType.plain
    )
    try:
        logger.info(f"开始向 {email} 发送验证码：{code}")
        await mail.send_message(message)
        logger.info(f"邮件发送成功：{email}")
        # 3、存储验证码
        # email_code_repo = EmailCodeRepository(session=session)
        # await email_code_repo.create_captcha(email, code)
        await redis_client.set(email, code, ex=300)
        return ResponseOut(result="success")
    except (SMTPResponseException, SMTPException) as e:
        logger.error(f"SMTP邮件发送失败：{e.code} - {e.message}")
        error_str = str(e)
        if "-1" in error_str and r"\x00" in error_str:
            logger.warning("QQ邮箱SMTP非标准响应，但邮件已发送")
            print("⚠ 忽略 QQ 邮箱 SMTP 关闭阶段的非标准响应（邮件已成功发送）")
            # email_code_repo = EmailCodeRepository(session=session)
            # await email_code_repo.create_captcha(email, code)
            await redis_client.set(email, code, ex=300)
            return ResponseOut(result="success")
        else:
            logger.error(f"未知错误：{str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="邮件发送失败！")


from schemas.user_schemas import RegisterIn, UserCreateSchema, LoginOut
from repository.user_repo import UserRepository


@router.post("/register", response_model=ResponseOut)
async def register(
        userinfo: RegisterIn,
        session: AsyncSession = Depends(get_session),
        redis_client: Redis = Depends(get_redis_client)):
    user_repo = UserRepository(session=session)

    # 检验邮箱是否存在
    email_exist = await user_repo.email_is_exist(email=str(userinfo.email))
    if email_exist:
        raise HTTPException(status_code=400, detail="该邮箱已注册！")

    # 检验验证码
    # email_code_repo = EmailCodeRepository(session=session)
    # email_code_match = await email_code_repo.verify_captcha(
    #     email=str(userinfo.email),
    #     email_code=str(userinfo.code))
    email_code_match = await redis_client.get(str(userinfo.email))
    if email_code_match != str(userinfo.code):
        raise HTTPException(400, detail="验证码错误或已过期")

    try:
        user_schema = UserCreateSchema(
            email=str(userinfo.email),
            password=str(userinfo.password),
            username=str(userinfo.username), )
        await user_repo.create_user(user_schema)
        await redis_client.delete(str(userinfo.email))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ResponseOut()


from schemas.user_schemas import LoginIn, LoginOut
from core.auth import AuthHandler
from models.user import User

authHandler = AuthHandler()
@router.post("/login", response_model=LoginOut)
async def login(
        data: LoginIn,
        request: Request,
        session: AsyncSession = Depends(get_session)):
    user_repo = UserRepository(session=session)
    user: User | None = await user_repo.get_by_email(str(data.email))
    if not user:
        raise HTTPException(status_code=400, detail="该用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")
    if not user.check_password(data.password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    await user_repo.add_login_record(
        user_id=user.id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    tokens = authHandler.encode_login_token(user.id)
    return {
        "token": tokens["access_token"],
        "user": user
    }
