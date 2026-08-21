import uuid
from datetime import datetime

from pydantic import BaseModel


class LogEntry(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    channel: str
    created_at: datetime
    tool: str
    arguments: dict
    result: dict
