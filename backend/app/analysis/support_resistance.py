# backend/app/analysis/support_resistance.py
# Horizontal support and resistance level detection from OHLCV swing points.
# Clusters nearby price levels and scores by touch count and recency.
# RELEVANT FILES: indicators.py, trendlines.py, fibonacci.py

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = ["SRLevel", "SupportResistanceLevels", "compute_support_resistance"]

# Same swing detection window as trendlines.py for consistency
_SWING_WINDOW = 5


@dataclass(frozen=True)
class SRLevel:
    """A single support or resistance price level."""
    price: float
    level_type: str   # "support", "resistance", or "both"
    touches: int
    first_touch_time: str  # ISO timestamp
    last_touch_time: str   # ISO timestamp
    strength: float        # 0-1 score


@dataclass(frozen=True)
class SupportResistanceLevels:
    """Collection of detected S/R levels, sorted by strength descending."""
    levels: list[SRLevel] = field(default_factory=list)


def _detect_swing_points(
    highs: np.ndarray,
    lows: np.ndarray,
    timestamps: pd.DatetimeIndex,
    window: int = _SWING_WINDOW,
) -> list[tuple[float, str, pd.Timestamp]]:
    """
    Detect local swing highs and lows, returning (price, type, timestamp) tuples.

    type is "high" or "low", used later to classify S/R levels.
    """
    half = window // 2
    points = []

    for i in range(half, len(highs) - half):
        # Check for local high
        high_window = highs[i - half: i + half + 1]
        if highs[i] == high_window.max():
            points.append((float(highs[i]), "high", timestamps[i]))

        # Check for local low
        low_window = lows[i - half: i + half + 1]
        if lows[i] == low_window.min():
            points.append((float(lows[i]), "low", timestamps[i]))

    return points


def compute_support_resistance(
    df: pd.DataFrame,
    tolerance_pct: float = 0.015,
    min_touches: int = 2,
) -> SupportResistanceLevels:
    """
    Detect horizontal support and resistance levels from OHLCV data.

    Algorithm:
    1. Collect all local swing highs and lows using a 5-candle window
    2. Cluster nearby prices within tolerance_pct of each other
    3. Classify clusters: mostly lows → support, mostly highs → resistance, mixed → both
    4. Score by touches × recency_weight, return top 10

    Args:
        df: DataFrame with [open, high, low, close], DatetimeIndex ascending.
        tolerance_pct: Maximum price difference (as fraction) to cluster points together.
        min_touches: Minimum touch count to qualify as a level.

    Returns:
        SupportResistanceLevels with up to 10 strongest levels.
    """
    if len(df) < _SWING_WINDOW + 2:
        return SupportResistanceLevels(levels=[])

    highs = df["high"].values.astype(float)
    lows = df["low"].values.astype(float)
    timestamps = df.index

    swing_points = _detect_swing_points(highs, lows, timestamps)
    if not swing_points:
        return SupportResistanceLevels(levels=[])

    # Sort swing points by price for clustering
    swing_points.sort(key=lambda p: p[0])

    # Cluster nearby prices: greedily group points within tolerance_pct
    clusters: list[list[tuple[float, str, pd.Timestamp]]] = []
    current_cluster: list[tuple[float, str, pd.Timestamp]] = [swing_points[0]]

    for i in range(1, len(swing_points)):
        price = swing_points[i][0]
        cluster_avg = np.mean([p[0] for p in current_cluster])

        # Check if this point is within tolerance of the cluster average
        if abs(price - cluster_avg) / cluster_avg <= tolerance_pct:
            current_cluster.append(swing_points[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [swing_points[i]]

    clusters.append(current_cluster)

    # Convert clusters to SRLevel objects
    # Use the last timestamp in the full DataFrame for recency weighting
    last_time = timestamps[-1]
    total_span = (timestamps[-1] - timestamps[0]).total_seconds() or 1.0

    levels: list[SRLevel] = []
    for cluster in clusters:
        touches = len(cluster)
        if touches < min_touches:
            continue

        # Average price of the cluster
        avg_price = float(np.mean([p[0] for p in cluster]))

        # Classify: count highs vs lows in the cluster
        high_count = sum(1 for p in cluster if p[1] == "high")
        low_count = sum(1 for p in cluster if p[1] == "low")

        if high_count > 0 and low_count > 0:
            level_type = "both"
        elif low_count > high_count:
            level_type = "support"
        else:
            level_type = "resistance"

        # Timestamps
        cluster_times = [p[2] for p in cluster]
        first_touch = min(cluster_times)
        last_touch = max(cluster_times)

        # Recency weight: more recent last touch → higher weight (0.5 to 1.0)
        recency = (last_touch - timestamps[0]).total_seconds() / total_span
        recency_weight = 0.5 + 0.5 * recency

        # Strength: touches * recency, normalized to 0-1 range
        # Cap at 1.0; a cluster with 5+ touches and recent activity gets max score
        raw_strength = touches * recency_weight
        strength = min(1.0, raw_strength / 5.0)

        levels.append(SRLevel(
            price=round(avg_price, 6),
            level_type=level_type,
            touches=touches,
            first_touch_time=first_touch.isoformat(),
            last_touch_time=last_touch.isoformat(),
            strength=round(strength, 4),
        ))

    # Sort by strength descending, return top 10
    levels.sort(key=lambda l: l.strength, reverse=True)
    return SupportResistanceLevels(levels=levels[:10])
