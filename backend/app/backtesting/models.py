"""
Data contracts for the backtesting engine.

BacktestResult: pure Python dataclass returned by run_backtest().
BacktestRequest: Pydantic model for the POST /api/backtest request body.

No DB access in this file — it is imported by both engine.py and the API route.
"""
from dataclasses import asdict, dataclass

from pydantic import BaseModel, Field

__all__ = ["BacktestRequest", "BacktestResult"]


@dataclass
class BacktestResult:
    """
    Backtest output metrics returned by run_backtest().

    All float metrics are stored as fractions (not percentages):
      win_rate=0.60 means 60%, max_drawdown=-0.25 means -25%.

    equity_curve is a list of [iso_timestamp, portfolio_value] pairs
    suitable for direct JSON serialization in the API response.
    """
    sharpe_ratio: float
    max_drawdown: float       # fraction, e.g. -0.25 = -25%
    win_rate: float           # fraction, e.g. 0.60 = 60%
    profit_factor: float
    total_return: float       # fraction, e.g. 0.35 = +35%
    total_trades: int
    equity_curve: list[list]  # [[iso_timestamp_str, float], ...]

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict for API responses."""
        return asdict(self)


class BacktestRequest(BaseModel):
    """
    Request body for POST /api/backtest.

    symbol and interval must match a stored asset in the market_data table.
    commission and slippage are per-trade fractions (0.001 = 0.1%).
    """
    symbol: str = Field(..., description="Asset symbol, e.g. 'AAPL' or 'BTC/USDT'")
    interval: str = Field(default="1D", description="Candle interval, e.g. '1D', '1H'")
    commission: float = Field(default=0.001, ge=0.0, le=0.1, description="Commission fraction per trade (0.001 = 0.1%)")
    slippage: float = Field(default=0.001, ge=0.0, le=0.1, description="Slippage fraction per trade (0.001 = 0.1%)")
    init_cash: float = Field(default=10_000.0, gt=0.0, description="Starting portfolio cash in USD")
