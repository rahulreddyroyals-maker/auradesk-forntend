import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AuthedSession, get_current_session
from app.core.audit import record_audit_event
from app.models import Conversation, Escalation, Patient
from app.schemas.escalations import EscalationOut

router = APIRouter(prefix="/escalations", tags=["escalations"])


def _to_out(db, e: Escalation) -> EscalationOut:
    patient_name = None
    conv = db.get(Conversation, e.conversation_id)
    if conv and conv.patient_id:
        patient = db.get(Patient, conv.patient_id)
        if patient:
            patient_name = f"{patient.first_name} {patient.last_name or ''}".strip()
    return EscalationOut(
        id=e.id,
        conversation_id=e.conversation_id,
        reason=e.reason,
        urgency=e.urgency,
        resolved=e.resolved,
        created_at=e.created_at,
        patient_name=patient_name,
    )


@router.get("", response_model=list[EscalationOut])
def list_escalations(session: AuthedSession = Depends(get_current_session)) -> list[EscalationOut]:
    escalations = (
        session.db.query(Escalation)
        .filter(Escalation.clinic_id == session.claims.clinic_id)
        .order_by(Escalation.created_at.desc())
        .limit(100)
        .all()
    )
    return [_to_out(session.db, e) for e in escalations]


@router.patch("/{escalation_id}/resolve", response_model=EscalationOut)
def resolve_escalation(
    escalation_id: uuid.UUID, session: AuthedSession = Depends(get_current_session)
) -> EscalationOut:
    escalation = (
        session.db.query(Escalation)
        .filter(Escalation.id == escalation_id, Escalation.clinic_id == session.claims.clinic_id)
        .first()
    )
    if not escalation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found")
    escalation.resolved = True
    escalation.resolved_by = uuid.UUID(session.claims.user_id)
    record_audit_event(
        session.db,
        clinic_id=session.claims.clinic_id,
        event_type="escalation_resolved",
        actor_user_id=session.claims.user_id,
        resource_type="escalation",
        resource_id=str(escalation.id),
    )
    session.db.commit()
    session.db.refresh(escalation)
    return _to_out(session.db, escalation)
