from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.agent import NameSchema
from schemas.name import CategoryLiteral, NameIn


class NamingRoundOut(BaseModel):
    id: int
    round_number: int
    feedback: str | None
    names: list[NameSchema]
    created_at: datetime


class NamingHistorySummaryOut(BaseModel):
    id: str
    category: CategoryLiteral
    conditions: NameIn
    latest_names: list[NameSchema]
    round_count: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class NamingHistoryDetailOut(NamingHistorySummaryOut):
    rounds: list[NamingRoundOut]


class NamingHistoryPageOut(BaseModel):
    items: list[NamingHistorySummaryOut]
    total: int
    page: int
    page_size: int


class FavoriteCreateIn(BaseModel):
    session_id: str
    round_number: int = Field(..., ge=1)
    name_index: int = Field(..., ge=0, le=20)


class FavoriteNameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_session_id: str | None
    source_round_number: int | None
    category: str
    name: str
    snapshot: NameSchema
    created_at: datetime


class FavoritePageOut(BaseModel):
    items: list[FavoriteNameOut]
    total: int
    page: int
    page_size: int
