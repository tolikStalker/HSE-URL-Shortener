import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: str | None = Field(None, min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_-]+$")
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def expires_must_be_in_future(cls, v: datetime | None) -> datetime | None:
        if v is not None and v < datetime.now(UTC):
            msg = "expires_at must be in the future"
            raise ValueError(msg)
        return v


class LinkUpdate(BaseModel):
    original_url: HttpUrl


class LinkResponse(BaseModel):
    id: uuid.UUID
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class LinkStats(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    last_used_at: datetime | None = None
    click_count: int
    expires_at: datetime | None = None
    owner_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}
