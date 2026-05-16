"""Add strategy_name to signals (extends PK) and backtest_runs.

Revision ID: 009
Revises: 008
Create Date: 2026-05-16

Pluggable strategy interface ships in this milestone. Multiple strategies
must be able to coexist for the same (symbol, interval). The signals PK
is therefore extended to (symbol, interval, strategy_name) and the
backtest_runs table gains a strategy_name column + index.

Existing rows backfill with 'baseline' — the legacy scoring rules are
now packaged as ``BaselineStrategy``.
"""
import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # signals: add strategy_name and rewrite the primary key. batch_alter_table
    # is required for SQLite (used in tests) — it recreates the table under the
    # hood. PostgreSQL/TimescaleDB tolerates the same syntax.
    with op.batch_alter_table("signals", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column(
                "strategy_name",
                sa.String(64),
                nullable=False,
                server_default="baseline",
            )
        )
        batch_op.create_primary_key(
            "pk_signals",
            ["symbol", "interval", "strategy_name"],
        )

    # backtest_runs: simple additive change — strategy_name plus an index for
    # the GET /api/backtest/runs?strategy=... filter.
    op.add_column(
        "backtest_runs",
        sa.Column(
            "strategy_name",
            sa.String(64),
            nullable=False,
            server_default="baseline",
        ),
    )
    op.create_index(
        "ix_backtest_runs_symbol_strategy",
        "backtest_runs",
        ["symbol", "strategy_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_backtest_runs_symbol_strategy", table_name="backtest_runs")
    op.drop_column("backtest_runs", "strategy_name")

    with op.batch_alter_table("signals", recreate="always") as batch_op:
        batch_op.drop_column("strategy_name")
        batch_op.create_primary_key(
            "pk_signals",
            ["symbol", "interval"],
        )
