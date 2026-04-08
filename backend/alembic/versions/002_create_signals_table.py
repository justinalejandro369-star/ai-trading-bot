"""Create signals table.

Revision ID: 002
Revises: 001
Create Date: 2026-04-08

Stores one row per (symbol, interval) — the latest trading signal.
ON CONFLICT DO UPDATE (not DO NOTHING) is used by the scanner upsert.
"""
import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signals",
        sa.Column("symbol",       sa.String(20),             nullable=False),
        sa.Column("interval",     sa.String(5),              nullable=False),
        sa.Column("scanned_at",   sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction",    sa.String(4),              nullable=False),
        sa.Column("confidence",   sa.Integer,                nullable=False),
        sa.Column("regime",       sa.String(10),             nullable=False),
        sa.Column("close",        sa.Float,                  nullable=False),
        sa.Column("entry_price",  sa.Float,                  nullable=True),
        sa.Column("stop_loss",    sa.Float,                  nullable=True),
        sa.Column("target_price", sa.Float,                  nullable=True),
        sa.Column("rsi_14",       sa.Float,                  nullable=True),
        sa.Column("macd_val",     sa.Float,                  nullable=True),
        sa.Column("adx_14",       sa.Float,                  nullable=True),
        sa.Column("atr_14",       sa.Float,                  nullable=True),
        sa.Column("reasons",      sa.String(500),            nullable=True),
        sa.PrimaryKeyConstraint("symbol", "interval"),
    )


def downgrade() -> None:
    op.drop_table("signals")
