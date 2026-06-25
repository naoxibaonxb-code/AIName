from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class QuotaOut(BaseModel):
    date: date
    daily_limit: int
    used: int
    remaining: int
    paid_remaining: int = 0
    total_remaining: int = 0


class ModelCallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    endpoint: str
    model: str
    success: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    request_id: str | None
    error_type: str | None
    created_at: datetime


class DailyUsageOut(BaseModel):
    date: date
    calls: int
    successful_calls: int
    failed_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AdminUsageSummaryOut(BaseModel):
    days: int
    calls: int
    successful_calls: int
    failed_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    daily: list[DailyUsageOut]


class AdminUsageCallsOut(BaseModel):
    items: list[ModelCallOut]
    total: int
    page: int
    page_size: int
