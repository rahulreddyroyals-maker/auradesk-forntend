import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import AuthedSession, get_current_session
from app.models import Appointment, AppointmentStatus, Patient, Service
from app.schemas.appointments import AppointmentOut, AppointmentStatusUpdate

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _to_out(db, a: Appointment) -> AppointmentOut:
    patient = db.get(Patient, a.patient_id)
    service = db.get(Service, a.service_id)
    return AppointmentOut(
        id=a.id,
        patient_name=f"{patient.first_name} {patient.last_name or ''}".strip() if patient else "Unknown",
        service_name=service.name if service else "Unknown service",
        start_time=a.start_time,
        end_time=a.end_time,
        status=a.status.value,
        booked_by=a.booked_by.value,
    )


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    upcoming_only: bool = Query(default=False),
    session: AuthedSession = Depends(get_current_session),
) -> list[AppointmentOut]:
    query = session.db.query(Appointment).filter(Appointment.clinic_id == session.claims.clinic_id)
    if upcoming_only:
        from datetime import datetime, timezone

        query = query.filter(Appointment.start_time >= datetime.now(timezone.utc))
    appointments = query.order_by(Appointment.start_time.asc()).limit(200).all()
    return [_to_out(session.db, a) for a in appointments]


@router.patch("/{appointment_id}", response_model=AppointmentOut)
def update_appointment_status(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdate,
    session: AuthedSession = Depends(get_current_session),
) -> AppointmentOut:
    appt = (
        session.db.query(Appointment)
        .filter(Appointment.id == appointment_id, Appointment.clinic_id == session.claims.clinic_id)
        .first()
    )
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    try:
        appt.status = AppointmentStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    session.db.commit()
    session.db.refresh(appt)
    return _to_out(session.db, appt)
