"""
Vectorbt backtesting engine.

Pure function: takes an OHLCV DataFrame and parameters, returns BacktestResult.
No DB access, no FastAPI imports — fully testable in isolation.

Look-ahead bias prevention:
  All entry/exit signals are computed from indicator data up to bar T-1
  before being applied at bar T. This is enforced by .shift(1).fillna(False).

Transaction costs:
  Passed directly to vbt.Portfolio.from_signals(fees=commission, slippage=slippage).

Signal logic mirrors score_signal() from Phase 2 (signals.py) but vectorized
across the full historical DataFrame instead of the last bar only.
"""
import math

import pandas as pd
import pandas_ta_classic as ta
import vectorbt as vbt

from app.analysis.indicators import MIN_CANDLES
from app.analysis.signals import THRESHOLD
from app.backtesting.models import BacktestResult

__all__ = ["run_backtest"]


def _compute_entries_series(df: pd.DataFrame) -> pd.Series:
    """
    Vectorized BUY entry signal across full OHLCV history.

    Mirrors score_signal() bull scoring logic from signals.py, applied to
    every bar simultaneously. Returns a boolean Series, same index as df.
    Pre-shift (before look-ahead correction) — caller applies .shift(1).
    """
    rsi = ta.rsi(df["close"], length=14)
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    bb_df = ta.bbands(df["close"], length=20, std=2)
    ema50 = ta.ema(df["close"], length=50)
    vol_sma = ta.sma(df["volume"], length=20)

    bull = pd.Series(0, index=df.index, dtype=int)
    bear = pd.Series(0, index=df.index, dtype=int)

    # RSI (25 pts)
    if rsi is not None:
        bull += ((rsi < 35).fillna(False).astype(int)) * 25
        bear += ((rsi > 65).fillna(False).astype(int)) * 25

    # MACD (30 pts)
    if macd_df is not None:
        macd_bull = (macd_df["MACD_12_26_9"] > macd_df["MACDs_12_26_9"]).fillna(False)
        bull += macd_bull.astype(int) * 30
        bear += (~macd_bull).astype(int) * 30

    # Bollinger Band position (25 pts)
    if bb_df is not None:
        bull += ((bb_df["BBP_20_2.0"] < 0.2).fillna(False).astype(int)) * 25
        bear += ((bb_df["BBP_20_2.0"] > 0.8).fillna(False).astype(int)) * 25

    # Volume surge (10 pts — guard against zero vol_sma)
    if vol_sma is not None:
        vol_surge = ((vol_sma > 0) & (df["volume"] > vol_sma * 1.5)).fillna(False)
        bull += (vol_surge & (bull >= bear)).astype(int) * 10
        bear += (vol_surge & (bear > bull)).astype(int) * 10

    # EMA50 trend (10 pts)
    if ema50 is not None:
        above_ema = (df["close"] > ema50).fillna(False)
        bull += above_ema.astype(int) * 10
        bear += (~above_ema).astype(int) * 10

    # BUY entry: bull score reaches threshold AND exceeds bear score
    return (bull >= THRESHOLD) & (bull > bear)


def _compute_exits_series(df: pd.DataFrame) -> pd.Series:
    """
    Vectorized SELL exit signal across full OHLCV history.

    Mirrors score_signal() bear scoring logic. Returns a boolean Series.
    Pre-shift — caller applies .shift(1).
    """
    rsi = ta.rsi(df["close"], length=14)
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    bb_df = ta.bbands(df["close"], length=20, std=2)
    ema50 = ta.ema(df["close"], length=50)
    vol_sma = ta.sma(df["volume"], length=20)

    bull = pd.Series(0, index=df.index, dtype=int)
    bear = pd.Series(0, index=df.index, dtype=int)

    if rsi is not None:
        bull += ((rsi < 35).fillna(False).astype(int)) * 25
        bear += ((rsi > 65).fillna(False).astype(int)) * 25

    if macd_df is not None:
        macd_bull = (macd_df["MACD_12_26_9"] > macd_df["MACDs_12_26_9"]).fillna(False)
        bull += macd_bull.astype(int) * 30
        bear += (~macd_bull).astype(int) * 30

    if bb_df is not None:
        bull += ((bb_df["BBP_20_2.0"] < 0.2).fillna(False).astype(int)) * 25
        bear += ((bb_df["BBP_20_2.0"] > 0.8).fillna(False).astype(int)) * 25

    if vol_sma is not None:
        vol_surge = ((vol_sma > 0) & (df["volume"] > vol_sma * 1.5)).fillna(False)
        bull += (vol_surge & (bull >= bear)).astype(int) * 10
        bear += (vol_surge & (bear > bull)).astype(int) * 10

    if ema50 is not None:
        above_ema = (df["close"] > ema50).fillna(False)
        bull += above_ema.astype(int) * 10
        bear += (~above_ema).astype(int) * 10

    # SELL exit: bear score reaches threshold AND exceeds bull score
    return (bear >= THRESHOLD) & (bear > bull)


