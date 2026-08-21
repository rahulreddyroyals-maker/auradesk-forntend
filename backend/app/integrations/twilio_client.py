"""
Thin wrapper around Twilio's REST API for outbound SMS. Inbound replies
to a webhook are sent inline as TwiML (see app/api/v1/sms.py) — this
client is for messages we initiate ourselves, like the follow-up worker.
"""
from twilio.rest import Client

from app.core.config import settings


def send_sms(to: str, body: str) -> str:
    """Returns the Twilio message SID on success."""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(to=to, from_=settings.TWILIO_PHONE_NUMBER, body=body)
    return message.sid
