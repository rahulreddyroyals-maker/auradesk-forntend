"""add audit_logs table

Revision ID: 0772ed272792
Revises: e21b52c5efd9
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0772ed272792"
down_revision = "e21b52c5efd9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),  # null for system/webhook-triggered events
        sa.Column("event_type", sa.String(64), nullable=False),  # e.g. staff_invited, staff_removed, role_changed, patient_deleted, integration_credentials_saved, escalation_resolved
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        # Deliberately named metadata_json, not detail/content — a reminder
        # at the schema level that this must never hold message content,
        # secrets, or PHI, only safe structured facts about the event.
        sa.Column("metadata_json", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_clinic_id", "audit_logs", ["clinic_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
