from fastapi_mail import FastMail

from core.database import AsyncSessionFactory
from core.mail import create_mail_instance


async def get_mail() -> FastMail:
    return create_mail_instance()


# 访问数据库链接
async def get_session():
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()