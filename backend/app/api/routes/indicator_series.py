# backend/app/api/routes/indicator_series.py
# GET /api/indicator-series/{symbol} — full time-series indicator arrays for chart overlays.
# Unlike /api/indicators (scalar snapshot), this returns full arrays for rendering.
# RELEVANT FILES: analysis/indicator_series.py, api/routes/indicators.py, main.py

import logging
from dataclasses import asdict
from typing import Annotated, AsyncIterator

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.indicator_series import compute_indicator_series
from app.analysis.indicators import MIN_CANDLES
from app.core.database import async_session_factory

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/indicator-series", tags=["indicator-series"])

VALID_INTERVALS: frozenset[str] = frozenset({"1m", "5m", "15m", "1H", "4H", "1D"})


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


@router.get("/{symbol}")
async def get_indicator_series(
    symbol: str,
    interval: Annotated[
        str,
        Query(description="Candle interval: 1m | 5m | 15m | 1H | 4H | 1D"),
    ] = "1D",
    limit: Annotated[
        int,
        Query(description="Max candles to return (capped at 500)", ge=50, le=500),
    ] = 200,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """
    Return full time-series indicator arrays for chart overlay rendering.

    Fetches up to `limit` candles from market_data and computes all indicator
    series (EMA, Bollinger Bands, RSI, MACD, volume SMA). The arrays align 1:1
    with timestamps — leading None values represent insufficient lookback.
    """
    if interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid interval '{interval}'. Must be one of: {sorted(VALID_INTERVALS)}",
        )

    # Fetch enough extra rows so indicators have sufficient lookback.
    # MIN_CANDLES = 200; we fetch max(limit, MIN_CANDLES) + 20 buffer.
    fetch_limit = max(limit, MIN_CANDLES) + 20

    result = await session.execute(
        text("""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = :symbol AND interval = :interval
            ORDER BY timestamp ASC
            LIMIT :limit
        """),
        {"symbol": symbol.upper(), "interval": interval, "limit": fetch_limit},
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

    series_set = compute_indicator_series(df, symbol=symbol.upper(), interval=interval)
    if series_set is None:
        raise HTTPException(status_code=404, detail="Indicator series computation returned None")

    return asdict(series_set)
