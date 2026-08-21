"""
Twilio calls this endpoint on every inbound SMS to a clinic's number.
Unlike the rest of the API, this is intentionally unauthenticated (no
Supabase session — Twilio isn't one of our users) — clinic identity comes
from matching the "To" number against Clinic.phone_number instead.
Signature validation (see _verify_twilio_signature) is the real
authentication boundary here.
"""
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import Response
from twilio.request_validator import RequestValidator

from app.core.config import settings
from app.core.idempotency import already_processed
from app.db.session import AdminSessionLocal, SessionLocal, bind_clinic_context
from app.models import ChannelType, Clinic, Conversation, ConversationStatus, Patient
from app.orchestrator.session import handle_message

router = APIRouter(prefix="/sms", tags=["sms"])


def _find_or_create_patient(db, clinic_id: str, phone: str) -> Patient:
    patient = db.query(Patient).filter(Patient.clinic_id == clinic_id, Patient.phone == phone).first()
    if patient:
        return patient
    patient = Patient(clinic_id=clinic_id, first_name="Unknown", phone=phone, source_channel="sms", lifecycle_stage="lead")
    db.add(patient)
    db.flush()
    return patient


def _find_active_sms_conversation(db, clinic_id: str, patient_id: str) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(
            Conversation.clinic_id == clinic_id,
            Conversation.patient_id == patient_id,
            Conversation.channel == ChannelType.sms,
            Conversation.status == ConversationStatus.active,
        )
        .order_by(Conversation.started_at.desc())
        .first()
    )


def _verify_twilio_signature(request: Request, form: dict, signature: str | None) -> None:
    if not settings.TWILIO_VALIDATE_SIGNATURE:
        return
    if not signature:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing Twilio signature")
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    # NOTE: this must be the exact public URL Twilio called. Behind a
    # reverse proxy (including most production deployments), request.url
    # reflects the internal URL unless X-Forwarded-Proto/Host are trusted
    # and applied — verify this matches your actual deployment before
    # relying on it, e.g. with ProxyHeadersMiddleware configured for your
    # specific proxy.
    if not validator.validate(str(request.url), form, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")


@router.post("/webhook")
async def sms_webhook(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
    X_Twilio_Signature: str | None = None,
) -> Response:
    form = dict(await request.form())
    _verify_twilio_signature(request, form, request.headers.get("X-Twilio-Signature"))

    if already_processed(MessageSid):
        # Twilio retries on any non-2xx response or timeout — this is
        # exactly the same delivery arriving again, not a new message.
        # Return the same shape of response without reprocessing, so the
        # patient doesn't get a duplicate reply.
        return Response(content="<Response></Response>", media_type="application/xml")

    # Resolving "which clinic does this phone number belong to" can't be
    # RLS-scoped — we don't know the clinic_id yet, that's what this query
    # finds. Keep this admin-connection query to exactly this one lookup;
    # everything after switches to the restricted, claim-bound connection.
    admin_db = AdminSessionLocal()
    try:
        clinic = admin_db.query(Clinic).filter(Clinic.phone_number == To).first()
    finally:
        admin_db.close()

    if not clinic:
        # Unknown number — don't leak whether a clinic exists either way,
        # just decline politely and log server-side for follow-up.
        twiml = "<Response><Message>Sorry, this number isn't set up yet.</Message></Response>"
        return Response(content=twiml, media_type="application/xml")

    db = SessionLocal()
    bind_clinic_context(db, str(clinic.id))
    try:
        patient = _find_or_create_patient(db, str(clinic.id), From)
        db.commit()
        existing_conv = _find_active_sms_conversation(db, str(clinic.id), str(patient.id))

        result = handle_message(
            db=db,
            clinic_id=str(clinic.id),
            channel=ChannelType.sms,
            user_message=Body,
            conversation_id=str(existing_conv.id) if existing_conv else None,
            patient_id=str(patient.id),
        )
        reply = result["reply"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        twiml = f"<Response><Message>{reply}</Message></Response>"
        return Response(content=twiml, media_type="application/xml")
    finally:
        db.close()
