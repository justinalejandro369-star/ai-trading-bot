"""Create paper trading tables.

Revision ID: 004
Revises: 003
Create Date: 2026-04-08

Creates three tables for the Phase 4 paper trading simulator:
  - paper_accounts: account configuration and cash balance
  - paper_positions: open positions per account
  - equity_snapshots: point-in-time equity curve snapshots
"""
import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # paper_accounts has no FK dependencies — create first
    op.create_table(
        "paper_accounts",
        sa.Column("id",               sa.Integer,                nullable=False, autoincrement=True),
        sa.Column("name",             sa.String(100),            nullable=False),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False),
        sa.Column("starting_balance", sa.Float,                  nullable=False),
        sa.Column("cash_balance",     sa.Float,                  nullable=False),
        sa.Column("slippage_std",     sa.Float,                  nullable=False, server_default="0.001"),
        sa.Column("commission",       sa.Float,                  nullable=False, server_default="0.001"),
        sa.Column("backtest_run_id",  sa.Integer,                nullable=True),
        sa.ForeignKeyConstraint(["backtest_run_id"], ["backtest_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # paper_positions FKs to paper_accounts
    op.create_table(
        "paper_positions",
        sa.Column("id",              sa.Integer,                nullable=False, autoincrement=True),
        sa.Column("account_id",      sa.Integer,                nullable=False),
        sa.Column("symbol",          sa.String(20),             nullable=False),
        sa.Column("interval",        sa.String(5),              nullable=False, server_default="1D"),
        sa.Column("quantity",        sa.Float,                  nullable=False),
        sa.Column("avg_entry_price", sa.Float,                  nullable=False),
        sa.Column("opened_at",       sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_positions_account_id", "paper_positions", ["account_id"])

    # equity_snapshots FKs to paper_accounts
    op.create_table(
        "equity_snapshots",
        sa.Column("id",              sa.Integer,                nullable=False, autoincrement=True),
        sa.Column("account_id",      sa.Integer,                nullable=False),
        sa.Column("recorded_at",     sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity_value",    sa.Float,                  nullable=False),
        sa.Column("cash",            sa.Float,                  nullable=False),
        sa.Column("positions_value", sa.Float,                  nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equity_snapshots_account_id", "equity_snapshots", ["account_id"])


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_index("ix_equity_snapshots_account_id", table_name="equity_snapshots")
    op.drop_table("equity_snapshots")
    op.drop_index("ix_paper_positions_account_id", table_name="paper_positions")
    op.drop_table("paper_positions")
    op.drop_table("paper_accounts")
