from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PaymentOrder(Base):
    __tablename__ = "payment_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    out_trade_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    trade_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(120))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(30), default="created", index=True)
    product_code: Mapped[str] = mapped_column(String(40), default="generation_credit", server_default="generation_credit")
    credit_amount: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    buyer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    benefit_granted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_notify: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, server_default=func.now()
    )
