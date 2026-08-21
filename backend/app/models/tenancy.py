import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
import enum


class ClinicStatus(str, enum.Enum):
    trial = "trial"
    active = "active"
    paused = "paused"
    canceled = "canceled"


class StaffRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    front_desk = "front_desk"


class Clinic(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    phone_number: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(String(500))
    hours_json: Mapped[dict] = mapped_column(JSON, default=dict)  # {"mon": ["09:00","18:00"], ...}
    branding_json: Mapped[dict] = mapped_column(JSON, default=dict)  # {logo_url, primary_color, ...}
    status: Mapped[ClinicStatus] = mapped_column(
        SAEnum(ClinicStatus, name="clinic_status"), default=ClinicStatus.trial
    )

    staff: Mapped[list["Staff"]] = relationship(back_populates="clinic", cascade="all, delete-orphan")
    ai_employee: Mapped["AIEmployee | None"] = relationship(
        back_populates="clinic", cascade="all, delete-orphan", uselist=False
    )


class Staff(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "staff"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)  # -> auth.users.id
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[StaffRole] = mapped_column(SAEnum(StaffRole, name="staff_role"), default=StaffRole.front_desk)
    phone: Mapped[str | None] = mapped_column(String(32))
    notification_prefs_json: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"sms": True, "push": True, "email": True}
    )

    clinic: Mapped["Clinic"] = relationship(back_populates="staff")


class AIEmployee(UUIDPKMixin, TimestampMixin, Base):
    """
    The configurable "AI staff member" for a clinic. One per clinic in v1
    (multiple personas per clinic is a plausible future extension, hence
    a dedicated table rather than columns on `clinics`).
    """

    __tablename__ = "ai_employees"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), default="Aura")
    voice_id: Mapped[str | None] = mapped_column(String(100))  # Cartesia/ElevenLabs voice identifier
    personality_prompt: Mapped[str] = mapped_column(String(4000), default="")
    escalation_rules_json: Mapped[dict] = mapped_column(JSON, default=dict)
    active_hours_json: Mapped[dict] = mapped_column(JSON, default=dict)  # can differ from clinic hours
    status: Mapped[str] = mapped_column(String(32), default="active")  # active | paused

    clinic: Mapped["Clinic"] = relationship(back_populates="ai_employee")
