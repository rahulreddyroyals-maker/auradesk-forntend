import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AuthedSession, get_current_session
from app.models import Conversation, Message, Patient
from app.schemas.conversations import ConversationDetailOut, ConversationOut, MessageOut

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(session: AuthedSession = Depends(get_current_session)) -> list[ConversationOut]:
    conversations = (
        session.db.query(Conversation)
        .filter(Conversation.clinic_id == session.claims.clinic_id)
        .order_by(Conversation.started_at.desc())
        .limit(100)
        .all()
    )
    out = []
    for c in conversations:
        patient_name = None
        if c.patient_id:
            patient = session.db.get(Patient, c.patient_id)
            if patient:
                patient_name = f"{patient.first_name} {patient.last_name or ''}".strip()
        out.append(
            ConversationOut(
                id=c.id,
                channel=c.channel.value,
                status=c.status.value,
                started_at=c.started_at,
                ended_at=c.ended_at,
                ai_handled=c.ai_handled,
                outcome=c.outcome.value if c.outcome else None,
                patient_name=patient_name,
            )
        )
    return out


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: uuid.UUID, session: AuthedSession = Depends(get_current_session)
) -> ConversationDetailOut:
    conv = (
        session.db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.clinic_id == session.claims.clinic_id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = (
        session.db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    patient_name = None
    if conv.patient_id:
        patient = session.db.get(Patient, conv.patient_id)
        if patient:
            patient_name = f"{patient.first_name} {patient.last_name or ''}".strip()

    return ConversationDetailOut(
        id=conv.id,
        channel=conv.channel.value,
        status=conv.status.value,
        started_at=conv.started_at,
        ended_at=conv.ended_at,
        ai_handled=conv.ai_handled,
        outcome=conv.outcome.value if conv.outcome else None,
        patient_name=patient_name,
        messages=[MessageOut(id=m.id, role=m.role.value, channel=m.channel.value, content=m.content, created_at=m.created_at) for m in messages],
    )
