"""
Tool definitions for the AI Employee orchestrator.

Each tool has two halves: the JSON schema Groq uses to decide when/how to
call it, and the Python function that actually executes it against the
database. Keeping both here (rather than scattering schema in one file
and logic in another) makes it easy to see the model's full capability
surface at a glance.

Booking currently only supports the "internal" scheduling engine
(CalendarConnection.provider == internal) — Google Calendar / Cal.com
sync is a follow-up; check_availability and book_appointment raise a
clear error for clinics on an external provider so the AI can tell the
patient to call the front desk instead of failing silently.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AppointmentStatus,
    BookedBy,
    CalendarConnection,
    CalendarProviderType,
    Escalation,
    KnowledgeBaseArticle,
    Patient,
    Service,
)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_knowledge_base",
            "description": (
                "Search the clinic's knowledge base for pricing, policy, hours, or FAQ "
                "answers. ALWAYS use this before answering any factual question about the "
                "clinic — never answer pricing or policy questions from general knowledge."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The patient's question, in their own words"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_services",
            "description": "List the treatments/services this clinic offers, with duration and price.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check open appointment slots for a service on a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "date": {"type": "string", "description": "ISO date, e.g. 2026-08-15"},
                },
                "required": ["service_name", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment for the patient. Only call this after confirming the exact time with the patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO 8601 datetime"},
                    "patient_first_name": {"type": "string"},
                    "patient_last_name": {"type": "string"},
                    "patient_phone": {"type": "string"},
                },
                "required": ["service_name", "start_time", "patient_first_name", "patient_phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_escalation",
            "description": (
                "Hand this conversation off to a human staff member. Use this for medical "
                "questions outside pricing/scheduling, complaints, anything urgent, or "
                "whenever the patient explicitly asks for a person."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "urgency": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                },
                "required": ["reason"],
            },
        },
    },
]


def _lookup_knowledge_base(db: Session, clinic_id: str, query: str) -> dict:
    like = f"%{query}%"
    articles = (
        db.query(KnowledgeBaseArticle)
        .filter(
            KnowledgeBaseArticle.clinic_id == clinic_id,
            or_(KnowledgeBaseArticle.question.ilike(like), KnowledgeBaseArticle.answer.ilike(like)),
        )
        .limit(5)
        .all()
    )
    # NOTE: keyword search for now — pgvector cosine-similarity retrieval
    # (using the embedding column already on this table) is a follow-up
    # once an embedding provider is wired in; see knowledge_base.py.
    if not articles:
        # Fall back to whole-KB context if no keyword hit — small clinics
        # rarely have more than a few dozen articles, so this stays cheap.
        articles = db.query(KnowledgeBaseArticle).filter(KnowledgeBaseArticle.clinic_id == clinic_id).limit(15).all()
    if not articles:
        return {"found": False, "message": "No knowledge base articles exist for this clinic yet."}
    return {
        "found": True,
        "articles": [{"category": a.category, "question": a.question, "answer": a.answer} for a in articles],
    }


def _list_services(db: Session, clinic_id: str) -> dict:
    services = db.query(Service).filter(Service.clinic_id == clinic_id, Service.active.is_(True)).all()
    return {
        "services": [
            {
                "name": s.name,
                "duration_minutes": s.duration_minutes,
                "price": f"${s.price_cents / 100:.0f}" if s.price_cents else "call for pricing",
            }
            for s in services
        ]
    }


def _get_service_or_none(db: Session, clinic_id: str, service_name: str) -> Service | None:
    return (
        db.query(Service)
        .filter(Service.clinic_id == clinic_id, Service.name.ilike(f"%{service_name}%"), Service.active.is_(True))
        .first()
    )


def _uses_internal_calendar(db: Session, clinic_id: str) -> bool:
    conn = db.query(CalendarConnection).filter(CalendarConnection.clinic_id == clinic_id).first()
    return conn is None or conn.provider == CalendarProviderType.internal


def _check_availability(db: Session, clinic_id: str, service_name: str, date: str) -> dict:
    if not _uses_internal_calendar(db, clinic_id):
        return {
            "available": False,
            "message": "This clinic uses an external calendar this AI can't check yet — tell the patient a staff member will confirm timing.",
        }

    service = _get_service_or_none(db, clinic_id, service_name)
    if not service:
        return {"available": False, "message": f"No service matching '{service_name}' found."}

    try:
        day = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    except ValueError:
        return {"available": False, "message": "Invalid date format, expected YYYY-MM-DD."}

    day_start = day.replace(hour=9, minute=0, second=0, microsecond=0)
    day_end = day.replace(hour=17, minute=0, second=0, microsecond=0)
    duration = timedelta(minutes=service.duration_minutes)

    existing = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.status.in_([AppointmentStatus.booked, AppointmentStatus.confirmed]),
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
        )
        .all()
    )
    busy = [(a.start_time, a.end_time) for a in existing]

    slots = []
    cursor = day_start
    while cursor + duration <= day_end and len(slots) < 6:
        slot_end = cursor + duration
        overlaps = any(cursor < b_end and slot_end > b_start for b_start, b_end in busy)
        if not overlaps:
            slots.append(cursor.strftime("%H:%M"))
        cursor += timedelta(minutes=30)

    return {"available": len(slots) > 0, "service": service.name, "date": date, "open_slots": slots}


def _book_appointment(
    db: Session,
    clinic_id: str,
    service_name: str,
    start_time: str,
    patient_first_name: str,
    patient_phone: str,
    patient_last_name: str | None = None,
    conversation_id: str | None = None,
) -> dict:
    if not _uses_internal_calendar(db, clinic_id):
        return {"booked": False, "message": "This clinic's calendar isn't handled by this AI yet — escalate instead."}

    service = _get_service_or_none(db, clinic_id, service_name)
    if not service:
        return {"booked": False, "message": f"No service matching '{service_name}' found."}

    try:
        start = datetime.fromisoformat(start_time)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    except ValueError:
        return {"booked": False, "message": "Invalid start_time format, expected ISO 8601."}

    end = start + timedelta(minutes=service.duration_minutes)

    conflict = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.status.in_([AppointmentStatus.booked, AppointmentStatus.confirmed]),
            Appointment.start_time < end,
            Appointment.end_time > start,
        )
        .first()
    )
    if conflict:
        return {"booked": False, "message": "That slot is no longer available — offer the patient a different time."}

    patient = (
        db.query(Patient)
        .filter(Patient.clinic_id == clinic_id, Patient.phone == patient_phone)
        .first()
    )
    if not patient:
        patient = Patient(
            clinic_id=clinic_id,
            first_name=patient_first_name,
            last_name=patient_last_name,
            phone=patient_phone,
            source_channel="web_chat",
            lifecycle_stage="lead",
        )
        db.add(patient)
        db.flush()
    elif patient.first_name == "Unknown":
        # Patient row was created from an inbound SMS before we had a name —
        # now that they're booking, fill in the real name.
        patient.first_name = patient_first_name
        patient.last_name = patient_last_name

    appointment = Appointment(
        clinic_id=clinic_id,
        patient_id=patient.id,
        conversation_id=conversation_id,
        service_id=service.id,
        start_time=start,
        end_time=end,
        status=AppointmentStatus.booked,
        booked_by=BookedBy.ai,
    )
    db.add(appointment)
    db.commit()

    return {
        "booked": True,
        "service": service.name,
        "start_time": start.isoformat(),
        "patient": f"{patient_first_name} {patient_last_name or ''}".strip(),
    }


def _create_escalation(
    db: Session, clinic_id: str, conversation_id: str, reason: str, urgency: str = "normal"
) -> dict:
    from app.core.safe_logging import log_event, redact_exception
    from app.integrations.twilio_client import send_sms
    from app.models import Staff

    notified_ids: list[str] = []
    staff_to_notify = (
        db.query(Staff)
        .filter(Staff.clinic_id == clinic_id, Staff.phone.isnot(None))
        .all()
    )
    for staff in staff_to_notify:
        prefs = staff.notification_prefs_json or {}
        if not prefs.get("sms", True):
            continue
        try:
            send_sms(
                staff.phone,
                f"AuraDesk: a conversation needs you — {reason} (urgency: {urgency}). "
                "Check the Inbox to respond.",
            )
            notified_ids.append(str(staff.id))
        except Exception as exc:  # noqa: BLE001 — one failed notification shouldn't block the escalation record
            log_event("staff_notification_failed", staff_id=str(staff.id), error_type=redact_exception(exc))

    escalation = Escalation(
        conversation_id=conversation_id,
        clinic_id=clinic_id,
        reason=reason,
        urgency=urgency,
        notified_staff_ids=notified_ids,
        created_at=datetime.now(timezone.utc),
    )
    db.add(escalation)
    db.commit()
    return {"escalated": True, "reason": reason, "urgency": urgency, "staff_notified": len(notified_ids)}


def execute_tool_call(
    db: Session, clinic_id: str, conversation_id: str, name: str, arguments: dict
) -> dict:
    if name == "lookup_knowledge_base":
        return _lookup_knowledge_base(db, clinic_id, arguments["query"])
    if name == "list_services":
        return _list_services(db, clinic_id)
    if name == "check_availability":
        return _check_availability(db, clinic_id, arguments["service_name"], arguments["date"])
    if name == "book_appointment":
        return _book_appointment(
            db,
            clinic_id,
            arguments["service_name"],
            arguments["start_time"],
            arguments["patient_first_name"],
            arguments["patient_phone"],
            arguments.get("patient_last_name"),
            conversation_id,
        )
    if name == "create_escalation":
        return _create_escalation(
            db, clinic_id, conversation_id, arguments["reason"], arguments.get("urgency", "normal")
        )
    return {"error": f"Unknown tool: {name}"}
