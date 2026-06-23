from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class NamingSession(Base):
    __tablename__ = "naming_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    surname: Mapped[str] = mapped_column(String(20), default="")
    gender: Mapped[str] = mapped_column(String(10), default="不限")
    name_length: Mapped[str] = mapped_column(String(10), default="不限")
    other: Mapped[str] = mapped_column(Text, default="")
    exclude: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class NamingRound(Base):
    __tablename__ = "naming_round"
    __table_args__ = (
        UniqueConstraint("session_id", "round_number", name="uq_naming_round_session_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("naming_session.id", ondelete="CASCADE"), index=True
    )
    round_number: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    names: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now()
    )


class FavoriteName(Base):
    __tablename__ = "favorite_name"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    source_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_round_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100), index=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now()
    )
