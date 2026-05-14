# backend/app/analysis/fibonacci.py
# Fibonacci retracement & extension level computation from OHLCV data.
# Identifies swing high/low in a lookback window and calculates standard fib levels.
# RELEVANT FILES: indicators.py, support_resistance.py, trendlines.py

from dataclasses import dataclass, field

import pandas as pd

__all__ = ["FibonacciLevels", "compute_fibonacci"]

# Standard Fibonacci ratios for retracement and extension
_RETRACEMENT_RATIOS = {
    "0.0": 0.0,
    "0.236": 0.236,
    "0.382": 0.382,
    "0.5": 0.5,
    "0.618": 0.618,
    "0.786": 0.786,
    "1.0": 1.0,
}

_EXTENSION_RATIOS = {
    "1.0": 1.0,
    "1.272": 1.272,
    "1.618": 1.618,
    "2.0": 2.0,
    "2.618": 2.618,
}


@dataclass(frozen=True)
class FibonacciLevels:
    """
    Fibonacci retracement and extension levels based on recent swing high/low.

    The trend_direction determines how levels are calculated:
    - "up": swing_low before swing_high → retracement from high to low
    - "down": swing_high before swing_low → retracement from low to high
    """
    swing_high: float
    swing_low: float
    swing_high_time: str  # ISO timestamp
    swing_low_time: str   # ISO timestamp
    trend_direction: str  # "up" or "down"
    retracement: dict[str, float] = field(default_factory=dict)
    extension: dict[str, float] = field(default_factory=dict)


def compute_fibonacci(
    df: pd.DataFrame,
    lookback: int = 50,
) -> FibonacciLevels | None:
    """
    Compute Fibonacci retracement and extension levels from OHLCV data.

    Finds the highest high and lowest low in the last `lookback` candles,
    determines trend direction from their chronological order, then calculates
    retracement levels between those extremes and extension levels beyond.

    Args:
        df: DataFrame with [open, high, low, close], DatetimeIndex ascending.
        lookback: Number of recent candles to search for swing points.

    Returns:
        FibonacciLevels with all computed levels, or None if insufficient data.
    """
    if len(df) < 2:
        return None

    # Use only the last `lookback` candles
    window = df.tail(lookback)

    # Find swing high (highest high) and swing low (lowest low)
    swing_high_idx = window["high"].idxmax()
    swing_low_idx = window["low"].idxmin()
    swing_high = float(window.loc[swing_high_idx, "high"])
    swing_low = float(window.loc[swing_low_idx, "low"])

    # No range means no meaningful fib levels
    price_range = swing_high - swing_low
    if price_range <= 0:
        return None

    # Determine trend direction: if swing_low comes before swing_high → uptrend
    # We compare index positions (timestamps) to determine chronological order
    trend_direction = "up" if swing_low_idx < swing_high_idx else "down"

    # Calculate retracement levels
    # Uptrend: levels descend from swing_high (0.0 = high, 1.0 = low)
    # Downtrend: levels ascend from swing_low (0.0 = low, 1.0 = high)
    retracement: dict[str, float] = {}
    for key, ratio in _RETRACEMENT_RATIOS.items():
        if trend_direction == "up":
            # Price retraces down from the high
            retracement[key] = round(swing_high - price_range * ratio, 6)
        else:
            # Price retraces up from the low
            retracement[key] = round(swing_low + price_range * ratio, 6)

    # Calculate extension levels beyond the swing range
    extension: dict[str, float] = {}
    for key, ratio in _EXTENSION_RATIOS.items():
        if trend_direction == "up":
            # Extensions project above the swing high
            extension[key] = round(swing_high + price_range * (ratio - 1.0), 6)
        else:
            # Extensions project below the swing low
            extension[key] = round(swing_low - price_range * (ratio - 1.0), 6)

    return FibonacciLevels(
        swing_high=swing_high,
        swing_low=swing_low,
        swing_high_time=swing_high_idx.isoformat(),
        swing_low_time=swing_low_idx.isoformat(),
        trend_direction=trend_direction,
        retracement=retracement,
        extension=extension,
    )
