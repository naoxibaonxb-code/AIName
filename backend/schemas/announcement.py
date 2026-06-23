from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AnnouncementType = Literal["info", "notice", "warning"]


class AnnouncementIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1, max_length=1000)
    type: AnnouncementType = "info"
    is_active: bool = True
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class AnnouncementUpdateIn(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    content: str | None = Field(None, min_length=1, max_length=1000)
    type: AnnouncementType | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    type: str
    is_active: bool
    starts_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnnouncementPageOut(BaseModel):
    items: list[AnnouncementOut]
    total: int
    page: int
    page_size: int
