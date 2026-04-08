"""
SQLAlchemy ORM models for Phase 4 paper trading simulator.

Three tables track the state of simulated paper trading:
- PaperAccount: account configuration and current cash balance
- PaperPosition: open positions held by a paper account
- EquitySnapshot: point-in-time equity values for charting the equity curve

All models import Base from app.models.market_data to share the same
declarative registry as market_data, backtest_runs, and signals tables.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.models.market_data import Base

__all__ = ["PaperAccount", "PaperPosition", "EquitySnapshot"]


class PaperAccount(Base):
    """
    Represents a single paper trading account.

    Stores configuration (slippage model, commission rate) and current
    cash balance. Optionally linked to a BacktestRun for performance
    comparison in Wave 2.
    """

    __tablename__ = "paper_accounts"

    id               = Column(Integer,                 primary_key=True, autoincrement=True)
    name             = Column(String(100),             nullable=False)
    created_at       = Column(DateTime(timezone=True), nullable=False)
    starting_balance = Column(Float,                   nullable=False)
    cash_balance     = Column(Float,                   nullable=False)
    slippage_std     = Column(Float,                   nullable=False, default=0.001)
    commission       = Column(Float,                   nullable=False, default=0.001)
    backtest_run_id  = Column(Integer,                 ForeignKey("backtest_runs.id"), nullable=True)


class PaperPosition(Base):
    """
    Represents an open position within a paper account.

    One row per symbol per account. quantity and avg_entry_price are updated
    in place when additional fills occur (average-up / average-down logic
    handled by the Wave 2 route handler).
    """

    __tablename__ = "paper_positions"

    id              = Column(Integer,                 primary_key=True, autoincrement=True)
    account_id      = Column(Integer,                 ForeignKey("paper_accounts.id"), nullable=False, index=True)
    symbol          = Column(String(20),              nullable=False)
    interval        = Column(String(5),               nullable=False, default="1D")
    quantity        = Column(Float,                   nullable=False)
    avg_entry_price = Column(Float,                   nullable=False)
    opened_at       = Column(DateTime(timezone=True), nullable=False)


class EquitySnapshot(Base):
    """
    Point-in-time snapshot of a paper account's total equity.

    Recorded after each order fill and on a periodic schedule so the Wave 2
    /equity endpoint can return a time-series chart of portfolio value.
    """

    __tablename__ = "equity_snapshots"

    id              = Column(Integer,                 primary_key=True, autoincrement=True)
    account_id      = Column(Integer,                 ForeignKey("paper_accounts.id"), nullable=False, index=True)
    recorded_at     = Column(DateTime(timezone=True), nullable=False)
    equity_value    = Column(Float,                   nullable=False)
    cash            = Column(Float,                   nullable=False)
    positions_value = Column(Float,                   nullable=False)
