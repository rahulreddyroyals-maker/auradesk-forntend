"""
Core request dependencies.

`get_current_session` is the one dependency almost every authenticated
route should use: it verifies the bearer token, opens a DB session, and
binds the RLS claims (clinic_id/user_id/role) to that session — so a
route handler can just query normally and trust that cross-tenant rows
are already invisible to it (see app/db/session.py::bind_clinic_context
for how this survives mid-request commits).
"""
from collections.abc import Generator
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import AuthClaims, decode_supabase_jwt
from app.db.session import SessionLocal, bind_clinic_context


@dataclass(frozen=True)
class AuthedSession:
    db: Session
    claims: AuthClaims


def get_current_session(
    authorization: str | None = Header(default=None),
) -> Generator[AuthedSession, None, None]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = authorization.split(" ", 1)[1]
    claims = decode_supabase_jwt(token)

    db = SessionLocal()
    try:
        bind_clinic_context(db, clinic_id=claims.clinic_id, user_id=claims.user_id, role=claims.role)
        yield AuthedSession(db=db, claims=claims)
    finally:
        db.close()


def require_role(*allowed_roles: str):
    """Route-level guard, e.g. Depends(require_role('owner', 'admin'))."""

    def _check(session: AuthedSession = Depends(get_current_session)) -> AuthedSession:
        if session.claims.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to perform this action.",
            )
        return session

    return _check
