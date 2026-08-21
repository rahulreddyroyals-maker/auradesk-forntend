import uuid
from datetime import datetime

from pydantic import BaseModel


class AppointmentOut(BaseModel):
    id: uuid.UUID
    patient_name: str
    service_name: str
    start_time: datetime
    end_time: datetime
    status: str
    booked_by: str

    class Config:
        from_attributes = True


class AppointmentStatusUpdate(BaseModel):
    status: str
