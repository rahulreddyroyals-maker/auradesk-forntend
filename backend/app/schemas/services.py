import uuid

from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = None
    duration_minutes: int = Field(default=30, ge=5, le=480)
    price_cents: int | None = Field(default=None, ge=0)
    description: str | None = None


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    price_cents: int | None = Field(default=None, ge=0)
    description: str | None = None
    active: bool | None = None


class ServiceOut(BaseModel):
    id: uuid.UUID
    name: str
    category: str | None
    duration_minutes: int
    price_cents: int | None
    description: str | None
    active: bool

    class Config:
        from_attributes = True
