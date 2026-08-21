import uuid

from sqlalchemy import ARRAY, DateTime, ForeignKey, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Patient(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "patients"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    source_channel: Mapped[str | None] = mapped_column(String(32))  # voice|sms|web_chat|messenger|instagram|manual
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    lifecycle_stage: Mapped[str] = mapped_column(String(32), default="lead")  # lead|patient|member
    last_contacted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_ids_json: Mapped[dict] = mapped_column(JSON, default=dict)  # {"messenger": "<PSID>", "instagram": "<IGSID>"}
