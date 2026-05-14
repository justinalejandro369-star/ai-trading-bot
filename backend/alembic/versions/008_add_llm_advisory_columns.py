"""Add LLM advisory columns to signals table.

Revision ID: 008
Revises: 007
Create Date: 2026-04-08

Adds llm_adjustment (Integer), llm_reasoning (Text), and llm_patterns (Text)
to store LLM advisory signal scoring data.
"""
import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "signals",
        sa.Column("llm_adjustment", sa.Integer, nullable=True, server_default="0"),
    )
    op.add_column(
        "signals",
        sa.Column("llm_reasoning", sa.Text, nullable=True, server_default=""),
    )
    op.add_column(
        "signals",
        sa.Column("llm_patterns", sa.Text, nullable=True, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("signals", "llm_patterns")
    op.drop_column("signals", "llm_reasoning")
    op.drop_column("signals", "llm_adjustment")
