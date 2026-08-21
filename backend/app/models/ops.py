import uuid
from datetime import datetime

from sqlalchemy import ARRAY, JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Escalation(UUIDPKMixin, Base):
    __tablename__ = "escalations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    urgency: Mapped[str] = mapped_column(String(16), default="normal")  # low|normal|high|urgent
    notified_staff_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Integration(UUIDPKMixin, TimestampMixin, Base):
    """
    Per-clinic channel/tool credentials (Twilio sub-account, Meta page
    token, etc). Calendar connections have their own table
    (models/scheduling.py::CalendarConnection) since that abstraction is
    richer; this table covers simpler channel integrations.
    """

    __tablename__ = "integrations"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # twilio|fb_messenger|instagram
    status: Mapped[str] = mapped_column(String(32), default="disconnected")
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)  # encrypted before persist
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UsageEvent(UUIDPKMixin, Base):
    """Feeds analytics dashboards and Stripe usage-based billing metering."""

    __tablename__ = "usage_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # call_handled|sms_sent|appointment_booked...
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Subscription(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="none")
    plan: Mapped[str | None] = mapped_column(String(64))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(UUIDPKMixin, Base):
    """
    Security-sensitive event trail (HIPAA §164.312(b) audit controls).
    metadata_json must only ever hold safe structured facts — IDs,
    enums, counts — never message content, secrets, or PHI. See
    app/core/audit.py for the only sanctioned way to write to this table.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
