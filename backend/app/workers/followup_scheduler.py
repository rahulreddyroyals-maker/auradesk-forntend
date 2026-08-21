"""
Finds conversations that went quiet without resulting in a booking, and
sends one SMS follow-up per patient. Run this periodically — there's no
job queue/scheduler infra yet (that's a reasonable Celery/APScheduler
upgrade once volume justifies it), so for now:

  Windows: Task Scheduler -> run `python -m app.workers.followup_scheduler`
           on whatever cadence you want (e.g. every 30 minutes).
  Linux/Mac: a cron entry doing the same.

Idempotency: a conversation is only followed up once — after sending,
we set ended_at and outcome=no_action so it won't be picked up again.
This is a blunt instrument (one follow-up, ever, per conversation) by
design for Phase 3; smarter cadences (e.g. a second nudge after 24h) are
a natural follow-up once this is proven out.
"""
from datetime import datetime, timedelta, timezone

from app.core.safe_logging import log_event, redact_exception
from app.db.session import AdminSessionLocal
from app.integrations.twilio_client import send_sms
from app.models import (
    Conversation,
    ConversationOutcome,
    ConversationStatus,
    ChannelType,
    Patient,
)

QUIET_THRESHOLD = timedelta(hours=2)
FOLLOW_UP_MESSAGE = (
    "Hi! Just checking in — were you still interested in booking? "
    "Reply here anytime and we'll get you set up, or let us know if you have questions."
)


def run() -> int:
    """Returns the number of follow-ups sent."""
    db = AdminSessionLocal()
    sent = 0
    try:
        cutoff = datetime.now(timezone.utc) - QUIET_THRESHOLD
        stale_conversations = (
            db.query(Conversation)
            .filter(
                Conversation.status == ConversationStatus.active,
                Conversation.ai_handled.is_(True),
                Conversation.channel.in_([ChannelType.sms, ChannelType.web_chat]),
                Conversation.started_at < cutoff,
                Conversation.outcome.is_(None),
            )
            .all()
        )

        for conv in stale_conversations:
            if not conv.patient_id:
                continue
            patient = db.get(Patient, conv.patient_id)
            if not patient or not patient.phone:
                continue

            try:
                send_sms(patient.phone, FOLLOW_UP_MESSAGE)
                sent += 1
            except Exception as exc:  # noqa: BLE001 — log and continue, one bad number shouldn't stop the batch
                log_event("followup_send_failed", conversation_id=str(conv.id), error_type=redact_exception(exc))
                continue

            conv.outcome = ConversationOutcome.no_action
            conv.ended_at = datetime.now(timezone.utc)
            db.commit()

        return sent
    finally:
        db.close()


if __name__ == "__main__":
    count = run()
    log_event("followup_batch_completed", messages_sent=count)
