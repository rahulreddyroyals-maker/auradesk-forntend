"""add patient external_ids_json

Revision ID: 45eb7a1e0395
Revises: db787d633d5b
Create Date: 2026-08-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "45eb7a1e0395"
down_revision = "db787d633d5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("external_ids_json", postgresql.JSON, nullable=False, server_default="{}"),
    )
    # e.g. {"messenger": "<PSID>", "instagram": "<IGSID>"} — lets us find/create
    # a Patient for channels that don't give us a phone number.


def downgrade() -> None:
    op.drop_column("patients", "external_ids_json")
