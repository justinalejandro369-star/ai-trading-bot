"""Add explanation column to signals table.

Revision ID: 007
Revises: 006
Create Date: 2026-04-08

Adds explanation (TEXT, nullable) to store cached LLM-generated plain-language
signal explanations. Empty string when LLM is disabled or not yet generated.
"""
import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "signals",
        sa.Column("explanation", sa.Text, nullable=True, server_default=""),
    )
    op.add_column(
        "signals",
        sa.Column("multiframe_agreement", sa.Text, nullable=True, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("signals", "multiframe_agreement")
    op.drop_column("signals", "explanation")
