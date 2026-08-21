"""initial schema

Revision ID: db787d633d5b
Revises:
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision = "db787d633d5b"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector extension is required for knowledge_base_articles.embedding (RAG).
    # uuid-ossp not required — we generate UUIDs client-side (see models/base.py).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    clinic_status = postgresql.ENUM("trial", "active", "paused", "canceled", name="clinic_status", create_type=False)
    staff_role = postgresql.ENUM("owner", "admin", "front_desk", name="staff_role", create_type=False)
    channel_type = postgresql.ENUM("voice", "sms", "web_chat", "messenger", "instagram", name="channel_type", create_type=False)
    conversation_status = postgresql.ENUM("active", "escalated", "resolved", "abandoned", name="conversation_status", create_type=False)
    conversation_outcome = postgresql.ENUM(
        "booked", "rescheduled", "faq_only", "no_action", "lost", name="conversation_outcome", create_type=False
    )
    message_role = postgresql.ENUM("patient", "ai", "staff", "system", name="message_role", create_type=False)
    calendar_provider_type = postgresql.ENUM("internal", "google_calendar", "cal_com", name="calendar_provider_type", create_type=False)
    appointment_status = postgresql.ENUM(
        "booked", "confirmed", "rescheduled", "canceled", "completed", "no_show", name="appointment_status", create_type=False
    )
    booked_by = postgresql.ENUM("ai", "staff", name="booked_by", create_type=False)

    bind = op.get_bind()
    for enum_type in (
        clinic_status, staff_role, channel_type, conversation_status,
        conversation_outcome, message_role, calendar_provider_type,
        appointment_status, booked_by,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "clinics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/New_York"),
        sa.Column("phone_number", sa.String(32)),
        sa.Column("address", sa.String(500)),
        sa.Column("hours_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("branding_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("status", clinic_status, nullable=False, server_default="trial"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_clinics_slug", "clinics", ["slug"])

    op.create_table(
        "staff",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", staff_role, nullable=False, server_default="front_desk"),
        sa.Column("phone", sa.String(32)),
        sa.Column("notification_prefs_json", postgresql.JSON, nullable=False, server_default='{"sms": true, "push": true, "email": true}'),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_staff_clinic_id", "staff", ["clinic_id"])

    op.create_table(
        "ai_employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False, server_default="Aura"),
        sa.Column("voice_id", sa.String(100)),
        sa.Column("personality_prompt", sa.String(4000), nullable=False, server_default=""),
        sa.Column("escalation_rules_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("active_hours_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("last_name", sa.String(120)),
        sa.Column("phone", sa.String(32)),
        sa.Column("email", sa.String(255)),
        sa.Column("source_channel", sa.String(32)),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("lifecycle_stage", sa.String(32), nullable=False, server_default="lead"),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_patients_clinic_id", "patients", ["clinic_id"])
    op.create_index("ix_patients_phone", "patients", ["phone"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="SET NULL")),
        sa.Column("channel", channel_type, nullable=False),
        sa.Column("status", conversation_status, nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("ai_handled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("escalated_to_staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL")),
        sa.Column("outcome", conversation_outcome),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_clinic_id", "conversations", ["clinic_id"])
    op.create_index("ix_conversations_patient_id", "conversations", ["patient_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("channel", channel_type, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("audio_url", sa.String(1000)),
        sa.Column("transcript_confidence", sa.Float),
        sa.Column("tool_calls_json", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("twilio_call_sid", sa.String(64), nullable=False, unique=True),
        sa.Column("direction", sa.String(16)),
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("recording_url", sa.String(1000)),
        sa.Column("sentiment", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_calls_twilio_call_sid", "calls", ["twilio_call_sid"])

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("price_cents", sa.Integer),
        sa.Column("description", sa.String(2000)),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_services_clinic_id", "services", ["clinic_id"])

    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("price_cents", sa.Integer, nullable=False),
        sa.Column("billing_interval", sa.String(32), nullable=False, server_default="monthly"),
        sa.Column("benefits_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memberships_clinic_id", "memberships", ["clinic_id"])

    op.create_table(
        "calendar_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("provider", calendar_provider_type, nullable=False, server_default="internal"),
        sa.Column("config_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="SET NULL")),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("provider_staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL")),
        sa.Column("external_event_id", sa.String(255)),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", appointment_status, nullable=False, server_default="booked"),
        sa.Column("booked_by", booked_by, nullable=False, server_default="ai"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_appointments_clinic_id", "appointments", ["clinic_id"])
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_start_time", "appointments", ["start_time"])

    op.create_table(
        "knowledge_base_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("question", sa.String(1000), nullable=False),
        sa.Column("answer", sa.String(5000), nullable=False),
        sa.Column("embedding", Vector(1536)),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_clinic_id", "knowledge_base_articles", ["clinic_id"])
    # IVFFlat index for cosine-distance similarity search (RAG retrieval).
    # lists=100 is a reasonable default for tens-of-thousands of rows per clinic;
    # revisit once real KB sizes are known.
    op.execute(
        "CREATE INDEX ix_kb_embedding_cosine ON knowledge_base_articles "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("urgency", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("notified_staff_ids", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_escalations_clinic_id", "escalations", ["clinic_id"])
    op.create_index("ix_escalations_conversation_id", "escalations", ["conversation_id"])

    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="disconnected"),
        sa.Column("config_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("connected_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_integrations_clinic_id", "integrations", ["clinic_id"])

    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("metadata_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usage_events_clinic_id", "usage_events", ["clinic_id"])


def downgrade() -> None:
    for table in (
        "usage_events", "integrations", "escalations", "knowledge_base_articles",
        "appointments", "calendar_connections", "memberships", "services",
        "calls", "messages", "conversations", "patients", "ai_employees",
        "staff", "clinics",
    ):
        op.drop_table(table)

    for enum_name in (
        "booked_by", "appointment_status", "calendar_provider_type", "message_role",
        "conversation_outcome", "conversation_status", "channel_type", "staff_role",
        "clinic_status",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    op.execute("DROP EXTENSION IF EXISTS vector")
