"""
Indicators REST endpoint.

GET /api/indicators/{symbol}?interval={interval}

Fetches the most recent N candles from the DB, computes indicators on the fly,
and returns the IndicatorSet as JSON.

Design decision: This endpoint computes indicators on-demand (not pre-cached).
It is intended for single-asset lookups from the dashboard — not for bulk access.
Bulk pre-computed results come from the scanner (see /api/signals).

Security:
  - symbol: parameterized SQL query — no injection risk
  - interval: validated against VALID_INTERVALS whitelist — 422 on violation
"""
import logging
from typing import Annotated, AsyncIterator

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.analysis.indicators import MIN_CANDLES, compute_indicators

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/indicators", tags=["indicators"])

VALID_INTERVALS: frozenset[str] = frozenset({"1m", "5m", "15m", "1H", "4H", "1D"})


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


@router.get("/{symbol}")
async def get_indicators(
    symbol: str,
    interval: Annotated[
        str,
        Query(description="Candle interval: 1m | 5m | 15m | 1H | 4H | 1D"),
    ] = "1D",
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """
    Return computed technical indicators for a symbol and interval.

    Fetches up to MIN_CANDLES+20 rows from market_data and runs compute_indicators().
    Returns 404 if insufficient data exists for indicator computation.
    """
    if interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid interval '{interval}'. Must be one of: {sorted(VALID_INTERVALS)}",
        )

    result = await session.execute(
        text("""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = :symbol AND interval = :interval
            ORDER BY timestamp ASC
            LIMIT :limit
        """),
        {"symbol": symbol.upper(), "interval": interval, "limit": MIN_CANDLES + 20},
    )
    rows = result.fetchall()

    if len(rows) < MIN_CANDLES:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Insufficient data for {symbol}/{interval}: "
                f"need {MIN_CANDLES} candles, have {len(rows)}"
            ),
        )

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")

    ind = compute_indicators(df, symbol=symbol.upper(), interval=interval)
    if ind is None:
        raise HTTPException(status_code=404, detail="Indicator computation returned None")

    return {
        "symbol": ind.symbol,
        "interval": ind.interval,
        "rsi_14": ind.rsi_14,
        "macd_val": ind.macd_val,
        "macd_signal": ind.macd_signal,
        "macd_hist": ind.macd_hist,
        "bb_upper": ind.bb_upper,
        "bb_lower": ind.bb_lower,
        "bb_pct": ind.bb_pct,
        "adx_14": ind.adx_14,
        "atr_14": ind.atr_14,
        "ema_50": ind.ema_50,
        "ema_200": ind.ema_200,
        "vol_sma_20": ind.vol_sma_20,
        "close": ind.close,
        "volume": ind.volume,
    }
