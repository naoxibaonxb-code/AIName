from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class AlipaySandboxCreateIn(BaseModel):
    subject: str = Field(default="AIName 生成机会 x1", max_length=120)
    total_amount: Annotated[Decimal, Field(gt=0, le=9999)] = Decimal("0.01")


class PaymentOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    out_trade_no: str
    trade_no: str | None
    subject: str
    total_amount: Decimal
    status: str
    product_code: str
    credit_amount: int
    benefit_granted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None


class AlipaySandboxCreateOut(BaseModel):
    order: PaymentOrderOut
    pay_url: str
    mode: Literal["sandbox"] = "sandbox"


class AlipayReturnOut(BaseModel):
    out_trade_no: str
    trade_no: str | None = None
    verified: bool
    message: str
