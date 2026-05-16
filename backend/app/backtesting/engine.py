"""
Vectorbt backtesting engine.

Pure function: takes an OHLCV DataFrame, a strategy instance, and
transaction-cost parameters; returns BacktestResult. No DB access, no
FastAPI imports — fully testable in isolation.

Look-ahead bias prevention:
  Entry and exit signals computed by the strategy are shifted forward
  by one bar via .shift(1).fillna(False). A signal generated from bar
  T's data is therefore applied at bar T+1's open.

Strategy abstraction:
  The engine no longer knows which scoring rules to apply. It calls
  strategy.generate_entries_exits(df) — the strategy decides. This is
  the single source of truth shared with the scanner.
"""
from __future__ import annotations

import math

import pandas as pd
import vectorbt as vbt

from app.analysis.indicators import MIN_CANDLES
from app.backtesting.models import BacktestResult
from app.strategies.base import BaseStrategy

__all__ = ["run_backtest"]


def _serialize_equity(value_series: pd.Series) -> list[list]:
    """Serialize vectorbt portfolio value Series to JSON-compatible pairs.

    Returns: [[iso_timestamp_str, float], ...]
    """
    result: list[list] = []
    for ts, val in value_series.items():
        if hasattr(ts, "isoformat"):
            ts_str = ts.isoformat()
        else:
            ts_str = str(ts)
        result.append([ts_str, float(val)])
    return result


def _safe_float(v: float, fallback: float = 0.0) -> float:
    """Return fallback if v is NaN or infinite; otherwise float(v)."""
    f = float(v)
    return fallback if (math.isnan(f) or math.isinf(f)) else f


def run_backtest(
    df: pd.DataFrame,
    strategy: BaseStrategy,
    commission: float = 0.001,
    slippage: float = 0.001,
    init_cash: float = 10_000.0,
) -> BacktestResult:
    """Run a vectorbt backtest of ``strategy`` over the OHLCV history.

    Args:
        df: OHLCV DataFrame with DatetimeIndex and columns
            [open, high, low, close, volume]. Must have >= MIN_CANDLES rows.
        strategy: BaseStrategy instance providing generate_entries_exits().
        commission: Per-trade commission fraction (0.001 = 0.1%).
        slippage: Per-trade slippage fraction (0.001 = 0.1%).
        init_cash: Starting portfolio cash in USD.

    Returns:
        BacktestResult with all performance metrics + equity curve. The
        result is tagged with strategy.name so persistence layers can
        attribute it.

    Raises:
        ValueError: If df has fewer than MIN_CANDLES rows.
    """
    if len(df) < MIN_CANDLES:
        raise ValueError(
            f"Insufficient data for backtest: {len(df)} rows < MIN_CANDLES ({MIN_CANDLES})"
        )

    entries_raw, exits_raw = strategy.generate_entries_exits(df)

    # Normalize the strategy's output: pandas Series of bool, aligned with df.
    entries_raw = pd.Series(entries_raw, index=df.index).fillna(False).astype(bool)
    exits_raw = pd.Series(exits_raw, index=df.index).fillna(False).astype(bool)

    # Look-ahead bias prevention. Signal at bar T applies at bar T+1.
    entries = entries_raw.shift(1).fillna(False).astype(bool)
    exits = exits_raw.shift(1).fillna(False).astype(bool)

    pf = vbt.Portfolio.from_signals(
        df["close"],
        entries=entries,
        exits=exits,
        fees=commission,
        slippage=slippage,
        init_cash=init_cash,
        freq="1D",
    )

    stats = pf.stats()

    win_rate_raw = stats.get("Win Rate [%]", 0.0)
    max_dd_raw = stats.get("Max Drawdown [%]", 0.0)
    profit_factor_raw = stats.get("Profit Factor", 0.0)
    sharpe_raw = pf.sharpe_ratio()
    total_return_raw = pf.total_return()

    return BacktestResult(
        strategy_name=strategy.name,
        sharpe_ratio=_safe_float(sharpe_raw),
        max_drawdown=_safe_float(-abs(max_dd_raw) / 100.0),
        win_rate=_safe_float(float(win_rate_raw) / 100.0),
        profit_factor=_safe_float(profit_factor_raw),
        total_return=_safe_float(total_return_raw),
        total_trades=int(stats.get("Total Trades", 0)),
        equity_curve=_serialize_equity(pf.value()),
    )
