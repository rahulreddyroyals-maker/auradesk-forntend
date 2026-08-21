from fastapi import APIRouter, Depends

from app.api.deps import AuthedSession, get_current_session
from app.models import Clinic
from app.schemas.clinic import ClinicOut, ClinicUpdate

router = APIRouter(prefix="/clinic", tags=["clinic"])


@router.get("", response_model=ClinicOut)
def get_clinic(session: AuthedSession = Depends(get_current_session)) -> Clinic:
    return session.db.get(Clinic, session.claims.clinic_id)


@router.patch("", response_model=ClinicOut)
def update_clinic(
    payload: ClinicUpdate, session: AuthedSession = Depends(get_current_session)
) -> Clinic:
    clinic = session.db.get(Clinic, session.claims.clinic_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(clinic, field, value)
    session.db.commit()
    session.db.refresh(clinic)
    return clinic
