"""
Self-serve sales demo: a standing fictional clinic ("Glow Aesthetic
Studio") that can be shared with prospects as a working login, plus a
secret, re-runnable reseed endpoint that refreshes its "activity" so the
dashboard always looks like it happened in the last few days — not like
a demo that was seeded once in March and never touched again.

Two endpoints:

  GET  /demo/info     Public. Returns the clinic name + login email/
                       password so the frontend's public /demo page can
                       display them with copy buttons. No secret, no
                       auth — safe to expose to anyone with the link.

  POST /demo/reseed    Protected by a secret header (X-Demo-Token, must
                       match settings.DEMO_RESEED_TOKEN). Wipes and
                       regenerates the demo clinic's "activity" data
                       (patients, conversations, messages, calls,
                       escalations, appointments, subscription) anchored
                       to datetime.now(timezone.utc) at call time, and
                       creates-or-finds the stable config data (the
                       Supabase Auth login, the Clinic/Staff/AIEmployee
                       rows, Services, Knowledge Base articles) so login
                       credentials never change across reseeds. Disabled
                       (503) if DEMO_RESEED_TOKEN isn't set — fails
                       closed, never open.

Run this once after deploying, then again before any client call that's
more than a day or two after the last reseed, so "today" on the
dashboard really does mean today. See DEMO_GUIDE.md for the exact curl
command and a narration script.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete

from app.core.config import settings
from app.db.session import AdminSessionLocal
from app.integrations.supabase_admin import get_or_create_user_with_password
from app.models.conversations import (
    Call,
    ChannelType,
    Conversation,
    ConversationOutcome,
    ConversationStatus,
    Message,
    MessageRole,
)
from app.models.knowledge_base import KnowledgeBaseArticle
from app.models.ops import Escalation, Subscription
from app.models.patients import Patient
from app.models.scheduling import Appointment, AppointmentStatus, BookedBy, Service
from app.models.tenancy import AIEmployee, Clinic, ClinicStatus, Staff, StaffRole

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_SLUG = "glow-aesthetic-studio-demo"


# ---------------------------------------------------------------------------
# GET /demo/info — public, read-only
# ---------------------------------------------------------------------------


class DemoInfoResponse(BaseModel):
    clinic_name: str
    login_email: str
    login_password: str
    note: str


@router.get("/info", response_model=DemoInfoResponse)
def demo_info() -> DemoInfoResponse:
    return DemoInfoResponse(
        clinic_name=settings.DEMO_CLINIC_NAME,
        login_email=settings.DEMO_LOGIN_EMAIL,
        login_password=settings.DEMO_LOGIN_PASSWORD,
        note=(
            "This is a live, fully-populated demo account — not screenshots. "
            "Log in and explore the dashboard, conversations, calls, appointments and "
            "knowledge base exactly as a real clinic owner would see them."
        ),
    )


# ---------------------------------------------------------------------------
# POST /demo/reseed — secret-protected, destructive (scoped to the demo clinic only)
# ---------------------------------------------------------------------------


class DemoReseedResponse(BaseModel):
    status: str
    clinic_id: str
    counts: dict


def _require_demo_token(x_demo_token: str | None) -> None:
    if not settings.DEMO_RESEED_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo reseeding is not configured on this server (DEMO_RESEED_TOKEN unset).",
        )
    if not x_demo_token or x_demo_token != settings.DEMO_RESEED_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing demo token.")


@router.post("/reseed", response_model=DemoReseedResponse)
def demo_reseed(x_demo_token: str | None = Header(default=None)) -> DemoReseedResponse:
    _require_demo_token(x_demo_token)

    now = datetime.now(timezone.utc)
    db = AdminSessionLocal()
    try:
        # Order matters: wipe the old story data (appointments RESTRICT-
        # reference services) BEFORE replacing services, or deleting services
        # while old appointments still point at them raises a FK violation.
        clinic = _ensure_clinic_and_staff(db, now)
        _wipe_story_data(db, clinic.id)
        services = _replace_services_and_kb(db, clinic, now)
        counts = _seed_story_data(db, clinic, services, now)
        db.commit()
        return DemoReseedResponse(status="ok", clinic_id=str(clinic.id), counts=counts)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Config data: found-or-created / fully replaced each call. Stable across
# reseeds so the login never changes. Uses the admin (RLS-bypassing)
# connection deliberately — same reasoning as onboarding.py's clinic
# creation: there's no single clinic_id claim to scope this call by,
# since this endpoint doesn't run inside an authenticated request at all.
# ---------------------------------------------------------------------------


def _ensure_clinic_and_staff(db, now: datetime) -> Clinic:
    # --- Supabase Auth user (stable id, password never reset on repeat calls) ---
    user_id = get_or_create_user_with_password(settings.DEMO_LOGIN_EMAIL, settings.DEMO_LOGIN_PASSWORD)

    # --- Clinic ---
    clinic = db.query(Clinic).filter(Clinic.slug == DEMO_SLUG).first()
    if not clinic:
        clinic = Clinic(slug=DEMO_SLUG)
        db.add(clinic)
    clinic.name = settings.DEMO_CLINIC_NAME
    clinic.timezone = "America/New_York"
    clinic.phone_number = "+1 (555) 014-7788"
    clinic.address = "482 Magnolia Ave, Austin, TX 78701"
    clinic.hours_json = {
        "mon": ["09:00", "19:00"],
        "tue": ["09:00", "19:00"],
        "wed": ["09:00", "19:00"],
        "thu": ["09:00", "19:00"],
        "fri": ["09:00", "19:00"],
        "sat": ["10:00", "16:00"],
        "sun": [],
    }
    clinic.branding_json = {"primary_color": "#C9A86A"}
    clinic.status = ClinicStatus.active
    db.flush()  # ensure clinic.id exists before dependent rows

    # --- Staff (the owner persona shown as "logged in as") ---
    staff = db.query(Staff).filter(Staff.user_id == uuid.UUID(user_id)).first()
    if not staff:
        staff = Staff(clinic_id=clinic.id, user_id=uuid.UUID(user_id))
        db.add(staff)
    staff.clinic_id = clinic.id
    staff.name = "Jordan Reyes"
    staff.role = StaffRole.owner
    staff.phone = "+1 (555) 014-7799"
    db.flush()

    # --- AI Employee ---
    ai_employee = db.query(AIEmployee).filter(AIEmployee.clinic_id == clinic.id).first()
    if not ai_employee:
        ai_employee = AIEmployee(clinic_id=clinic.id)
        db.add(ai_employee)
    ai_employee.name = "Aura"
    ai_employee.voice_id = "warm-professional-female-01"
    ai_employee.personality_prompt = (
        "You are Aura, the friendly AI front-desk employee for Glow Aesthetic Studio, a med spa in Austin, TX. "
        "Warm, concise, never pushy. Answer pricing/policy/hours questions from the knowledge base, help patients "
        "book or reschedule appointments, and escalate to staff immediately for anything urgent, medical, or "
        "clearly outside what you're confident answering."
    )
    ai_employee.escalation_rules_json = {
        "escalate_on_keywords": ["allergic reaction", "in pain", "emergency", "complication", "refund", "lawyer"],
        "escalate_after_failed_attempts": 2,
    }
    ai_employee.active_hours_json = clinic.hours_json
    ai_employee.status = "active"
    db.flush()

    return clinic


def _wipe_story_data(db, clinic_id) -> None:
    """
    Deletes everything from the previous reseed that depends on a specific
    row of config data (services, via Appointment's RESTRICT FK) or that's
    simply "activity" meant to be regenerated fresh every call. Must run
    BEFORE _replace_services_and_kb, or deleting a service that an old
    appointment still points to raises a FK violation. Order here respects
    the remaining FKs: escalations -> appointments -> messages (by
    conversation_id) -> calls (by conversation_id) -> conversations ->
    patients -> subscription.
    """
    conv_ids_subq = db.query(Conversation.id).filter(Conversation.clinic_id == clinic_id).subquery()

    db.query(Escalation).filter(Escalation.clinic_id == clinic_id).delete(synchronize_session=False)
    db.query(Appointment).filter(Appointment.clinic_id == clinic_id).delete(synchronize_session=False)
    db.execute(delete(Message).where(Message.conversation_id.in_(conv_ids_subq)))
    db.execute(delete(Call).where(Call.conversation_id.in_(conv_ids_subq)))
    db.query(Conversation).filter(Conversation.clinic_id == clinic_id).delete(synchronize_session=False)
    db.query(Patient).filter(Patient.clinic_id == clinic_id).delete(synchronize_session=False)
    db.query(Subscription).filter(Subscription.clinic_id == clinic_id).delete(synchronize_session=False)
    db.flush()


def _replace_services_and_kb(db, clinic: Clinic, now: datetime) -> dict:
    """Fully replaces Service and KnowledgeBaseArticle rows. Safe to call only
    after _wipe_story_data has cleared any appointments referencing the old
    service rows."""
    # --- Services: fully replace (simple, keeps prices/durations always in sync with this file) ---
    db.query(Service).filter(Service.clinic_id == clinic.id).delete()
    db.flush()
    service_defs = [
        ("Botox / Neuromodulator", "injectables", 30, 45000, "Smooths fine lines and wrinkles; results in 3-7 days."),
        ("Lip Filler", "injectables", 45, 65000, "Hyaluronic acid filler for natural-looking volume and shape."),
        ("HydraFacial", "facial", 50, 19900, "Deep cleanse, exfoliation, and hydration — no downtime."),
        ("Laser Hair Removal — Underarms", "laser", 20, 12000, "Series of 6-8 sessions recommended for best results."),
        ("Chemical Peel", "skin", 40, 17500, "Resurfacing treatment for tone, texture, and mild sun damage."),
        ("Microneedling with PRP", "skin", 60, 45000, "Collagen-stimulating treatment using the patient's own plasma."),
    ]
    services: dict[str, Service] = {}
    for name, category, duration, price, desc in service_defs:
        svc = Service(
            clinic_id=clinic.id, name=name, category=category, duration_minutes=duration,
            price_cents=price, description=desc, active=True,
        )
        db.add(svc)
        services[name] = svc
    db.flush()

    # --- Knowledge base: fully replace ---
    db.query(KnowledgeBaseArticle).filter(KnowledgeBaseArticle.clinic_id == clinic.id).delete()
    db.flush()
    kb_defs = [
        ("pricing", "How much does Botox cost?",
         "Botox/neuromodulator treatments start at $450 per session, depending on the number of units needed. "
         "We'll confirm an exact quote at your consultation."),
        ("pricing", "Do you offer payment plans or financing?",
         "Yes — we partner with Cherry and CareCredit for 0% and low-interest financing on treatments over $300."),
        ("hours", "What are your hours?",
         "We're open Monday-Friday 9am-7pm and Saturday 10am-4pm. We're closed Sundays."),
        ("policy", "What is your cancellation policy?",
         "We ask for at least 24 hours' notice to cancel or reschedule. Cancellations within 24 hours may incur "
         "a $50 fee, which is waived for your first missed appointment."),
        ("service", "How long does a HydraFacial take?",
         "A standard HydraFacial takes about 50 minutes, with no downtime afterward — you can go straight back "
         "to your day."),
        ("service", "Is laser hair removal painful?",
         "Most patients describe it as a quick snapping sensation, similar to a rubber band — mild, brief, and "
         "well tolerated. We use a cooling tip to minimize discomfort."),
        ("policy", "Do I need a consultation before my first treatment?",
         "Yes, for injectables (Botox, filler) and laser treatments we require a brief complimentary consultation "
         "first so your provider can assess your goals and skin. Facials and peels can be booked directly."),
        ("general", "Do you accept walk-ins?",
         "We're appointment-based to make sure every patient gets their provider's full attention, but we're "
         "happy to fit in same-day requests when there's availability — just call or text us."),
        ("service", "How many sessions of laser hair removal will I need?",
         "Most patients see the best results after 6-8 sessions spaced about 4-6 weeks apart, since hair grows "
         "in cycles. We'll build a plan at your consultation."),
    ]
    now_ts = now
    for category, question, answer in kb_defs:
        db.add(KnowledgeBaseArticle(
            clinic_id=clinic.id, category=category, question=question, answer=answer,
            embedding=None, source="manual", updated_at=now_ts,
        ))
    db.flush()

    return services


# ---------------------------------------------------------------------------
# Story data: regenerated every call (the previous version was already
# wiped by _wipe_story_data), anchored to `now` so the dashboard's live
# "today"/"7-day" metrics always look fresh.
# ---------------------------------------------------------------------------


def _seed_story_data(db, clinic: Clinic, services: dict, now: datetime) -> dict:
    clinic_id = clinic.id

    def at(days_ago: int, hour: int, minute: int = 0) -> datetime:
        d = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        return d

    def patient(first, last, phone, email, source, stage, tags=None):
        p = Patient(
            clinic_id=clinic_id, first_name=first, last_name=last, phone=phone, email=email,
            source_channel=source, tags=tags or [], lifecycle_stage=stage,
            last_contacted_at=now, external_ids_json={},
        )
        db.add(p)
        db.flush()
        return p

    patients = {
        "sophia": patient("Sophia", "Chen", "+15125550101", "sophia.chen@example.com", "voice", "lead", ["injectables"]),
        "olivia": patient("Olivia", "Martinez", "+15125550102", "olivia.martinez@example.com", "sms", "lead", ["laser"]),
        "mia": patient("Mia", "Johnson", "+15125550103", "mia.johnson@example.com", "sms", "patient"),
        "emma": patient("Emma", "Larson", "+15125550104", "emma.larson@example.com", "web_chat", "lead"),
        "harper": patient("Harper", "Wilson", "+15125550105", "harper.wilson@example.com", "messenger", "lead"),
        "ava": patient("Ava", "Thompson", "+15125550106", "ava.thompson@example.com", "messenger", "patient"),
        "isabella": patient("Isabella", "Rodriguez", "+15125550107", "isabella.rodriguez@example.com", "instagram", "lead"),
        "charlotte": patient("Charlotte", "Davis", "+15125550108", "charlotte.davis@example.com", "web_chat", "lead"),
        "amelia": patient("Amelia", "Garcia", "+15125550109", "amelia.garcia@example.com", "voice", "patient"),
        "evelyn": patient("Evelyn", "Brown", "+15125550110", "evelyn.brown@example.com", "instagram", "patient"),
    }

    def conversation(patient_key, channel, days_ago, hour, minute, outcome, status_=ConversationStatus.resolved,
                      escalated_to_staff_id=None, ended_offset_min=6):
        started = at(days_ago, hour, minute)
        c = Conversation(
            clinic_id=clinic_id, patient_id=patients[patient_key].id, channel=channel, status=status_,
            started_at=started, ended_at=started + timedelta(minutes=ended_offset_min),
            ai_handled=escalated_to_staff_id is None, escalated_to_staff_id=escalated_to_staff_id, outcome=outcome,
        )
        db.add(c)
        db.flush()
        return c

    def msg(conv, role, channel, content, minute_offset, tool_calls=None):
        db.add(Message(
            conversation_id=conv.id, role=role, channel=channel, content=content,
            tool_calls_json=tool_calls or [], created_at=conv.started_at + timedelta(minutes=minute_offset),
        ))

    def tool_call(tool, arguments, result):
        return {"tool": tool, "arguments": arguments, "result": result}

    staff = db.query(Staff).filter(Staff.clinic_id == clinic_id).first()

    # ---- 1. Sophia Chen — voice, today, booked Botox ----
    c1 = conversation("sophia", ChannelType.voice, 0, 9, 14, ConversationOutcome.booked)
    db.add(Call(
        conversation_id=c1.id, twilio_call_sid=f"CA{uuid.uuid4().hex[:30]}", direction="inbound",
        duration_seconds=312, recording_url=None, sentiment="positive", created_at=c1.started_at,
    ))
    msg(c1, MessageRole.patient, ChannelType.voice, "Hi, I wanted to see if I could get in for Botox sometime this week.", 0)
    msg(c1, MessageRole.ai, ChannelType.voice, "Of course! I can check availability for Botox with one of our providers this week — do you have a day that works best?", 1,
        [tool_call("list_services", {"category": "injectables"}, {"found": True, "count": 6})])
    msg(c1, MessageRole.patient, ChannelType.voice, "Thursday afternoon if possible.", 2)
    msg(c1, MessageRole.ai, ChannelType.voice, "I have 2:00pm Thursday open for a Botox appointment, 30 minutes. Want me to book that for you?", 3,
        [tool_call("check_availability", {"service": "Botox / Neuromodulator", "day": "Thursday"}, {"slots": ["14:00", "16:30"]})])
    msg(c1, MessageRole.patient, ChannelType.voice, "Yes, let's do 2pm Thursday.", 4)
    msg(c1, MessageRole.ai, ChannelType.voice, "You're all set for Thursday at 2:00pm for Botox. You'll get a text confirmation shortly!", 5,
        [tool_call("book_appointment", {"patient": "Sophia Chen", "service": "Botox / Neuromodulator", "start_time": "Thursday 14:00"}, {"status": "booked"})])

    # ---- 2. Olivia Martinez — sms, today, booked laser hair removal ----
    c2 = conversation("olivia", ChannelType.sms, 0, 11, 2, ConversationOutcome.booked, ended_offset_min=4)
    msg(c2, MessageRole.patient, ChannelType.sms, "hey do you guys do laser hair removal for underarms? how much", 0)
    msg(c2, MessageRole.ai, ChannelType.sms, "Yes! Underarm laser hair removal is $120/session, about 20 minutes. Most people do 6-8 sessions for lasting results. Want me to find you a time?", 1,
        [tool_call("lookup_knowledge_base", {"query": "laser hair removal sessions"}, {"found": True, "count": 1})])
    msg(c2, MessageRole.patient, ChannelType.sms, "yes! this week if u have anything", 2)
    msg(c2, MessageRole.ai, ChannelType.sms, "I've got Friday 10:30am open — want that one?", 3,
        [tool_call("check_availability", {"service": "Laser Hair Removal — Underarms", "day": "Friday"}, {"slots": ["10:30"]})])
    msg(c2, MessageRole.patient, ChannelType.sms, "perfect, book it", 4)
    msg(c2, MessageRole.ai, ChannelType.sms, "Booked! Friday 10:30am for underarm laser hair removal. See you then 😊", 4,
        [tool_call("book_appointment", {"patient": "Olivia Martinez", "service": "Laser Hair Removal — Underarms", "start_time": "Friday 10:30"}, {"status": "booked"})])

    # ---- 3. Mia Johnson — sms, today, faq only ----
    c3 = conversation("mia", ChannelType.sms, 0, 13, 40, ConversationOutcome.faq_only, ended_offset_min=2)
    msg(c3, MessageRole.patient, ChannelType.sms, "are you open on sundays?", 0)
    msg(c3, MessageRole.ai, ChannelType.sms, "We're closed Sundays — open Mon-Fri 9am-7pm and Sat 10am-4pm. Want me to help you find a time this week?", 1,
        [tool_call("lookup_knowledge_base", {"query": "hours"}, {"found": True, "count": 1})])
    msg(c3, MessageRole.patient, ChannelType.sms, "no just checking thanks", 2)

    # ---- 4. Emma Larson — web_chat, today, no_action (missed lead) ----
    c4 = conversation("emma", ChannelType.web_chat, 0, 15, 5, ConversationOutcome.no_action,
                       status_=ConversationStatus.abandoned, ended_offset_min=3)
    msg(c4, MessageRole.patient, ChannelType.web_chat, "hi what's the price range for lip filler", 0)
    msg(c4, MessageRole.ai, ChannelType.web_chat, "Lip filler starts at $650 per syringe — most first-time patients do one syringe. Would you like to book a consultation?", 1,
        [tool_call("lookup_knowledge_base", {"query": "lip filler pricing"}, {"found": True, "count": 1})])
    # patient never replies — chat window closed, becomes a missed/uncontacted lead

    # ---- 5. Harper Wilson — messenger, today, faq only ----
    c5 = conversation("harper", ChannelType.messenger, 0, 17, 30, ConversationOutcome.faq_only, ended_offset_min=3)
    msg(c5, MessageRole.patient, ChannelType.messenger, "do i need a consult before getting a peel done", 0)
    msg(c5, MessageRole.ai, ChannelType.messenger, "Nope — chemical peels and facials can be booked directly, no consult needed. Just injectables and laser require one first.", 1,
        [tool_call("lookup_knowledge_base", {"query": "consultation required"}, {"found": True, "count": 1})])

    # ---- 6. Ava Thompson — messenger, 1 day ago, booked HydraFacial ----
    c6 = conversation("ava", ChannelType.messenger, 1, 10, 15, ConversationOutcome.booked)
    msg(c6, MessageRole.patient, ChannelType.messenger, "can i get a hydrafacial booked for next week", 0)
    msg(c6, MessageRole.ai, ChannelType.messenger, "Absolutely — I have next Tuesday at 11am or Wednesday at 3pm for a HydraFacial. Which works?", 1,
        [tool_call("check_availability", {"service": "HydraFacial", "day": "next week"}, {"slots": ["Tuesday 11:00", "Wednesday 15:00"]})])
    msg(c6, MessageRole.patient, ChannelType.messenger, "wednesday 3pm works", 2)
    msg(c6, MessageRole.ai, ChannelType.messenger, "You're booked for Wednesday at 3:00pm for a HydraFacial!", 3,
        [tool_call("book_appointment", {"patient": "Ava Thompson", "service": "HydraFacial", "start_time": "Wednesday 15:00"}, {"status": "booked"})])

    # ---- 7. Isabella Rodriguez — instagram, 1 day ago, no_action ----
    c7 = conversation("isabella", ChannelType.instagram, 1, 19, 0, ConversationOutcome.no_action,
                       status_=ConversationStatus.abandoned, ended_offset_min=2)
    msg(c7, MessageRole.patient, ChannelType.instagram, "saw your post on microneedling, how much is that", 0)
    msg(c7, MessageRole.ai, ChannelType.instagram, "Microneedling with PRP is $450 per session, about an hour. Want me to help you book?", 1,
        [tool_call("lookup_knowledge_base", {"query": "microneedling pricing"}, {"found": False, "message": "No exact match — answered from general service list."})])

    # ---- 8. Charlotte Davis — web_chat, 2 days ago, lost + escalated ----
    c8 = conversation("charlotte", ChannelType.web_chat, 2, 14, 20, ConversationOutcome.lost,
                       status_=ConversationStatus.escalated,
                       escalated_to_staff_id=staff.id if staff else None, ended_offset_min=9)
    msg(c8, MessageRole.patient, ChannelType.web_chat, "I had filler done last month and I'm not happy with the results, I want a refund", 0)
    msg(c8, MessageRole.ai, ChannelType.web_chat, "I'm really sorry to hear that. This is something our team needs to look into directly — I'm flagging this for our clinic owner to call you back today.", 1,
        [tool_call("create_escalation", {"reason": "Patient unsatisfied with filler results, requesting refund", "urgency": "high"}, {"status": "escalated"})])
    db.add(Escalation(
        conversation_id=c8.id, clinic_id=clinic_id, reason="Patient unsatisfied with filler results, requesting refund",
        urgency="high", notified_staff_ids=[str(staff.id)] if staff else [], resolved=False, resolved_by=None,
        created_at=c8.started_at + timedelta(minutes=1),
    ))

    # ---- 9. Amelia Garcia — voice, 4 days ago, rescheduled ----
    c9 = conversation("amelia", ChannelType.voice, 4, 12, 0, ConversationOutcome.rescheduled, ended_offset_min=5)
    db.add(Call(
        conversation_id=c9.id, twilio_call_sid=f"CA{uuid.uuid4().hex[:30]}", direction="inbound",
        duration_seconds=178, recording_url=None, sentiment="neutral", created_at=c9.started_at,
    ))
    msg(c9, MessageRole.patient, ChannelType.voice, "Hi, I need to move my filler appointment, something came up.", 0)
    msg(c9, MessageRole.ai, ChannelType.voice, "No problem at all — I can move that for you. What day works better?", 1)
    msg(c9, MessageRole.patient, ChannelType.voice, "Next Monday instead, same time if you have it.", 2)
    msg(c9, MessageRole.ai, ChannelType.voice, "Done — you're moved to next Monday at the same time. See you then!", 3,
        [tool_call("book_appointment", {"patient": "Amelia Garcia", "service": "Lip Filler", "action": "reschedule"}, {"status": "rescheduled"})])

    # ---- 10. Evelyn Brown — instagram, 5 days ago, faq only ----
    c10 = conversation("evelyn", ChannelType.instagram, 5, 16, 45, ConversationOutcome.faq_only, ended_offset_min=2)
    msg(c10, MessageRole.patient, ChannelType.instagram, "do you take walk ins", 0)
    msg(c10, MessageRole.ai, ChannelType.instagram, "We're appointment-based, but we're happy to try to fit in same-day requests when we have openings — just call or text us!", 1,
        [tool_call("lookup_knowledge_base", {"query": "walk-ins"}, {"found": True, "count": 1})])

    # ---- Appointments (8 total, independent variety of statuses) ----
    def appt(patient_key, service_name, conv, days_offset, hour, minute, duration_min, status_, booked_by, created_days_ago=0, created_hour=None):
        svc = services[service_name]
        start = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_offset)
        end = start + timedelta(minutes=duration_min)
        a = Appointment(
            clinic_id=clinic_id, patient_id=patients[patient_key].id, conversation_id=conv.id if conv else None,
            service_id=svc.id, provider_staff_id=staff.id if staff else None, external_event_id=None,
            start_time=start, end_time=end, status=status_, booked_by=booked_by,
        )
        db.add(a)
        db.flush()
        # Appointment.created_at auto-defaults to the real insertion instant via
        # TimestampMixin — that's exactly what we want for "created today" rows
        # (left as-is, always <= now). For older rows, override it so the
        # dashboard's "booked_today"/revenue figures only pick up today's two.
        if created_days_ago:
            a.created_at = at(created_days_ago, created_hour if created_hour is not None else 9)
        return a

    appt("sophia", "Botox / Neuromodulator", c1, 3, 14, 0, 30, AppointmentStatus.booked, BookedBy.ai)
    appt("olivia", "Laser Hair Removal — Underarms", c2, 5, 10, 30, 20, AppointmentStatus.booked, BookedBy.ai)
    appt("ava", "HydraFacial", c6, 7, 15, 0, 50, AppointmentStatus.confirmed, BookedBy.ai, created_days_ago=1, created_hour=10)
    appt("amelia", "Lip Filler", c9, -1, 10, 0, 45, AppointmentStatus.completed, BookedBy.ai, created_days_ago=4, created_hour=12)
    appt("harper", "Microneedling with PRP", None, 2, 13, 0, 60, AppointmentStatus.booked, BookedBy.staff, created_days_ago=2, created_hour=9)
    appt("isabella", "HydraFacial", None, -3, 11, 0, 50, AppointmentStatus.no_show, BookedBy.ai, created_days_ago=3, created_hour=9)
    appt("evelyn", "Botox / Neuromodulator", None, -4, 15, 0, 30, AppointmentStatus.completed, BookedBy.ai, created_days_ago=5, created_hour=16)
    appt("charlotte", "Lip Filler", c8, 10, 14, 0, 45, AppointmentStatus.canceled, BookedBy.staff, created_days_ago=2, created_hour=14)

    # ---- Subscription: show what a paying customer's Billing page looks like ----
    db.add(Subscription(
        clinic_id=clinic_id, stripe_customer_id="cus_demo_glowstudio", stripe_subscription_id="sub_demo_glowstudio",
        status="active", plan="professional", current_period_end=now + timedelta(days=21),
    ))

    db.flush()

    return {
        "patients": len(patients),
        "conversations": 10,
        "messages": db.query(Message).filter(Message.conversation_id.in_(
            db.query(Conversation.id).filter(Conversation.clinic_id == clinic_id).subquery()
        )).count(),
        "calls": 2,
        "escalations": 1,
        "appointments": 8,
        "services": len(services),
        "knowledge_base_articles": db.query(KnowledgeBaseArticle).filter(KnowledgeBaseArticle.clinic_id == clinic_id).count(),
    }
