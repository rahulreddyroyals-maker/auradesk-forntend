from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.api.deps import AuthedSession, get_current_session
from app.models import (
    Appointment,
    AppointmentStatus,
    ChannelType,
    Conversation,
    ConversationOutcome,
    ConversationStatus,
    Message,
    MessageRole,
    Service,
)
from app.schemas.analytics import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(session: AuthedSession = Depends(get_current_session)) -> AnalyticsSummary:
    db = session.db
    clinic_id = session.claims.clinic_id
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    today_conversations = (
        db.query(Conversation)
        .filter(Conversation.clinic_id == clinic_id, Conversation.started_at >= today_start)
        .all()
    )
    calls_today = sum(1 for c in today_conversations if c.channel == ChannelType.voice)
    texts_today = sum(1 for c in today_conversations if c.channel == ChannelType.sms)
    chats_today = sum(
        1 for c in today_conversations if c.channel in (ChannelType.web_chat, ChannelType.messenger, ChannelType.instagram)
    )
    missed_leads_today = sum(
        1 for c in today_conversations if c.outcome in (ConversationOutcome.no_action, ConversationOutcome.lost)
    )

    appointments_today = (
        db.query(Appointment)
        .filter(Appointment.clinic_id == clinic_id, Appointment.created_at >= today_start, Appointment.booked_by == "ai")
        .all()
    )
    booked_today = len(appointments_today)
    revenue_today_cents = 0
    for appt in appointments_today:
        service = db.get(Service, appt.service_id)
        if service and service.price_cents:
            revenue_today_cents += service.price_cents

    upcoming_appointments = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.start_time >= now,
            Appointment.status.in_([AppointmentStatus.booked, AppointmentStatus.confirmed]),
        )
        .count()
    )

    week_conversations = (
        db.query(Conversation)
        .filter(Conversation.clinic_id == clinic_id, Conversation.started_at >= week_ago)
        .all()
    )
    total_conversations_7d = len(week_conversations)
    booked_7d = sum(1 for c in week_conversations if c.outcome == ConversationOutcome.booked)
    conversion_rate_7d = (booked_7d / total_conversations_7d) if total_conversations_7d else 0.0

    # Average response time: gap between each patient message and the next AI
    # message that follows it, within today's conversations.
    today_conv_ids = [c.id for c in today_conversations]
    response_gaps = []
    if today_conv_ids:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id.in_(today_conv_ids))
            .order_by(Message.conversation_id, Message.created_at)
            .all()
        )
        by_conv: dict = {}
        for m in messages:
            by_conv.setdefault(m.conversation_id, []).append(m)
        for conv_messages in by_conv.values():
            for i in range(len(conv_messages) - 1):
                cur, nxt = conv_messages[i], conv_messages[i + 1]
                if cur.role == MessageRole.patient and nxt.role == MessageRole.ai:
                    response_gaps.append((nxt.created_at - cur.created_at).total_seconds())
    avg_response_seconds = sum(response_gaps) / len(response_gaps) if response_gaps else None

    return AnalyticsSummary(
        calls_today=calls_today,
        texts_today=texts_today,
        chats_today=chats_today,
        booked_today=booked_today,
        missed_leads_today=missed_leads_today,
        revenue_today_cents=revenue_today_cents,
        upcoming_appointments=upcoming_appointments,
        conversion_rate_7d=round(conversion_rate_7d, 4),
        avg_response_seconds=round(avg_response_seconds, 1) if avg_response_seconds is not None else None,
        total_conversations_7d=total_conversations_7d,
    )
