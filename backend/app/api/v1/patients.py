import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import AuthedSession, get_current_session
from app.core.audit import record_audit_event
from app.models import Patient
from app.schemas.patients import PatientCreate, PatientOut, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(
    search: str | None = Query(default=None, description="Match against name, phone, or email"),
    session: AuthedSession = Depends(get_current_session),
) -> list[Patient]:
    query = session.db.query(Patient).filter(Patient.clinic_id == session.claims.clinic_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Patient.first_name.ilike(like))
            | (Patient.last_name.ilike(like))
            | (Patient.phone.ilike(like))
            | (Patient.email.ilike(like))
        )
    return query.order_by(Patient.created_at.desc()).limit(200).all()


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate, session: AuthedSession = Depends(get_current_session)
) -> Patient:
    patient = Patient(clinic_id=session.claims.clinic_id, source_channel="manual", **payload.model_dump())
    session.db.add(patient)
    session.db.commit()
    session.db.refresh(patient)
    return patient


def _get_owned_patient(session: AuthedSession, patient_id: uuid.UUID) -> Patient:
    patient = (
        session.db.query(Patient)
        .filter(Patient.id == patient_id, Patient.clinic_id == session.claims.clinic_id)
        .first()
    )
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    session: AuthedSession = Depends(get_current_session),
) -> Patient:
    patient = _get_owned_patient(session, patient_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    session.db.commit()
    session.db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: uuid.UUID, session: AuthedSession = Depends(get_current_session)
) -> None:
    patient = _get_owned_patient(session, patient_id)
    record_audit_event(
        session.db,
        clinic_id=session.claims.clinic_id,
        event_type="patient_deleted",
        actor_user_id=session.claims.user_id,
        resource_type="patient",
        resource_id=str(patient.id),
    )
    session.db.delete(patient)
    session.db.commit()
