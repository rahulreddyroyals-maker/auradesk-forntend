import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.api.deps import AuthedSession, get_current_session, require_role
from app.core.audit import record_audit_event
from app.integrations.supabase_admin import invite_user_by_email
from app.models import Staff, StaffRole
from app.schemas.team import InviteRequest, StaffOut, StaffRoleUpdate

router = APIRouter(prefix="/team", tags=["team"])


def _get_email(db, user_id: uuid.UUID) -> str | None:
    # auth.users lives in Supabase's own schema on the same Postgres
    # instance — not one of our SQLAlchemy models, so a direct query here.
    row = db.execute(text("SELECT email FROM auth.users WHERE id = :uid"), {"uid": str(user_id)}).first()
    return row[0] if row else None


@router.get("", response_model=list[StaffOut])
def list_team(session: AuthedSession = Depends(get_current_session)) -> list[StaffOut]:
    staff = session.db.query(Staff).filter(Staff.clinic_id == session.claims.clinic_id).all()
    return [
        StaffOut(id=s.id, name=s.name, role=s.role.value, phone=s.phone, email=_get_email(session.db, s.user_id))
        for s in staff
    ]


@router.post("/invite", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
def invite_team_member(
    payload: InviteRequest, session: AuthedSession = Depends(require_role("owner", "admin"))
) -> StaffOut:
    try:
        user_id = invite_user_by_email(payload.email)
    except Exception as exc:  # noqa: BLE001 — surface a clean message rather than a raw HTTP error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Couldn't send invite — the email may already be registered.",
        ) from exc

    staff = Staff(
        clinic_id=session.claims.clinic_id,
        user_id=uuid.UUID(user_id),
        name=payload.name,
        role=StaffRole(payload.role),
    )
    session.db.add(staff)
    record_audit_event(
        session.db,
        clinic_id=session.claims.clinic_id,
        event_type="staff_invited",
        actor_user_id=session.claims.user_id,
        resource_type="staff",
        resource_id=str(staff.id),
        role=payload.role,
    )
    session.db.commit()
    session.db.refresh(staff)
    return StaffOut(id=staff.id, name=staff.name, role=staff.role.value, phone=staff.phone, email=payload.email)


@router.patch("/{staff_id}/role", response_model=StaffOut)
def update_role(
    staff_id: uuid.UUID,
    payload: StaffRoleUpdate,
    session: AuthedSession = Depends(require_role("owner", "admin")),
) -> StaffOut:
    staff = (
        session.db.query(Staff)
        .filter(Staff.id == staff_id, Staff.clinic_id == session.claims.clinic_id)
        .first()
    )
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")
    old_role = staff.role.value
    staff.role = StaffRole(payload.role)
    record_audit_event(
        session.db,
        clinic_id=session.claims.clinic_id,
        event_type="staff_role_changed",
        actor_user_id=session.claims.user_id,
        resource_type="staff",
        resource_id=str(staff.id),
        old_role=old_role,
        new_role=payload.role,
    )
    session.db.commit()
    session.db.refresh(staff)
    return StaffOut(id=staff.id, name=staff.name, role=staff.role.value, phone=staff.phone, email=_get_email(session.db, staff.user_id))


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    staff_id: uuid.UUID, session: AuthedSession = Depends(require_role("owner", "admin"))
) -> None:
    staff = (
        session.db.query(Staff)
        .filter(Staff.id == staff_id, Staff.clinic_id == session.claims.clinic_id)
        .first()
    )
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")

    if staff.role == StaffRole.owner:
        owner_count = (
            session.db.query(Staff)
            .filter(Staff.clinic_id == session.claims.clinic_id, Staff.role == StaffRole.owner)
            .count()
        )
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can't remove the last owner — promote someone else first.",
            )

    record_audit_event(
        session.db,
        clinic_id=session.claims.clinic_id,
        event_type="staff_removed",
        actor_user_id=session.claims.user_id,
        resource_type="staff",
        resource_id=str(staff.id),
    )
    session.db.delete(staff)
    session.db.commit()
