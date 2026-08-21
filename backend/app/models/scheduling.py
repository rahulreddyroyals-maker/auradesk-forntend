import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class CalendarProviderType(str, enum.Enum):
    internal = "internal"        # AuraDesk's own scheduling engine (appointments table is source of truth)
    google_calendar = "google_calendar"
    cal_com = "cal_com"


class AppointmentStatus(str, enum.Enum):
    booked = "booked"
    confirmed = "confirmed"
    rescheduled = "rescheduled"
    canceled = "canceled"
    completed = "completed"
    no_show = "no_show"


class BookedBy(str, enum.Enum):
    ai = "ai"
    staff = "staff"


class Service(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "services"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Botox, Fillers, Laser, Hydrafacial, PRP, ...
    category: Mapped[str | None] = mapped_column(String(100))
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Membership(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "memberships"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(32), default="monthly")
    benefits_json: Mapped[dict] = mapped_column(JSON, default=dict)


class CalendarConnection(UUIDPKMixin, TimestampMixin, Base):
    """
    Per-clinic choice of scheduling backend. The orchestrator's booking
    tool talks to app/services/scheduling.py, which dispatches to the
    right AvailabilityProvider implementation based on this row rather
    than the caller needing to know which backend is in use.
    """

    __tablename__ = "calendar_connections"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider: Mapped[CalendarProviderType] = mapped_column(
        SAEnum(CalendarProviderType, name="calendar_provider_type"), default=CalendarProviderType.internal
    )
    # Encrypted at rest (Supabase Vault or app-level envelope encryption before write) —
    # holds OAuth tokens / calendar IDs for google_calendar and cal_com.
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Appointment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "appointments"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    provider_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    # If the clinic uses an external calendar, this is that system's event id —
    # lets us reconcile/cancel on the external side too.
    external_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(AppointmentStatus, name="appointment_status"), default=AppointmentStatus.booked
    )
    booked_by: Mapped[BookedBy] = mapped_column(SAEnum(BookedBy, name="booked_by"), default=BookedBy.ai)
