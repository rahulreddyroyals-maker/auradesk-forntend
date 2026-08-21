import uuid
from datetime import datetime

from pydantic import BaseModel


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    channel: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: uuid.UUID
    channel: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    ai_handled: bool
    outcome: str | None
    patient_name: str | None = None

    class Config:
        from_attributes = True


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]
