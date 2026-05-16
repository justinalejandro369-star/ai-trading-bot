"""
SQLAlchemy ORM model for the backtest_runs table.

Persists backtest results for Phase 4 paper trading comparison.
Imports Base from market_data to share the same declarative registry.
"""
import json

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.models.market_data import Base

__all__ = ["BacktestRun"]


class BacktestRun(Base):
    """
    Stores one backtest execution result per (symbol, interval, run_at).

    Multiple backtests for the same symbol are allowed — no composite PK uniqueness
    constraint. Identified by auto-incrementing integer id.
    """
    __tablename__ = "backtest_runs"

    id            = Column(Integer,                primary_key=True, autoincrement=True)
    symbol        = Column(String(20),             nullable=False, index=True)
    interval      = Column(String(5),              nullable=False)
    strategy_name = Column(String(64),             nullable=False, default="baseline", server_default="baseline", index=True)
    run_at        = Column(DateTime(timezone=True), nullable=False)
    commission    = Column(Float,                  nullable=False)
    slippage      = Column(Float,                  nullable=False)
    init_cash     = Column(Float,                  nullable=False)
    sharpe_ratio  = Column(Float,                  nullable=True)
    max_drawdown  = Column(Float,                  nullable=True)
    win_rate      = Column(Float,                  nullable=True)
    profit_factor = Column(Float,                  nullable=True)
    total_return  = Column(Float,                  nullable=True)
    total_trades  = Column(Integer,                nullable=True)
    equity_curve  = Column(Text,                   nullable=True)   # JSON string

    def equity_curve_data(self) -> list[list]:
        """Deserialize equity curve JSON to list of [timestamp, value] pairs."""
        if self.equity_curve is None:
            return []
        try:
            return json.loads(self.equity_curve)
        except (json.JSONDecodeError, TypeError):
            return []
