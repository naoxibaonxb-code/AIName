import uuid
from datetime import datetime

from sqlalchemy import func, or_, select, exists, update
from sqlalchemy.ext.asyncio.session import AsyncSession
from models.user import LoginRecord
from schemas.user_schemas import UserCreateSchema
from models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, user_schema: UserCreateSchema):
        async with self.session.begin():
            user = User(**user_schema.model_dump())
            self.session.add(user)
            return user
    async def get_by_email(self, email: str):
        async with self.session.begin():
            user = await self.session.scalar(
                select(User).where(User.email == email, User.deleted_at.is_(None))
            )
            return user
    async def email_is_exist(self, email: str):
        async with self.session.begin():
            stmt = select(exists().where(User.email == email))
            result = await self.session.execute(stmt)
            return result.scalar()

    async def list_regular_users(self, search: str, offset: int, limit: int):
        filters = [User.role == "user", User.deleted_at.is_(None)]
        if search:
            keyword = f"%{search}%"
            filters.append(or_(User.username.like(keyword), User.email.like(keyword)))

        total = await self.session.scalar(
            select(func.count(User.id)).where(*filters)
        )
        result = await self.session.scalars(
            select(User)
            .where(*filters)
            .order_by(User.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result), total or 0

    async def get_by_id(self, user_id: int):
        return await self.session.get(User, user_id)

    async def set_active(self, user: User, is_active: bool):
        user.is_active = is_active
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def email_belongs_to_other_user(self, email: str, user_id: int) -> bool:
        result = await self.session.scalar(
            select(exists().where(User.email == email, User.id != user_id))
        )
        return bool(result)

    async def add_login_record(self, user_id: int, ip_address: str, user_agent: str):
        record = LoginRecord(
            user_id=user_id,
            ip_address=ip_address[:45],
            user_agent=user_agent[:500],
        )
        self.session.add(record)
        await self.session.commit()
        return record

    async def list_login_records(self, user_id: int, limit: int = 20):
        records = await self.session.scalars(
            select(LoginRecord)
            .where(LoginRecord.user_id == user_id)
            .order_by(LoginRecord.login_at.desc())
            .limit(limit)
        )
        return list(records)

    async def increment_usage(self, user_id: int):
        await self.session.execute(
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(usage_count=User.usage_count + 1)
        )
        await self.session.commit()

    async def cancel_account(self, user: User):
        suffix = uuid.uuid4().hex[:12]
        user.email = f"deleted_{user.id}_{suffix}@deleted.local"
        user.username = "已注销用户"
        user.password = uuid.uuid4().hex
        user.role = "user"
        user.is_active = False
        user.deleted_at = datetime.now()
        await self.session.commit()
