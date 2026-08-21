import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class IntegrationUpsert(BaseModel):
    type: str = Field(pattern="^(messenger|instagram)$")
    page_id: str = Field(min_length=1)
    page_access_token: str = Field(min_length=1)


class IntegrationOut(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    connected_at: datetime | None
    # page_access_token intentionally excluded from responses — write-only

    class Config:
        from_attributes = True
