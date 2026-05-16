"""
Example strategy: EMA-50 / EMA-200 golden-cross / death-cross.

This file is intentionally small and heavily commented — it doubles as
the canonical "how to write your own strategy" reference. Copy this
file, change the name + math, register it, and you have a new strategy
plugged into the scanner, backtester, paper trader, and UI.

To add a new strategy:
    1. Copy this file to backend/app/strategies/your_strategy.py
    2. Rename the class and update name / version / description
    3. Replace the body of generate_signal() and generate_entries_exits()
    4. Add `from app.strategies import your_strategy as _your` to
       app/strategies/__init__.py (so the decorator runs at import time)
    5. Run pytest tests/test_strategies.py — registry + round-trip tests
       should pass
"""
from __future__ import annotations

import pandas as pd
import pandas_ta_classic as ta

from app.analysis.indicators import IndicatorSet
from app.analysis.signals import SignalResult
from app.strategies import register_strategy
from app.strategies.base import BaseStrategy

__all__ = ["MACrossoverStrategy"]


@register_strategy
class MACrossoverStrategy(BaseStrategy):
    """EMA-50 above EMA-200 → BUY; EMA-50 below EMA-200 → SELL.

    Classic trend-following filter. Confidence is fixed at 70 because
    crossovers are binary — they either happened or didn't. Stop-loss
    and target use ATR(14) when available, otherwise fixed percentages.
    """

    name = "ma_crossover"
    version = "1.0.0"
    description = "EMA-50 vs EMA-200 trend filter (golden cross / death cross)."
    required_indicators = ["EMA50", "EMA200"]

    def generate_signal(self, ind: IndicatorSet) -> SignalResult:
        # No EMAs? Cannot decide — abstain.
        if ind.ema_50 is None or ind.ema_200 is None:
            return SignalResult(
                direction="HOLD",
                confidence=0,
                entry_price=ind.close,
                stop_loss=None,
                target_price=None,
                reasons=["EMA-50 or EMA-200 unavailable"],
            )

        atr = ind.atr_14
        stop_loss = (ind.close - 2 * atr) if atr is not None else ind.close * 0.97
        target_price = (ind.close + 3 * atr) if atr is not None else ind.close * 1.05

        if ind.ema_50 > ind.ema_200:
            return SignalResult(
                direction="BUY",
                confidence=70,
                entry_price=ind.close,
                stop_loss=stop_loss,
                target_price=target_price,
                reasons=[
                    f"EMA-50 ({ind.ema_50:.2f}) above EMA-200 ({ind.ema_200:.2f}) — uptrend",
                ],
            )

        return SignalResult(
            direction="SELL",
            confidence=70,
            entry_price=ind.close,
            stop_loss=None,
            target_price=None,
            reasons=[
                f"EMA-50 ({ind.ema_50:.2f}) below EMA-200 ({ind.ema_200:.2f}) — downtrend",
            ],
        )

    def generate_entries_exits(
        self, df: pd.DataFrame
    ) -> tuple[pd.Series, pd.Series]:
        fast = ta.ema(df["close"], length=50)
        slow = ta.ema(df["close"], length=200)

        if fast is None or slow is None:
            empty = pd.Series(False, index=df.index)
            return empty, empty

        # Golden cross: fast crosses above slow (first bar where fast > slow
        # and the prior bar had fast <= slow).
        prev_below = (fast.shift(1) <= slow.shift(1)).fillna(False)
        now_above = (fast > slow).fillna(False)
        entries = (prev_below & now_above).fillna(False)

        # Death cross: fast crosses below slow.
        prev_above = (fast.shift(1) >= slow.shift(1)).fillna(False)
        now_below = (fast < slow).fillna(False)
        exits = (prev_above & now_below).fillna(False)

        return entries, exits
