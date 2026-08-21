import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps_onboarding import get_authenticated_user_id
from app.db.session import AdminSessionLocal
from app.models import Clinic, Staff, AIEmployee, StaffRole
from app.schemas.onboarding import OnboardClinicRequest, OnboardClinicResponse

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base or "clinic"


@router.post("/clinic", response_model=OnboardClinicResponse, status_code=status.HTTP_201_CREATED)
def onboard_clinic(
    payload: OnboardClinicRequest,
    user_id: str = Depends(get_authenticated_user_id),
) -> OnboardClinicResponse:
    # This creates the clinic itself, so there's no clinic_id claim that
    # could exist yet to satisfy RLS — the admin connection is the
    # correct, narrowly-scoped exception here, same reasoning as the
    # webhook clinic-resolution lookups.
    db = AdminSessionLocal()
    try:
        existing = db.query(Staff).filter(Staff.user_id == uuid.UUID(user_id)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This account is already linked to a clinic.",
            )

        slug_base = _slugify(payload.clinic_name)
        slug = slug_base
        suffix = 1
        while db.query(Clinic).filter(Clinic.slug == slug).first():
            suffix += 1
            slug = f"{slug_base}-{suffix}"

        clinic = Clinic(name=payload.clinic_name, slug=slug, timezone=payload.timezone)
        db.add(clinic)
        db.flush()  # get clinic.id before creating dependent rows

        staff = Staff(
            clinic_id=clinic.id,
            user_id=uuid.UUID(user_id),
            name=payload.owner_name,
            role=StaffRole.owner,
        )
        db.add(staff)

        ai_employee = AIEmployee(clinic_id=clinic.id, name="Aura")
        db.add(ai_employee)

        db.commit()
        db.refresh(clinic)

        return OnboardClinicResponse(clinic_id=str(clinic.id), clinic_name=clinic.name, slug=clinic.slug)
    finally:
        db.close()
