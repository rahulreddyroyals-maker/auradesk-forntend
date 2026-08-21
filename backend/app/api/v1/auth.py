from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import AuthedSession, get_current_session
from app.models import Clinic

router = APIRouter(prefix="/auth", tags=["auth"])


class MeResponse(BaseModel):
    user_id: str
    clinic_id: str
    clinic_name: str
    role: str
    email: str | None


@router.get("/me", response_model=MeResponse)
def read_current_user(session: AuthedSession = Depends(get_current_session)) -> MeResponse:
    clinic = session.db.get(Clinic, session.claims.clinic_id)
    return MeResponse(
        user_id=session.claims.user_id,
        clinic_id=session.claims.clinic_id,
        clinic_name=clinic.name if clinic else "",
        role=session.claims.role,
        email=session.claims.email,
    )
