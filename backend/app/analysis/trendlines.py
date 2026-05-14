# backend/app/analysis/trendlines.py
# Auto-detected trend lines from OHLCV swing points using linear regression.
# Returns max 4 strongest lines (ascending + descending) for chart overlay.
# RELEVANT FILES: indicators.py, support_resistance.py, fibonacci.py

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = ["TrendLine", "TrendLineSet", "compute_trendlines"]

# Swing detection window: a local min/max must be the extreme within this many
# candles on each side. 5 candles = 2 on each side + center.
_SWING_WINDOW = 5


@dataclass(frozen=True)
class TrendLine:
    """A single detected trend line between two swing points."""
    start_time: str   # ISO timestamp
    start_price: float
    end_time: str     # ISO timestamp
    end_price: float
    slope: float      # Price change per candle
    direction: str    # "ascending" or "descending"
    touches: int      # Number of price points touching this line
    strength: float   # 0-1 score (touches * R-squared, normalized)


@dataclass(frozen=True)
class TrendLineSet:
    """Collection of auto-detected trend lines, sorted by strength descending."""
    lines: list[TrendLine] = field(default_factory=list)


def _detect_swing_lows(lows: np.ndarray, window: int = _SWING_WINDOW) -> list[int]:
    """Find indices of local minima in the lows array using a rolling window."""
    half = window // 2
    swings = []
    for i in range(half, len(lows) - half):
        window_slice = lows[i - half: i + half + 1]
        if lows[i] == window_slice.min():
            swings.append(i)
    return swings


def _detect_swing_highs(highs: np.ndarray, window: int = _SWING_WINDOW) -> list[int]:
    """Find indices of local maxima in the highs array using a rolling window."""
    half = window // 2
    swings = []
    for i in range(half, len(highs) - half):
        window_slice = highs[i - half: i + half + 1]
        if highs[i] == window_slice.max():
            swings.append(i)
    return swings


def _count_touches(
    prices: np.ndarray,
    start_idx: int,
    end_idx: int,
    start_price: float,
    slope: float,
    tolerance: float,
) -> int:
    """
    Count how many price points lie within `tolerance` of the trend line.

    The line is defined by start_price at start_idx with the given slope.
    We check all points between start_idx and end_idx inclusive.
    """
    count = 0
    for i in range(start_idx, min(end_idx + 1, len(prices))):
        expected = start_price + slope * (i - start_idx)
        if abs(prices[i] - expected) <= tolerance:
            count += 1
    return count


def compute_trendlines(
    df: pd.DataFrame,
    min_touches: int = 3,
    lookback: int = 100,
) -> TrendLineSet:
    """
    Auto-detect ascending and descending trend lines from OHLCV data.

    Algorithm:
    1. Detect local minima (swing lows) and maxima (swing highs) using a 5-candle window
    2. For each pair of swing lows → fit ascending line, count touches within 0.5×ATR
    3. For each pair of swing highs → fit descending line, same counting
    4. Filter by min_touches, rank by touches × R-squared proxy, return top 4

    Args:
        df: DataFrame with [open, high, low, close], DatetimeIndex ascending.
        min_touches: Minimum touch points to qualify as a valid trend line.
        lookback: Number of recent candles to analyze.

    Returns:
        TrendLineSet with up to 4 strongest trend lines.
    """
    if len(df) < _SWING_WINDOW + 2:
        return TrendLineSet(lines=[])

    window = df.tail(lookback).copy()
    highs = window["high"].values.astype(float)
    lows = window["low"].values.astype(float)
    timestamps = window.index

    # Use ATR-like measure for touch tolerance: average true range over the window
    # Simplified: mean of (high - low) over the window * 0.5
    avg_range = float(np.mean(highs - lows))
    tolerance = avg_range * 0.5

    # Avoid division by zero on flat data
    if tolerance <= 0:
        return TrendLineSet(lines=[])

    swing_low_indices = _detect_swing_lows(lows)
    swing_high_indices = _detect_swing_highs(highs)

    candidates: list[TrendLine] = []

    # Ascending lines: connect pairs of swing lows where the second is higher
    for i in range(len(swing_low_indices)):
        for j in range(i + 1, len(swing_low_indices)):
            idx_a = swing_low_indices[i]
            idx_b = swing_low_indices[j]
            price_a = lows[idx_a]
            price_b = lows[idx_b]

            # Skip if not ascending
            if price_b <= price_a:
                continue

            span = idx_b - idx_a
            if span == 0:
                continue
            slope = (price_b - price_a) / span

            touches = _count_touches(lows, idx_a, idx_b, price_a, slope, tolerance)
            if touches < min_touches:
                continue

            # Strength: touches normalized by span, capped at 1.0
            strength = min(1.0, touches / max(span * 0.5, 1.0))

            candidates.append(TrendLine(
                start_time=timestamps[idx_a].isoformat(),
                start_price=round(price_a, 6),
                end_time=timestamps[idx_b].isoformat(),
                end_price=round(price_b, 6),
                slope=round(slope, 6),
                direction="ascending",
                touches=touches,
                strength=round(strength, 4),
            ))

    # Descending lines: connect pairs of swing highs where the second is lower
    for i in range(len(swing_high_indices)):
        for j in range(i + 1, len(swing_high_indices)):
            idx_a = swing_high_indices[i]
            idx_b = swing_high_indices[j]
            price_a = highs[idx_a]
            price_b = highs[idx_b]

            # Skip if not descending
            if price_b >= price_a:
                continue

            span = idx_b - idx_a
            if span == 0:
                continue
            slope = (price_b - price_a) / span

            touches = _count_touches(highs, idx_a, idx_b, price_a, slope, tolerance)
            if touches < min_touches:
                continue

            strength = min(1.0, touches / max(span * 0.5, 1.0))

            candidates.append(TrendLine(
                start_time=timestamps[idx_a].isoformat(),
                start_price=round(price_a, 6),
                end_time=timestamps[idx_b].isoformat(),
                end_price=round(price_b, 6),
                slope=round(slope, 6),
                direction="descending",
                touches=touches,
                strength=round(strength, 4),
            ))

    # Sort by strength descending, return top 4
    candidates.sort(key=lambda t: t.strength, reverse=True)
    return TrendLineSet(lines=candidates[:4])
