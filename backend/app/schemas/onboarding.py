from pydantic import BaseModel, Field


class OnboardClinicRequest(BaseModel):
    clinic_name: str = Field(min_length=1, max_length=255)
    owner_name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(default="America/New_York")


class OnboardClinicResponse(BaseModel):
    clinic_id: str
    clinic_name: str
    slug: str
