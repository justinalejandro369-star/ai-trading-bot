"""
Multi-timeframe signal agreement analysis.

Queries the signals table for the same symbol across 1H, 4H, 1D intervals
and returns an agreement dict showing whether signals align across timeframes.

Design:
  - Reads from signals table (pre-computed by scanner)
  - Returns a simple dict — no computation here
  - agreement=True when all available intervals have the same direction
  - Missing intervals (no scan data yet) are excluded from agreement check

Usage:
  from app.analysis.multiframe import compute_multiframe_agreement
  result = await compute_multiframe_agreement("AAPL", session)
  # {"1H": "BUY", "4H": "HOLD", "1D": "BUY", "agreement": false}
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import TradingSignal

__all__ = ["compute_multiframe_agreement", "MULTIFRAME_INTERVALS"]

log = logging.getLogger(__name__)

MULTIFRAME_INTERVALS = ["1H", "4H", "1D"]


async def compute_multiframe_agreement(
    symbol: str,
    session: AsyncSession,
) -> dict:
    """
    Check signal direction for a symbol across 1H, 4H, 1D timeframes.

    Queries the signals table for existing rows matching symbol + interval.
    Returns a dict with one key per found interval, plus an "agreement" boolean.

    agreement=True when all *found* intervals have the same direction.
    If only one interval exists, agreement=True (trivially aligned).
    If no intervals exist, returns {"agreement": False}.

    Args:
        symbol: Asset symbol (e.g. "AAPL", "BTC/USDT")
        session: Active SQLAlchemy async session

    Returns:
        Dict like {"1H": "BUY", "4H": "HOLD", "1D": "BUY", "agreement": false}
    """
    try:
        result = await session.execute(
            select(TradingSignal.interval, TradingSignal.direction).where(
                TradingSignal.symbol == symbol,
                TradingSignal.interval.in_(MULTIFRAME_INTERVALS),
            )
        )
        rows = result.fetchall()
    except Exception as exc:
        log.warning("compute_multiframe_agreement: DB error for %s: %s", symbol, exc)
        return {"agreement": False}

    if not rows:
        return {"agreement": False}

    frame_data: dict = {}
    for interval, direction in rows:
        frame_data[interval] = direction

    # agreement = all found intervals have the same direction
    directions = list(frame_data.values())
    agreement = len(set(directions)) == 1 if directions else False

    return {**frame_data, "agreement": agreement}
