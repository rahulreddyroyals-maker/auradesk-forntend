import uuid

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    tags: list[str] = Field(default_factory=list)
    lifecycle_stage: str = "lead"


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    tags: list[str] | None = None
    lifecycle_stage: str | None = None


class PatientOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str | None
    phone: str | None
    email: str | None
    tags: list[str]
    lifecycle_stage: str
    source_channel: str | None

    class Config:
        from_attributes = True
