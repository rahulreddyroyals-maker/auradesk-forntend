import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UUIDPKMixin:
    """Primary key convention: UUID, generated client-side (uuid4)."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# Convention (not a mixin, since SQLAlchemy declarative mixins can't easily
# share a FK target across models): every tenant-scoped table declares its
# own field, always named and typed identically —
#
#   clinic_id: Mapped[uuid.UUID] = mapped_column(
#       UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"),
#       nullable=False, index=True,
#   )
#
# This consistency is what sql/rls_policies.sql relies on — every policy
# is generated against a table's `clinic_id` column by the same template.
