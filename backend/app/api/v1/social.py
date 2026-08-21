"""
Messenger + Instagram webhooks. Both arrive in the same "entry[].messaging[]"
shape (Meta's unified webhook format for Page-connected products) — the
`object` field ("page" vs "instagram") tells us which channel a given
event is actually for, independent of which URL Meta called.
"""
import json

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func

from app.core.config import settings
from app.core.safe_logging import log_event, redact_exception
from app.db.session import AdminSessionLocal, SessionLocal, bind_clinic_context
from app.integrations.meta_client import send_message, verify_webhook_signature
from app.models import ChannelType, Conversation, ConversationStatus, Integration, Patient
from app.orchestrator.session import handle_message

router = APIRouter(tags=["social"])


def _verify_challenge(hub_mode: str | None, hub_verify_token: str | None, hub_challenge: str | None) -> PlainTextResponse:
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge or "")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@router.get("/messenger/webhook")
def verify_messenger(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    return _verify_challenge(hub_mode, hub_verify_token, hub_challenge)


@router.get("/instagram/webhook")
def verify_instagram(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    return _verify_challenge(hub_mode, hub_verify_token, hub_challenge)


def _find_integration_by_page_id(db, page_id: str) -> Integration | None:
    return (
        db.query(Integration)
        .filter(
            Integration.type.in_(["messenger", "instagram"]),
            func.json_extract_path_text(Integration.config_json, "page_id") == page_id,
        )
        .first()
    )


def _find_or_create_social_patient(db, clinic_id: str, channel_key: str, external_id: str) -> Patient:
    patient = (
        db.query(Patient)
        .filter(
            Patient.clinic_id == clinic_id,
            func.json_extract_path_text(Patient.external_ids_json, channel_key) == external_id,
        )
        .first()
    )
    if patient:
        return patient
    patient = Patient(
        clinic_id=clinic_id,
        first_name="Unknown",
        source_channel=channel_key,
        lifecycle_stage="lead",
        external_ids_json={channel_key: external_id},
    )
    db.add(patient)
    db.flush()
    return patient


def _find_active_conversation(db, clinic_id: str, patient_id: str, channel: ChannelType) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(
            Conversation.clinic_id == clinic_id,
            Conversation.patient_id == patient_id,
            Conversation.channel == channel,
            Conversation.status == ConversationStatus.active,
        )
        .order_by(Conversation.started_at.desc())
        .first()
    )


async def _handle_webhook(request: Request) -> dict:
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    payload = json.loads(raw_body)
    object_type = payload.get("object")  # "page" (Messenger) or "instagram"
    channel = ChannelType.instagram if object_type == "instagram" else ChannelType.messenger
    channel_key = channel.value

    db = SessionLocal()
    admin_db = AdminSessionLocal()
    try:
        for entry in payload.get("entry", []):
            page_id = entry.get("id")
            # Page-to-clinic mapping lookup can't be RLS-scoped — we don't
            # know which clinic this is until this query resolves it.
            integration = _find_integration_by_page_id(admin_db, page_id)
            if not integration:
                continue  # unknown page — not one of our clinics, or not configured yet

            page_access_token = integration.config_json.get("page_access_token")
            clinic_id = str(integration.clinic_id)
            # A single payload can batch entries for multiple pages/clinics —
            # rebind for each entry (safe/idempotent; just updates the claim
            # and re-applies it immediately).
            bind_clinic_context(db, clinic_id)

            for event in entry.get("messaging", []):
                message = event.get("message")
                if not message or message.get("is_echo"):
                    continue  # skip delivery/read receipts and our own echoed sends
                text = message.get("text")
                if not text:
                    continue  # attachments/stickers-only messages — not handled yet

                sender_id = event["sender"]["id"]
                patient = _find_or_create_social_patient(db, clinic_id, channel_key, sender_id)
                db.commit()

                existing_conv = _find_active_conversation(db, clinic_id, str(patient.id), channel)
                result = handle_message(
                    db=db,
                    clinic_id=clinic_id,
                    channel=channel,
                    user_message=text,
                    conversation_id=str(existing_conv.id) if existing_conv else None,
                    patient_id=str(patient.id),
                )

                if page_access_token:
                    try:
                        send_message(page_access_token, sender_id, result["reply"])
                    except Exception as exc:  # noqa: BLE001 — log and continue; don't fail the whole webhook over one send error
                        log_event("social_reply_send_failed", channel=channel_key, error_type=redact_exception(exc))

        return {"status": "ok"}
    finally:
        db.close()
        admin_db.close()


@router.post("/messenger/webhook")
async def messenger_webhook(request: Request) -> dict:
    return await _handle_webhook(request)


@router.post("/instagram/webhook")
async def instagram_webhook(request: Request) -> dict:
    return await _handle_webhook(request)
