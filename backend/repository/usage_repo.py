from datetime import date, datetime, time, timedelta

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.usage import DailyGenerationUsage, GenerationCredit, ModelCallUsage
from models.user import User


class UsageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def daily_used(self, user_id: int, usage_date: date) -> int:
        value = await self.session.scalar(
            select(DailyGenerationUsage.successful_generations).where(
                DailyGenerationUsage.user_id == user_id,
                DailyGenerationUsage.usage_date == usage_date,
            )
        )
        return value or 0

    async def paid_remaining(self, user_id: int) -> int:
        value = await self.session.scalar(
            select(func.coalesce(func.sum(GenerationCredit.remaining_credits), 0))
            .where(
                GenerationCredit.user_id == user_id,
                GenerationCredit.status == "active",
                GenerationCredit.remaining_credits > 0,
            )
        )
        return int(value or 0)

    async def grant_paid_credit(
            self,
            user_id: int,
            source_id: str,
            credits: int = 1,
            source_type: str = "alipay_sandbox") -> bool:
        existing = await self.session.scalar(
            select(GenerationCredit).where(
                GenerationCredit.source_type == source_type,
                GenerationCredit.source_id == source_id,
            )
        )
        if existing:
            return False
        self.session.add(GenerationCredit(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            total_credits=credits,
            remaining_credits=credits,
            status="active",
        ))
        await self.session.commit()
        return True

    async def reserve_paid_credit(self, user_id: int) -> int | None:
        credit = await self.session.scalar(
            select(GenerationCredit)
            .where(
                GenerationCredit.user_id == user_id,
                GenerationCredit.status == "active",
                GenerationCredit.remaining_credits > 0,
            )
            .order_by(GenerationCredit.created_at.asc(), GenerationCredit.id.asc())
            .with_for_update()
            .limit(1)
        )
        if not credit:
            return None
        credit.remaining_credits -= 1
        await self.session.commit()
        return credit.id

    async def refund_paid_credit(self, credit_id: int) -> None:
        await self.session.execute(
            update(GenerationCredit)
            .where(GenerationCredit.id == credit_id)
            .values(remaining_credits=GenerationCredit.remaining_credits + 1)
        )
        await self.session.commit()

    async def record_call(
            self,
            user_id: int,
            endpoint: str,
            success: bool,
            token_usage: dict[str, int],
            request_id: str | None = None,
            error_type: str | None = None,
            count_daily: bool = True) -> None:
        self.session.add(ModelCallUsage(
            user_id=user_id,
            endpoint=endpoint,
            success=success,
            prompt_tokens=token_usage.get("prompt_tokens", 0),
            completion_tokens=token_usage.get("completion_tokens", 0),
            total_tokens=token_usage.get("total_tokens", 0),
            request_id=request_id,
            error_type=error_type,
        ))
        if success and count_daily:
            today = date.today()
            daily = await self.session.scalar(
                select(DailyGenerationUsage).where(
                    DailyGenerationUsage.user_id == user_id,
                    DailyGenerationUsage.usage_date == today,
                )
            )
            if daily:
                daily.successful_generations += 1
            else:
                self.session.add(DailyGenerationUsage(
                    user_id=user_id,
                    usage_date=today,
                    successful_generations=1,
                ))
            await self.session.execute(
                update(User)
                .where(User.id == user_id, User.deleted_at.is_(None))
                .values(usage_count=User.usage_count + 1)
            )
        elif success:
            await self.session.execute(
                update(User)
                .where(User.id == user_id, User.deleted_at.is_(None))
                .values(usage_count=User.usage_count + 1)
            )
        await self.session.commit()

    async def summary(self, days: int) -> tuple[list, dict[str, int]]:
        start_date = date.today() - timedelta(days=days - 1)
        start = datetime.combine(start_date, time.min)
        day = func.date(ModelCallUsage.created_at).label("date")
        rows = (await self.session.execute(
            select(
                day,
                func.count(ModelCallUsage.id).label("calls"),
                func.sum(case((ModelCallUsage.success.is_(True), 1), else_=0)).label("successful_calls"),
                func.sum(case((ModelCallUsage.success.is_(False), 1), else_=0)).label("failed_calls"),
                func.sum(ModelCallUsage.prompt_tokens).label("prompt_tokens"),
                func.sum(ModelCallUsage.completion_tokens).label("completion_tokens"),
                func.sum(ModelCallUsage.total_tokens).label("total_tokens"),
            )
            .where(ModelCallUsage.created_at >= start)
            .group_by(day)
            .order_by(day)
        )).all()
        totals = {
            key: sum(int(getattr(row, key) or 0) for row in rows)
            for key in (
                "calls", "successful_calls", "failed_calls", "prompt_tokens",
                "completion_tokens", "total_tokens",
            )
        }
        return rows, totals

    async def list_calls(
            self, offset: int, limit: int, user_id: int | None = None
    ) -> tuple[list[ModelCallUsage], int]:
        filters = []
        if user_id is not None:
            filters.append(ModelCallUsage.user_id == user_id)
        total = await self.session.scalar(select(func.count(ModelCallUsage.id)).where(*filters))
        calls = await self.session.scalars(
            select(ModelCallUsage)
            .where(*filters)
            .order_by(ModelCallUsage.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(calls), total or 0
