import uuid

from pydantic import BaseModel, Field


class AIEmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    voice_id: str | None = None
    personality_prompt: str | None = Field(default=None, max_length=4000)
    status: str | None = Field(default=None, pattern="^(active|paused)$")


class AIEmployeeOut(BaseModel):
    id: uuid.UUID
    name: str
    voice_id: str | None
    personality_prompt: str
    status: str

    class Config:
        from_attributes = True
