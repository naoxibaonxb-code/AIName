from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class DailyGenerationUsage(Base):
    __tablename__ = "daily_generation_usage"
    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_daily_generation_usage_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    usage_date: Mapped[date] = mapped_column(Date, index=True)
    successful_generations: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, server_default=func.now()
    )


class ModelCallUsage(Base):
    __tablename__ = "model_call_usage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    endpoint: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(50), default="deepseek-chat")
    success: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), index=True
    )


class GenerationCredit(Base):
    __tablename__ = "generation_credit"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_generation_credit_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="alipay_sandbox", server_default="alipay_sandbox")
    source_id: Mapped[str] = mapped_column(String(80), index=True)
    total_credits: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    remaining_credits: Mapped[int] = mapped_column(Integer, default=1, server_default="1", index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, server_default=func.now()
    )
