"""
Baseline weighted-confluence strategy.

Wraps the legacy ``app.analysis.signals.score_signal()`` so existing
behavior is preserved verbatim, then moves the vectorized entry/exit
logic out of ``app.backtesting.engine`` into a single source of truth.

The parity test in ``tests/test_strategies.py`` locks
``BaselineStrategy().generate_signal(ind) == score_signal(ind)`` so any
future refactor of the scoring rules has a regression net.

Scoring (total 100 pts, THRESHOLD = 55):
    RSI(14)          25 pts   < 35 bull / > 65 bear
    MACD(12,26,9)    30 pts   MACD line vs signal line
    Bollinger %B     25 pts   < 0.2 bull / > 0.8 bear
    Volume surge     10 pts   volume > 1.5x SMA(20) — amplifies leader
    EMA50 trend      10 pts   close vs EMA50
"""
from __future__ import annotations

import pandas as pd
import pandas_ta_classic as ta

from app.analysis.indicators import IndicatorSet
from app.analysis.signals import SignalResult, THRESHOLD, score_signal
from app.strategies import register_strategy
from app.strategies.base import BaseStrategy

__all__ = ["BaselineStrategy"]


@register_strategy
class BaselineStrategy(BaseStrategy):
    """Confluence scoring across RSI, MACD, Bollinger, volume, and EMA50."""

    name = "baseline"
    version = "1.0.0"
    description = (
        "Weighted confluence: RSI(25) + MACD(30) + Bollinger(25) + Volume(10) + EMA50(10). "
        "Threshold 55 to fire BUY/SELL; otherwise HOLD."
    )
    required_indicators = ["RSI", "MACD", "BB", "EMA50", "VOL_SMA"]

    def generate_signal(self, ind: IndicatorSet) -> SignalResult:
        # Delegate to legacy pure function — the parity test locks them.
        return score_signal(ind)

    def generate_entries_exits(
        self, df: pd.DataFrame
    ) -> tuple[pd.Series, pd.Series]:
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

        # Bollinger %B (25 pts)
        if bb_df is not None:
            bull += ((bb_df["BBP_20_2.0"] < 0.2).fillna(False).astype(int)) * 25
            bear += ((bb_df["BBP_20_2.0"] > 0.8).fillna(False).astype(int)) * 25

        # Volume surge (10 pts) — amplifies the leading direction
        if vol_sma is not None:
            vol_surge = ((vol_sma > 0) & (df["volume"] > vol_sma * 1.5)).fillna(False)
            bull += (vol_surge & (bull >= bear)).astype(int) * 10
            bear += (vol_surge & (bear > bull)).astype(int) * 10

        # EMA50 trend (10 pts)
        if ema50 is not None:
            above_ema = (df["close"] > ema50).fillna(False)
            bull += above_ema.astype(int) * 10
            bear += (~above_ema).astype(int) * 10

        entries = (bull >= THRESHOLD) & (bull > bear)
        exits = (bear >= THRESHOLD) & (bear > bull)
        return entries, exits
