import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class KBArticleCreate(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=5000)


class KBArticleUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=100)
    question: str | None = Field(default=None, min_length=1, max_length=1000)
    answer: str | None = Field(default=None, min_length=1, max_length=5000)


class KBArticleOut(BaseModel):
    id: uuid.UUID
    category: str
    question: str
    answer: str
    source: str
    updated_at: datetime
    embedded: bool = Field(description="Whether an embedding has been generated for this article yet")

    class Config:
        from_attributes = True