def _serialize_equity(value_series: pd.Series) -> list[list]:
    """
    Serialize vectorbt portfolio value Series to JSON-compatible pairs.

    Returns: [[iso_timestamp_str, float], ...]
    """
    result = []
    for ts, val in value_series.items():
        if hasattr(ts, "isoformat"):
            ts_str = ts.isoformat()
        else:
            ts_str = str(ts)
        result.append([ts_str, float(val)])
    return result


def run_backtest(
    df: pd.DataFrame,
    commission: float = 0.001,
    slippage: float = 0.001,
    init_cash: float = 10_000.0,
) -> BacktestResult:
    """
    Run a vectorbt backtest against a historical OHLCV DataFrame.

    Args:
        df: OHLCV DataFrame with DatetimeIndex and columns
            [open, high, low, close, volume]. Must have >= MIN_CANDLES rows.
        commission: Per-trade commission fraction (0.001 = 0.1%).
        slippage: Per-trade slippage fraction (0.001 = 0.1%).
        init_cash: Starting portfolio cash in USD.

    Returns:
        BacktestResult with all performance metrics and equity curve.

    Raises:
        ValueError: If df has fewer than MIN_CANDLES rows.

    Look-ahead bias guarantee:
        entries and exits are computed from indicator data at bar T-1 and
        applied at bar T via .shift(1).fillna(False). A signal at bar T can
        never use price data from bar T's close.
    """
    if len(df) < MIN_CANDLES:
        raise ValueError(
            f"Insufficient data for backtest: {len(df)} rows < MIN_CANDLES ({MIN_CANDLES})"
        )

    # Compute raw entry/exit signals (pre-shift — these use bar T's data)
    entries_raw = _compute_entries_series(df)
    exits_raw   = _compute_exits_series(df)

    # CRITICAL: shift(1) enforces look-ahead bias prevention.
    # Signal generated from bar T's data is applied at bar T+1's open.
    entries = entries_raw.shift(1).fillna(False).astype(bool)
    exits   = exits_raw.shift(1).fillna(False).astype(bool)

    # Run vectorbt portfolio simulation
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

    # Extract metrics — convert percentages to fractions where needed.
    # Guard against NaN: vectorbt returns NaN for win_rate/profit_factor when
    # there are zero completed round-trips (e.g. only 1 trade entered, never exited).
    win_rate_raw = stats.get("Win Rate [%]", 0.0)
    max_dd_raw   = stats.get("Max Drawdown [%]", 0.0)
    profit_factor_raw = stats.get("Profit Factor", 0.0)

    def _safe_float(v: float, fallback: float = 0.0) -> float:
        """Return fallback if v is NaN or infinite; otherwise return float(v)."""
        f = float(v)
        return fallback if (math.isnan(f) or math.isinf(f)) else f

    sharpe_raw = pf.sharpe_ratio()
    total_return_raw = pf.total_return()

    return BacktestResult(
        sharpe_ratio=_safe_float(sharpe_raw),
        max_drawdown=_safe_float(-abs(max_dd_raw) / 100.0),   # negative fraction
        win_rate=_safe_float(float(win_rate_raw) / 100.0),    # fraction [0,1]
        profit_factor=_safe_float(profit_factor_raw),
        total_return=_safe_float(total_return_raw),
        total_trades=int(stats.get("Total Trades", 0)),
        equity_curve=_serialize_equity(pf.value()),
    )
