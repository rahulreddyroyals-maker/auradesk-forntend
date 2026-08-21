import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class ChannelType(str, enum.Enum):
    voice = "voice"
    sms = "sms"
    web_chat = "web_chat"
    messenger = "messenger"
    instagram = "instagram"


class ConversationStatus(str, enum.Enum):
    active = "active"
    escalated = "escalated"
    resolved = "resolved"
    abandoned = "abandoned"


class ConversationOutcome(str, enum.Enum):
    booked = "booked"
    rescheduled = "rescheduled"
    faq_only = "faq_only"
    no_action = "no_action"
    lost = "lost"


class MessageRole(str, enum.Enum):
    patient = "patient"
    ai = "ai"
    staff = "staff"
    system = "system"


class Conversation(UUIDPKMixin, TimestampMixin, Base):
    """
    The channel-agnostic thread. A patient who calls, then texts, then
    books via web chat can (once phone-number/identity matching applies)
    be tracked as one continuous relationship even across separate
    Conversation rows — the AI's context assembly service is responsible
    for that continuity; Conversation rows themselves are per-session.
    """

    __tablename__ = "conversations"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel: Mapped[ChannelType] = mapped_column(SAEnum(ChannelType, name="channel_type"), nullable=False)
    status: Mapped[ConversationStatus] = mapped_column(
        SAEnum(ConversationStatus, name="conversation_status"), default=ConversationStatus.active
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_handled: Mapped[bool] = mapped_column(default=True)
    escalated_to_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    outcome: Mapped[ConversationOutcome | None] = mapped_column(
        SAEnum(ConversationOutcome, name="conversation_outcome"), nullable=True
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(UUIDPKMixin, Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole, name="message_role"), nullable=False)
    channel: Mapped[ChannelType] = mapped_column(SAEnum(ChannelType, name="channel_type"), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    transcript_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_calls_json: Mapped[list] = mapped_column(JSON, default=list)  # audit trail of tools invoked this turn
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Call(UUIDPKMixin, Base):
    """1:1 with a Conversation where channel == voice."""

    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    twilio_call_sid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(16))  # inbound | outbound
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)  # positive|neutral|negative
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
