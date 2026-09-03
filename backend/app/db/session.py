"""
Two database connections, deliberately:

  engine / SessionLocal       — the RESTRICTED `auradesk_app` role (see
                                 sql/restrict_app_role.sql). NOT a table
                                 owner, so Postgres actually applies RLS
                                 to it. This is what every normal request
                                 uses.

  admin_engine / AdminSessionLocal — the `postgres` table-owner role.
                                 Bypasses RLS entirely. Used ONLY where
                                 that's structurally necessary: Alembic
                                 migrations (DDL — the restricted role
                                 deliberately has no CREATE/DROP rights),
                                 and onboarding's clinic-creation step
                                 (there's no clinic_id claim to check
                                 against yet — that's the row being
                                 created). Treat DATABASE_URL_ADMIN as a
                                 more sensitive secret than DATABASE_URL.

RLS claim binding (bind_clinic_context) uses a SQLAlchemy `after_begin`
session event rather than a one-time `set_config` call. This matters:
`set_config(..., true)` is scoped to the current transaction, and
SQLAlchemy starts a new transaction after every commit — so a request
that commits partway through and queries again afterward would silently
lose its claim without this. The event re-applies it at the start of
EVERY transaction on the session, including ones that start after a
mid-request commit.

IMPORTANT implementation detail: the `after_begin` listener executes
directly on the raw `connection` object it's given, NOT via
`session.execute(...)`. Calling back into the session's own execute()
method from inside its own connection-provisioning hook raises
`InvalidRequestError: This session is provisioning a new connection;
concurrent operations are not permitted` — SQLAlchemy doesn't allow a
session to re-enter itself mid-provisioning. This only surfaces
intermittently (timing-dependent on connection pool state), and a
SQLite-only test won't catch it, since SQLite doesn't enforce this same
restriction — real Postgres does. Always use the `connection` parameter
inside this specific hook, never `session`/`db`.
"""
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_admin_url = settings.DATABASE_URL_ADMIN or settings.DATABASE_URL
admin_engine = create_engine(_admin_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
AdminSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=admin_engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a request-scoped, RLS-restricted DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def bind_clinic_context(db: Session, clinic_id: str, user_id: str | None = None, role: str | None = None) -> None:
    """
    Attaches clinic_id (and optionally user_id/role) to this session and
    ensures every transaction on it — including ones that begin after a
    mid-request commit — carries the RLS claim. Call this once per
    session, as early as possible (right after you know the clinic_id),
    for both authenticated requests (deps.py) and webhook handlers that
    resolve clinic_id from an external identifier (phone number, page
    ID, etc.) rather than a JWT.
    """
    db.info["rls_clinic_id"] = clinic_id
    db.info["rls_user_id"] = user_id
    db.info["rls_role"] = role

    # Apply immediately for the session's current/first transaction —
    # safe here since this runs as a normal top-level call, not from
    # inside a connection-provisioning hook.
    _apply_claims(db)

    # Idempotent: only attach the listener once per session, even if
    # bind_clinic_context is called more than once (e.g. re-binding after
    # resolving the clinic partway through a webhook handler).
    if not db.info.get("rls_listener_attached"):
        event.listen(db, "after_begin", _after_begin_apply_claims)
        db.info["rls_listener_attached"] = True


def _after_begin_apply_claims(session: Session, transaction, connection: Connection) -> None:
    """
    SQLAlchemy `after_begin` hook. Must execute on the raw `connection`
    passed in here, NOT via session.execute()/db.execute() — the session
    is still provisioning this very connection at this point, and
    calling back into the session's own execute() from inside this hook
    raises InvalidRequestError (see module docstring).
    """
    clinic_id = session.info.get("rls_clinic_id")
    if not clinic_id:
        return
    connection.execute(text("SELECT set_config('request.jwt.claim.clinic_id', :v, true)"), {"v": str(clinic_id)})
    user_id = session.info.get("rls_user_id")
    if user_id:
        connection.execute(text("SELECT set_config('request.jwt.claim.sub', :v, true)"), {"v": str(user_id)})
    role = session.info.get("rls_role")
    if role:
        connection.execute(text("SELECT set_config('request.jwt.claim.role', :v, true)"), {"v": str(role)})


def _apply_claims(db: Session) -> None:
    """Used for the initial, immediate application in bind_clinic_context — safe to go through the session here."""
    clinic_id = db.info.get("rls_clinic_id")
    if not clinic_id:
        return
    db.execute(text("SELECT set_config('request.jwt.claim.clinic_id', :v, true)"), {"v": str(clinic_id)})
    user_id = db.info.get("rls_user_id")
    if user_id:
        db.execute(text("SELECT set_config('request.jwt.claim.sub', :v, true)"), {"v": str(user_id)})
    role = db.info.get("rls_role")
    if role:
        db.execute(text("SELECT set_config('request.jwt.claim.role', :v, true)"), {"v": str(role)})


# Kept for backward compatibility with any code still calling the old
# one-shot name — prefer bind_clinic_context for new code, since it
# survives mid-request commits and this doesn't.
def set_rls_claims(db: Session, clinic_id: str, user_id: str, role: str) -> None:
    bind_clinic_context(db, clinic_id, user_id, role)
