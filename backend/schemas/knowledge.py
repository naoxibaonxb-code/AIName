from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict


class KnowledgeFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    original_name: str
    scope: str
    status: str
    error_message: str | None
    file_size: int
    chunk_count: int
    is_enabled: bool
    uploaded_at: datetime


class KnowledgeFileUpdateIn(BaseModel):
    is_enabled: bool


class KnowledgeStatsOut(BaseModel):
    private_total: int
    private_ready: int
    public_total: int
    public_ready: int


KnowledgeScope = Literal["private", "public"]
