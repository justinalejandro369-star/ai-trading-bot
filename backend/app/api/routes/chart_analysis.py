# backend/app/api/routes/chart_analysis.py
# GET /api/chart-analysis/{symbol} — bundled geometric analysis (Fibonacci, trendlines, S/R, pivots).
# Single endpoint to avoid multiple round-trips for chart overlay data.
# RELEVANT FILES: analysis/fibonacci.py, analysis/trendlines.py, analysis/support_resistance.py, analysis/pivots.py

import logging
from dataclasses import asdict
from typing import Annotated, AsyncIterator

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.fibonacci import compute_fibonacci
from app.analysis.pivots import VALID_METHODS, compute_pivots
from app.analysis.support_resistance import compute_support_resistance
from app.analysis.trendlines import compute_trendlines
from app.core.database import async_session_factory

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/chart-analysis", tags=["chart-analysis"])

VALID_INTERVALS: frozenset[str] = frozenset({"1m", "5m", "15m", "1H", "4H", "1D"})

# Need enough candles for trendline lookback (100) + swing detection buffer
_MIN_CANDLES_ANALYSIS = 30


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


@router.get("/{symbol}")
async def get_chart_analysis(
    symbol: str,
    interval: Annotated[
        str,
        Query(description="Candle interval: 1m | 5m | 15m | 1H | 4H | 1D"),
    ] = "1D",
    pivot_method: Annotated[
        str,
        Query(description="Pivot method: standard | camarilla | woodie"),
    ] = "standard",
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """
    Return bundled geometric chart analysis for a symbol.

    Fetches candles once and runs all geometric analysis engines:
    - Fibonacci retracement & extension levels
    - Auto-detected trend lines (max 4)
    - Horizontal support & resistance levels (max 10)
    - Pivot points (Standard/Camarilla/Woodie)

    This avoids multiple round-trips for the chart overlay rendering.
    """
    if interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid interval '{interval}'. Must be one of: {sorted(VALID_INTERVALS)}",
        )

    if pivot_method not in VALID_METHODS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid pivot method '{pivot_method}'. Must be one of: {sorted(VALID_METHODS)}",
        )

    # Fetch enough candles for trendline lookback (100) + extra buffer
    result = await session.execute(
        text("""
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = :symbol AND interval = :interval
            ORDER BY timestamp ASC
            LIMIT :limit
        """),
        {"symbol": symbol.upper(), "interval": interval, "limit": 200},
    )
    rows = result.fetchall()

    if len(rows) < _MIN_CANDLES_ANALYSIS:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Insufficient data for chart analysis on {symbol}/{interval}: "
                f"need {_MIN_CANDLES_ANALYSIS} candles, have {len(rows)}"
            ),
        )

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")

    # Run all geometric analysis engines on the same DataFrame
    fibonacci = compute_fibonacci(df, lookback=50)
    trendlines = compute_trendlines(df, min_touches=3, lookback=100)
    sr_levels = compute_support_resistance(df, tolerance_pct=0.015, min_touches=2)

    # Pivot points use the previous period's OHLC (second-to-last candle)
    # This gives users levels based on the most recently completed period
    pivots = None
    if len(df) >= 2:
        prev = df.iloc[-2]
        pivots = compute_pivots(
            high=float(prev["high"]),
            low=float(prev["low"]),
            close=float(prev["close"]),
            open_=float(prev["open"]),
            method=pivot_method,
        )

    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "fibonacci": asdict(fibonacci) if fibonacci else None,
        "trendlines": asdict(trendlines),
        "support_resistance": asdict(sr_levels),
        "pivots": asdict(pivots) if pivots else None,
    }
