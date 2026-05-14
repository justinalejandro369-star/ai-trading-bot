# backend/app/analysis/indicator_series.py
# Full time-series indicator computation for chart overlays.
# Unlike indicators.py (returns last scalar), this returns full arrays for rendering.
# RELEVANT FILES: indicators.py, api/routes/indicators.py, api/routes/indicator_series.py

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import pandas_ta_classic as ta

from app.analysis.indicators import MIN_CANDLES

__all__ = ["IndicatorSeriesSet", "compute_indicator_series"]


@dataclass(frozen=True)
class IndicatorSeriesSet:
    """
    Full time-series arrays for every indicator, ready for chart overlay rendering.

    Each list aligns 1:1 with `timestamps`. None values represent insufficient
    lookback (e.g. EMA-200 has 199 leading Nones). The frontend skips None entries
    when plotting series.
    """
    symbol: str
    interval: str
    timestamps: list[str] = field(default_factory=list)
    # Trend overlays (main pane)
    ema_50: list[Optional[float]] = field(default_factory=list)
    ema_200: list[Optional[float]] = field(default_factory=list)
    # Bollinger Bands (main pane)
    bb_upper: list[Optional[float]] = field(default_factory=list)
    bb_lower: list[Optional[float]] = field(default_factory=list)
    bb_mid: list[Optional[float]] = field(default_factory=list)
    # RSI oscillator (sub-pane 1)
    rsi_14: list[Optional[float]] = field(default_factory=list)
    # MACD (sub-pane 2)
    macd_val: list[Optional[float]] = field(default_factory=list)
    macd_signal: list[Optional[float]] = field(default_factory=list)
    macd_hist: list[Optional[float]] = field(default_factory=list)
    # Volume (main pane, low opacity)
    volume: list[float] = field(default_factory=list)
    vol_sma_20: list[Optional[float]] = field(default_factory=list)


def _series_to_list(series: pd.Series | None) -> list[Optional[float]]:
    """Convert a pandas Series to a list, replacing NaN with None for JSON."""
    if series is None:
        return []
    return [None if pd.isna(v) else float(v) for v in series]


def compute_indicator_series(
    df: pd.DataFrame,
    symbol: str,
    interval: str,
) -> IndicatorSeriesSet | None:
    """
    Compute full time-series arrays for all chart overlay indicators.

    Same pandas_ta_classic calls as compute_indicators(), but returns the entire
    Series as lists instead of just the last value. This powers the frontend chart
    overlays (EMA lines, Bollinger Bands, RSI pane, MACD pane, volume bars).

    Args:
        df: DataFrame with [open, high, low, close, volume], DatetimeIndex ascending.
        symbol: Asset symbol (e.g. "AAPL").
        interval: Candle interval (e.g. "1D").

    Returns:
        IndicatorSeriesSet with aligned arrays, or None if len(df) < MIN_CANDLES.
    """
    if len(df) < MIN_CANDLES:
        return None

    # Compute all indicators — same calls as indicators.py
    rsi = ta.rsi(df["close"], length=14)
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    bb_df = ta.bbands(df["close"], length=20, std=2)
    ema50 = ta.ema(df["close"], length=50)
    ema200 = ta.ema(df["close"], length=200)
    vol_sma = ta.sma(df["volume"], length=20)

    # Bollinger mid band is SMA(20) of close — compute separately since
    # pandas_ta_classic bbands doesn't include a midline column by default
    bb_mid = ta.sma(df["close"], length=20)

    # Convert timestamps to ISO strings for JSON serialization
    timestamps = [ts.isoformat() for ts in df.index]

    return IndicatorSeriesSet(
        symbol=symbol,
        interval=interval,
        timestamps=timestamps,
        ema_50=_series_to_list(ema50),
        ema_200=_series_to_list(ema200),
        bb_upper=_series_to_list(bb_df["BBU_20_2.0"]) if bb_df is not None else [],
        bb_lower=_series_to_list(bb_df["BBL_20_2.0"]) if bb_df is not None else [],
        bb_mid=_series_to_list(bb_mid),
        rsi_14=_series_to_list(rsi),
        macd_val=_series_to_list(macd_df["MACD_12_26_9"]) if macd_df is not None else [],
        macd_signal=_series_to_list(macd_df["MACDs_12_26_9"]) if macd_df is not None else [],
        macd_hist=_series_to_list(macd_df["MACDh_12_26_9"]) if macd_df is not None else [],
        volume=[float(v) for v in df["volume"]],
        vol_sma_20=_series_to_list(vol_sma),
    )
