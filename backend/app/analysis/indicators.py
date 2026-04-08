"""
Pure-function indicator computation engine.

No DB access — takes a pandas DataFrame, returns an IndicatorSet dataclass.
Testable without any database or scheduler.

CRITICAL: Uses pandas_ta_classic (not pandas_ta).
Install: uv add pandas-ta-classic
Import: import pandas_ta_classic as ta  (module name differs from package name)
"""
from dataclasses import dataclass

import pandas as pd
import pandas_ta_classic as ta

__all__ = ["IndicatorSet", "compute_indicators", "MIN_CANDLES"]

#: Minimum candle rows before computing. EMA-200 requires exactly 200 rows.
MIN_CANDLES: int = 200


@dataclass
class IndicatorSet:
    """
    Snapshot of all computed technical indicator values for one asset.

    None fields mean insufficient data for that indicator (not an error).
    The scanner skips assets where compute_indicators() returns None entirely
    (< MIN_CANDLES rows), but individual None fields within an IndicatorSet
    are valid and are handled gracefully by the scorer.
    """
    symbol: str
    interval: str
    rsi_14: float | None
    macd_val: float | None       # MACD_12_26_9
    macd_signal: float | None   # MACDs_12_26_9
    macd_hist: float | None     # MACDh_12_26_9
    bb_upper: float | None      # BBU_20_2.0
    bb_lower: float | None      # BBL_20_2.0
    bb_pct: float | None        # BBP_20_2.0 — position within bands [0,1]
    adx_14: float | None        # ADX_14
    atr_14: float | None        # ATRr_14
    ema_50: float | None        # EMA_50
    ema_200: float | None       # EMA_200
    vol_sma_20: float | None    # SMA_20 of volume
    close: float
    volume: float


def compute_indicators(
    df: pd.DataFrame,
    symbol: str,
    interval: str,
) -> IndicatorSet | None:
    """
    Compute all technical indicators from an OHLCV DataFrame.

    Returns None if df has fewer than MIN_CANDLES rows — the caller (scanner)
    must skip this asset.

    Args:
        df: DataFrame with columns [open, high, low, close, volume].
            Index must be DatetimeIndex in ascending timestamp order.
        symbol: Asset symbol (e.g. "AAPL", "BTC/USDT") — passed through.
        interval: Candle interval (e.g. "1D") — passed through.

    Returns:
        IndicatorSet with all computed values, or None if insufficient data.

    Notes:
        - VWAP is intentionally omitted: only valid on intraday candles; 1D VWAP
          is meaningless (equals typical price).
        - volume=0.0 (CoinGecko) is handled gracefully: vol_sma_20 will be 0.0
          and the volume surge scoring component will be skipped by the scorer.
        - pandas_ta_classic raises no exceptions for insufficient lookback — it
          returns NaN-padded Series/DataFrames. The _last() helper returns None
          for all-NaN output.
    """
    if len(df) < MIN_CANDLES:
        return None

    def _last(series) -> float | None:
        """Extract last non-null float from a Series or single-column DataFrame."""
        if series is None:
            return None
        if hasattr(series, "iloc"):
            vals = series.dropna()
            return float(vals.iloc[-1]) if len(vals) > 0 else None
        return None

    rsi = ta.rsi(df["close"], length=14)
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    bb_df = ta.bbands(df["close"], length=20, std=2)
    adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
    atr = ta.atr(df["high"], df["low"], df["close"], length=14)
    ema50 = ta.ema(df["close"], length=50)
    ema200 = ta.ema(df["close"], length=200)
    vol_sma = ta.sma(df["volume"], length=20)

    return IndicatorSet(
        symbol=symbol,
        interval=interval,
        rsi_14=_last(rsi),
        macd_val=_last(macd_df["MACD_12_26_9"]) if macd_df is not None else None,
        macd_signal=_last(macd_df["MACDs_12_26_9"]) if macd_df is not None else None,
        macd_hist=_last(macd_df["MACDh_12_26_9"]) if macd_df is not None else None,
        bb_upper=_last(bb_df["BBU_20_2.0"]) if bb_df is not None else None,
        bb_lower=_last(bb_df["BBL_20_2.0"]) if bb_df is not None else None,
        bb_pct=_last(bb_df["BBP_20_2.0"]) if bb_df is not None else None,
        adx_14=_last(adx_df["ADX_14"]) if adx_df is not None else None,
        atr_14=_last(atr),
        ema_50=_last(ema50),
        ema_200=_last(ema200),
        vol_sma_20=_last(vol_sma),
        close=float(df["close"].iloc[-1]),
        volume=float(df["volume"].iloc[-1]),
    )
