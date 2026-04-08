"""Create backtest_runs table.

Revision ID: 003
Revises: 002
Create Date: 2026-04-08

Persists backtest execution results. Phase 4 queries this table to compare
paper trading performance against historical backtests.
"""
import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id",            sa.Integer,                nullable=False, autoincrement=True),
        sa.Column("symbol",        sa.String(20),             nullable=False),
        sa.Column("interval",      sa.String(5),              nullable=False),
        sa.Column("run_at",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("commission",    sa.Float,                  nullable=False),
        sa.Column("slippage",      sa.Float,                  nullable=False),
        sa.Column("init_cash",     sa.Float,                  nullable=False),
        sa.Column("sharpe_ratio",  sa.Float,                  nullable=True),
        sa.Column("max_drawdown",  sa.Float,                  nullable=True),
        sa.Column("win_rate",      sa.Float,                  nullable=True),
        sa.Column("profit_factor", sa.Float,                  nullable=True),
        sa.Column("total_return",  sa.Float,                  nullable=True),
        sa.Column("total_trades",  sa.Integer,                nullable=True),
        sa.Column("equity_curve",  sa.Text,                   nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backtest_runs_symbol", "backtest_runs", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_backtest_runs_symbol", table_name="backtest_runs")
    op.drop_table("backtest_runs")
