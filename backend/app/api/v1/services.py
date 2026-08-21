import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AuthedSession, get_current_session
from app.models import Service
from app.schemas.services import ServiceCreate, ServiceOut, ServiceUpdate

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceOut])
def list_services(session: AuthedSession = Depends(get_current_session)) -> list[Service]:
    return (
        session.db.query(Service)
        .filter(Service.clinic_id == session.claims.clinic_id)
        .order_by(Service.name)
        .all()
    )


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: ServiceCreate, session: AuthedSession = Depends(get_current_session)
) -> Service:
    service = Service(clinic_id=session.claims.clinic_id, **payload.model_dump())
    session.db.add(service)
    session.db.commit()
    session.db.refresh(service)
    return service


def _get_owned_service(session: AuthedSession, service_id: uuid.UUID) -> Service:
    service = (
        session.db.query(Service)
        .filter(Service.id == service_id, Service.clinic_id == session.claims.clinic_id)
        .first()
    )
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: uuid.UUID,
    payload: ServiceUpdate,
    session: AuthedSession = Depends(get_current_session),
) -> Service:
    service = _get_owned_service(session, service_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    session.db.commit()
    session.db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: uuid.UUID, session: AuthedSession = Depends(get_current_session)
) -> None:
    service = _get_owned_service(session, service_id)
    session.db.delete(service)
    session.db.commit()
