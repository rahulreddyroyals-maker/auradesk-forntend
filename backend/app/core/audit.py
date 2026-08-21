"""
The only sanctioned way to write to audit_logs. Keeping this as a single
narrow function (rather than letting every endpoint construct an
AuditLog row directly) makes it possible to review every place PHI
could accidentally end up in metadata_json by reading one file instead
of grepping the whole codebase.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit_event(
    db: Session,
    clinic_id: str,
    event_type: str,
    actor_user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    **metadata,
) -> None:
    """
    metadata must only be safe, structured facts (counts, booleans,
    enum values, IDs) — never message content, names of specific
    treatments discussed, or secrets. This function does not filter
    for that; it's a contract enforced by what callers choose to pass.
    """
    db.add(
        AuditLog(
            clinic_id=clinic_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=metadata,
            created_at=datetime.now(timezone.utc),
        )
    )
    # Deliberately does not commit — callers already commit their own
    # transaction; piggybacking on that keeps the audit row atomic with
    # the change it's describing (both succeed or both roll back together).
