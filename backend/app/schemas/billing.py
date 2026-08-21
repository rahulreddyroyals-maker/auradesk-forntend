import uuid
from datetime import datetime

from pydantic import BaseModel


class SubscriptionOut(BaseModel):
    status: str
    plan: str | None
    current_period_end: datetime | None


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str
