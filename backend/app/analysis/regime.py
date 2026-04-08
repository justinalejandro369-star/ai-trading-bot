"""
Market regime classifier.

Pure function: classifies current market conditions from ADX and ATR values.
No DB access — testable without any infrastructure.

Three regimes:
  volatile  — strong trend (ADX > 25) with elevated volatility (ATR > 1.2x SMA)
  trending  — strong trend (ADX > 25) with normal volatility
  ranging   — no clear trend (ADX <= 25) or insufficient data
"""
from typing import Literal

from app.analysis.indicators import IndicatorSet

__all__ = ["RegimeType", "detect_regime"]

RegimeType = Literal["trending", "ranging", "volatile"]


def detect_regime(ind: IndicatorSet, atr_sma_20: float | None = None) -> RegimeType:
    """
    Classify the current market regime from ADX and relative ATR.

    Args:
        ind: Computed indicator values for the asset.
        atr_sma_20: 20-period SMA of ATR values (computed separately by scanner).
                    If None, the volatile sub-classification is skipped.

    Returns:
        "volatile"  — ADX > 25 and ATR > 1.2x its 20-period SMA
        "trending"  — ADX > 25 but ATR within normal range (or atr_sma_20 unavailable)
        "ranging"   — ADX <= 25 or adx_14 is None (no clear directional trend)
    """
    if ind.adx_14 is None:
        return "ranging"

    if ind.adx_14 > 25:
        if (
            atr_sma_20 is not None
            and ind.atr_14 is not None
            and ind.atr_14 > atr_sma_20 * 1.2
        ):
            return "volatile"
        return "trending"

    return "ranging"
