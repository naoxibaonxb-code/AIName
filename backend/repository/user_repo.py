import datetime
from datetime import datetime, timedelta

from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio.session import AsyncSession
from models.user import EmailCode
from schemas.user_schemas import UserCreateSchema
from models.user import User


# 用户模块，直接访问数据库的函数
# 访问数据库需要session
class EmailCodeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # 向数据库添加邮件和验证码的信息
    # email：你向那个邮箱发了邮件
    # code生成验证码
    async def create_captcha(self, email: str, email_code: str):
        async with self.session.begin():
            email_code = EmailCode(email=email, code=email_code)
            self.session.add(email_code)
        return email_code

    async def verify_captcha(self, email: str, email_code: str):
        async with self.session.begin():
            email_code_obj = await self.session.scalar(
                select(EmailCode).where(EmailCode.email == email, EmailCode.code == email_code))
            if not email_code_obj:
                return False

            if (datetime.now() - email_code_obj.created_time) > timedelta(minutes=5):
                return False
            return True


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self,user_schema: UserCreateSchema):
        async with self.session.begin():
            user = User(**user_schema.model_dump())
            self.session.add(user)
            return user
    async def get_by_email(self, email: str):
        async with self.session.begin():
            user = await self.session.scalar(select(User).where(User.email == email))
            return user
    async def email_is_exist(self, email: str):
        async with self.session.begin():
            stmt = select(exists().where(User.email==email))
            result = await self.session.execute(stmt)
            return result.scalar()