import uuid

from pydantic import BaseModel, EmailStr, Field


class StaffOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    phone: str | None
    email: str | None


class InviteRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(default="front_desk", pattern="^(owner|admin|front_desk)$")


class StaffRoleUpdate(BaseModel):
    role: str = Field(pattern="^(owner|admin|front_desk)$")
