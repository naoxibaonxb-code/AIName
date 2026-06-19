import argparse
import asyncio

from sqlalchemy import select

from core.database import AsyncSessionFactory, engine
from models.user import User


async def promote_user(email: str) -> None:
    async with AsyncSessionFactory() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if not user:
            raise SystemExit(f"未找到邮箱为 {email} 的用户，请先完成普通用户注册。")
        user.role = "admin"
        user.is_active = True
        await session.commit()
        print(f"已将 {email} 设置为管理员。")


async def main(email: str) -> None:
    try:
        await promote_user(email)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将已注册用户设置为管理员")
    parser.add_argument("email", help="已注册用户的邮箱")
    args = parser.parse_args()
    asyncio.run(main(args.email))
