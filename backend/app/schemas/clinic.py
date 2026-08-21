import uuid

from pydantic import BaseModel, Field


class ClinicUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = None
    address: str | None = None
    timezone: str | None = None


class ClinicOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    phone_number: str | None
    address: str | None
    timezone: str

    class Config:
        from_attributes = True
