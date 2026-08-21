import uuid
from datetime import datetime

from pydantic import BaseModel


class EscalationOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    reason: str
    urgency: str
    resolved: bool
    created_at: datetime
    patient_name: str | None = None

    class Config:
        from_attributes = True
