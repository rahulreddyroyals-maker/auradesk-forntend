"""add subscriptions table

Revision ID: e21b52c5efd9
Revises: 45eb7a1e0395
Create Date: 2026-08-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e21b52c5efd9"
down_revision = "45eb7a1e0395"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("stripe_subscription_id", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False, server_default="none"),  # none|trialing|active|past_due|canceled
        sa.Column("plan", sa.String(64)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_subscriptions_clinic_id", "subscriptions", ["clinic_id"])
    op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"])


def downgrade() -> None:
    op.drop_table("subscriptions")
