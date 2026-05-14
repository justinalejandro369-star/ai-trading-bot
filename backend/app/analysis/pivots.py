# backend/app/analysis/pivots.py
# Pivot point calculation engine supporting Standard, Camarilla, and Woodie methods.
# Pure function — takes previous period OHLC, returns pivot + support/resistance levels.
# RELEVANT FILES: indicators.py, support_resistance.py, fibonacci.py

from dataclasses import dataclass

__all__ = ["PivotPointSet", "compute_pivots"]

VALID_METHODS = frozenset({"standard", "camarilla", "woodie"})


@dataclass(frozen=True)
class PivotPointSet:
    """Pivot point with 3 resistance and 3 support levels."""
    method: str
    pivot: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float


def compute_pivots(
    high: float,
    low: float,
    close: float,
    open_: float,
    method: str = "standard",
) -> PivotPointSet | None:
    """
    Calculate pivot points from previous period's OHLC values.

    Three methods implemented:
    - Standard (Floor): Classic pivot formula used by most traders
    - Camarilla: Tighter levels designed for intraday mean-reversion
    - Woodie: Gives more weight to the close price

    Args:
        high: Previous period's high.
        low: Previous period's low.
        close: Previous period's close.
        open_: Previous period's open (used by Woodie method).
        method: One of "standard", "camarilla", "woodie".

    Returns:
        PivotPointSet with pivot + R1-R3 + S1-S3, or None if invalid method.
    """
    if method not in VALID_METHODS:
        return None

    price_range = high - low

    if method == "standard":
        # Classic floor trader pivot formula
        pivot = (high + low + close) / 3.0
        r1 = 2.0 * pivot - low
        s1 = 2.0 * pivot - high
        r2 = pivot + price_range
        s2 = pivot - price_range
        r3 = high + 2.0 * (pivot - low)
        s3 = low - 2.0 * (high - pivot)

    elif method == "camarilla":
        # Camarilla: tighter levels using multipliers of the range
        pivot = (high + low + close) / 3.0
        r1 = close + price_range * 1.1 / 12.0
        r2 = close + price_range * 1.1 / 6.0
        r3 = close + price_range * 1.1 / 4.0
        s1 = close - price_range * 1.1 / 12.0
        s2 = close - price_range * 1.1 / 6.0
        s3 = close - price_range * 1.1 / 4.0

    else:  # woodie
        # Woodie: double-weights the close price
        pivot = (high + low + 2.0 * close) / 4.0
        r1 = 2.0 * pivot - low
        s1 = 2.0 * pivot - high
        r2 = pivot + price_range
        s2 = pivot - price_range
        # Woodie R3/S3 use same formula as standard
        r3 = high + 2.0 * (pivot - low)
        s3 = low - 2.0 * (high - pivot)

    return PivotPointSet(
        method=method,
        pivot=round(pivot, 6),
        r1=round(r1, 6),
        r2=round(r2, 6),
        r3=round(r3, 6),
        s1=round(s1, 6),
        s2=round(s2, 6),
        s3=round(s3, 6),
    )
