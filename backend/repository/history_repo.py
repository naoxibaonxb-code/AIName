from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.history import FavoriteName, NamingRound, NamingSession
from schemas.name import NameIn
from settings.config import settings


EXTRA_CONDITION_FIELDS = (
    "use_bazi",
    "birth_info",
    "brand_tone",
    "target_audience",
    "competitors",
    "ip_setting",
    "ip_personality",
)


def extra_conditions(conditions: NameIn) -> dict:
    return {
        field: getattr(conditions, field)
        for field in EXTRA_CONDITION_FIELDS
        if getattr(conditions, field, None) not in (None, "", False)
    }


class HistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_history(
            self,
            thread_id: str,
            user_id: int,
            conditions: NameIn,
            names: list[dict],
            commit: bool = True) -> NamingSession:
        now = datetime.now()
        history = NamingSession(
            id=thread_id,
            user_id=user_id,
            category=conditions.category,
            surname=conditions.surname,
            gender=conditions.gender,
            name_length=conditions.length,
            other=conditions.other or "",
            exclude=conditions.exclude,
            extra_conditions=extra_conditions(conditions),
            expires_at=now + timedelta(days=settings.HISTORY_RETENTION_DAYS),
        )
        self.session.add(history)
        await self.session.flush()
        self.session.add(NamingRound(
            session_id=thread_id,
            round_number=1,
            feedback=None,
            names=names,
        ))
        if commit:
            await self.session.commit()
        return history

    async def get_history(
            self, history_id: str, user_id: int) -> NamingSession | None:
        return await self.session.scalar(
            select(NamingSession).where(
                NamingSession.id == history_id,
                NamingSession.user_id == user_id,
            )
        )

    async def list_histories(
            self,
            user_id: int,
            category: str | None,
            offset: int,
            limit: int) -> tuple[list[NamingSession], int]:
        filters = [NamingSession.user_id == user_id]
        if category:
            filters.append(NamingSession.category == category)
        total = await self.session.scalar(
            select(func.count(NamingSession.id)).where(*filters)
        )
        histories = await self.session.scalars(
            select(NamingSession)
            .where(*filters)
            .order_by(NamingSession.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(histories), total or 0

    async def get_rounds(self, history_id: str) -> list[NamingRound]:
        result = await self.session.scalars(
            select(NamingRound)
            .where(NamingRound.session_id == history_id)
            .order_by(NamingRound.round_number)
        )
        return list(result)

    async def get_round(
            self, history_id: str, round_number: int) -> NamingRound | None:
        return await self.session.scalar(
            select(NamingRound).where(
                NamingRound.session_id == history_id,
                NamingRound.round_number == round_number,
            )
        )

    async def add_round(
            self,
            history: NamingSession,
            feedback: str,
            names: list[dict],
            commit: bool = True) -> NamingRound:
        last_number = await self.session.scalar(
            select(func.max(NamingRound.round_number)).where(
                NamingRound.session_id == history.id
            )
        ) or 0
        now = datetime.now()
        round_record = NamingRound(
            session_id=history.id,
            round_number=last_number + 1,
            feedback=feedback,
            names=names,
        )
        history.updated_at = now
        history.expires_at = now + timedelta(days=settings.HISTORY_RETENTION_DAYS)
        self.session.add(round_record)
        if commit:
            await self.session.commit()
        return round_record

    async def delete_history(self, history: NamingSession) -> None:
        await self.session.delete(history)
        await self.session.commit()

    async def create_favorite(
            self,
            user_id: int,
            history: NamingSession,
            round_number: int,
            snapshot: dict) -> FavoriteName:
        existing = await self.session.scalar(
            select(FavoriteName).where(
                FavoriteName.user_id == user_id,
                FavoriteName.source_session_id == history.id,
                FavoriteName.source_round_number == round_number,
                FavoriteName.name == snapshot["name"],
            )
        )
        if existing:
            return existing
        favorite = FavoriteName(
            user_id=user_id,
            source_session_id=history.id,
            source_round_number=round_number,
            category=history.category,
            name=snapshot["name"],
            snapshot=snapshot,
        )
        self.session.add(favorite)
        await self.session.commit()
        await self.session.refresh(favorite)
        return favorite

    async def list_favorites(
            self, user_id: int, offset: int, limit: int
    ) -> tuple[list[FavoriteName], int]:
        total = await self.session.scalar(
            select(func.count(FavoriteName.id)).where(FavoriteName.user_id == user_id)
        )
        result = await self.session.scalars(
            select(FavoriteName)
            .where(FavoriteName.user_id == user_id)
            .order_by(FavoriteName.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result), total or 0

    async def get_favorite(
            self, favorite_id: int, user_id: int) -> FavoriteName | None:
        return await self.session.scalar(
            select(FavoriteName).where(
                FavoriteName.id == favorite_id,
                FavoriteName.user_id == user_id,
            )
        )

    async def delete_favorite(self, favorite: FavoriteName) -> None:
        await self.session.delete(favorite)
        await self.session.commit()


def history_conditions(history: NamingSession) -> NameIn:
    extra = history.extra_conditions or {}
    return NameIn(
        category=history.category,
        surname=history.surname,
        gender=history.gender,
        length=history.name_length,
        other=history.other,
        exclude=history.exclude or [],
        use_bazi=bool(extra.get("use_bazi")),
        birth_info=extra.get("birth_info") or "",
        brand_tone=extra.get("brand_tone") or "",
        target_audience=extra.get("target_audience") or "",
        competitors=extra.get("competitors") or "",
        ip_setting=extra.get("ip_setting") or "",
        ip_personality=extra.get("ip_personality") or "",
    )
