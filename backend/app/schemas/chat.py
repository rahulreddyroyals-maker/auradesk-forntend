import uuid

from pydantic import BaseModel, Field


class TestMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None


class TestMessageResponse(BaseModel):
    conversation_id: uuid.UUID
    reply: str
    escalated: bool
