"""
Platform admin: you, managing every clinic on AuraDesk — distinct from a
clinic's own owner/admin/front_desk staff roles, which are all scoped to
one clinic via RLS and can never see across tenants.

Access is gated by an email allowlist (settings.PLATFORM_ADMIN_EMAILS),
not a database row or a Staff role — there's no migration to run, and
granting yourself access is just adding your own Supabase account's
email to that setting. The check is against the verified JWT's own
"email" claim (decoded and signature-checked the same way every other
route verifies a token), never a client-supplied value.

Every route here uses AdminSessionLocal (the RLS-bypassing connection) —
by definition, seeing "every clinic" requires bypassing the per-clinic
RLS policies. Nothing here is reachable without a valid Supabase session
whose email is on the allowlist; leaving PLATFORM_ADMIN_EMAILS unset
disables all of it (fails closed, same pattern as DEMO_RESEED_TOKEN).
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import decode_raw_claims
from app.db.session import AdminSessionLocal
from app.models.ops import Subscription
from app.models.scheduling import Service
from app.models.tenancy import Clinic, ClinicStatus, Staff

router = APIRouter(prefix="/admin", tags=["platform-admin"])


def require_platform_admin(authorization: str | None = Header(default=None)) -> str:
    """Returns the verified admin's email, or raises. Use as a route dependency."""
    if not settings.platform_admin_emails_list:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platform admin is not configured on this server (PLATFORM_ADMIN_EMAILS unset).",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_raw_claims(token)  # verifies signature; doesn't require clinic_id, unlike decode_supabase_jwt
    email = (payload.get("email") or "").strip().lower()
    if not email or email not in settings.platform_admin_emails_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a platform admin account.")
    return email


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SubscriptionOut(BaseModel):
    status: str
    plan: str | None
    current_period_end: datetime | None


class ClinicAdminOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str
    created_at: datetime
    staff_count: int
    service_count: int
    subscription: SubscriptionOut | None


class ClinicStatusUpdateIn(BaseModel):
    status: ClinicStatus


class SubscriptionUpdateIn(BaseModel):
    status: str | None = None  # e.g. "active" | "past_due" | "canceled" | "none"
    plan: str | None = None  # e.g. "starter" | "professional"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/clinics", response_model=list[ClinicAdminOut])
def list_clinics(_admin_email: str = Depends(require_platform_admin)) -> list[ClinicAdminOut]:
    db = AdminSessionLocal()
    try:
        clinics = db.query(Clinic).order_by(Clinic.created_at.desc()).all()
        out = []
        for c in clinics:
            sub = db.query(Subscription).filter(Subscription.clinic_id == c.id).first()
            out.append(
                ClinicAdminOut(
                    id=c.id,
                    name=c.name,
                    slug=c.slug,
                    status=c.status.value,
                    created_at=c.created_at,
                    staff_count=db.query(Staff).filter(Staff.clinic_id == c.id).count(),
                    service_count=db.query(Service).filter(Service.clinic_id == c.id).count(),
                    subscription=SubscriptionOut(
                        status=sub.status, plan=sub.plan, current_period_end=sub.current_period_end
                    )
                    if sub
                    else None,
                )
            )
        return out
    finally:
        db.close()


@router.patch("/clinics/{clinic_id}/status", response_model=ClinicAdminOut)
def update_clinic_status(
    clinic_id: uuid.UUID, payload: ClinicStatusUpdateIn, _admin_email: str = Depends(require_platform_admin)
) -> ClinicAdminOut:
    """Suspend, reactivate, or cancel a clinic — independent of its billing
    subscription status, e.g. to pause access for a trial that's gone quiet
    or a clinic under review, without touching Stripe."""
    db = AdminSessionLocal()
    try:
        clinic = db.get(Clinic, clinic_id)
        if not clinic:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
        clinic.status = payload.status
        db.commit()
        db.refresh(clinic)
        sub = db.query(Subscription).filter(Subscription.clinic_id == clinic.id).first()
        return ClinicAdminOut(
            id=clinic.id,
            name=clinic.name,
            slug=clinic.slug,
            status=clinic.status.value,
            created_at=clinic.created_at,
            staff_count=db.query(Staff).filter(Staff.clinic_id == clinic.id).count(),
            service_count=db.query(Service).filter(Service.clinic_id == clinic.id).count(),
            subscription=SubscriptionOut(
                status=sub.status, plan=sub.plan, current_period_end=sub.current_period_end
            )
            if sub
            else None,
        )
    finally:
        db.close()


@router.patch("/clinics/{clinic_id}/subscription", response_model=SubscriptionOut)
def update_subscription(
    clinic_id: uuid.UUID, payload: SubscriptionUpdateIn, _admin_email: str = Depends(require_platform_admin)
) -> SubscriptionOut:
    """Manually set a clinic's subscription status/plan — e.g. to comp an
    account, mark one active after confirming payment out-of-band, or flag
    one past_due. This writes your own database row directly; it does not
    call Stripe. Keep your source of truth (Stripe dashboard, or your own
    Stripe webhook handler once wired up) in sync with this by hand."""
    db = AdminSessionLocal()
    try:
        clinic = db.get(Clinic, clinic_id)
        if not clinic:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
        sub = db.query(Subscription).filter(Subscription.clinic_id == clinic_id).first()
        if not sub:
            sub = Subscription(clinic_id=clinic_id, status=payload.status or "none", plan=payload.plan)
            db.add(sub)
        else:
            if payload.status is not None:
                sub.status = payload.status
            if payload.plan is not None:
                sub.plan = payload.plan
        db.commit()
        db.refresh(sub)
        return SubscriptionOut(status=sub.status, plan=sub.plan, current_period_end=sub.current_period_end)
    finally:
        db.close()
