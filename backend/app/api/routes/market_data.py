"""
Market data REST endpoint.

GET /api/market-data/{symbol}?interval={interval}&limit={N}

Returns up to N OHLCV candles for the given symbol and interval, ordered by
timestamp DESC (most recent first). If no data exists, returns an empty array.

Security:
- symbol: passed to SQLAlchemy .where() as a parameterized value — no injection risk
- interval: validated against VALID_INTERVALS whitelist before any DB call
- limit: enforced ge=1, le=1000 by FastAPI Query annotation (422 on violation)
"""
import logging
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.market_data import MarketData

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/market-data", tags=["market-data"])

#: Whitelist of valid interval values. Any other value returns 422.
VALID_INTERVALS: frozenset[str] = frozenset({"1m", "5m", "15m", "1H", "4H", "1D"})


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency: yields a SQLAlchemy async session.

    This async generator form is required by FastAPI's dependency injection system.
    The @asynccontextmanager version in database.py is for non-FastAPI callers
    (scheduler jobs, etc.).
    """
    async with async_session_factory() as session:
        yield session


@router.get("/{symbol}")
async def get_candles(
    symbol: str,
    interval: Annotated[
        str,
        Query(description="Candle interval: 1m | 5m | 15m | 1H | 4H | 1D"),
    ],
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> list[dict]:
    """
    Return OHLCV candles for a symbol and interval.

    Args:
        symbol: Ticker or asset identifier (case-insensitive — uppercased internally)
        interval: Candle interval; must be one of VALID_INTERVALS
        limit: Maximum number of candles to return (1–1000, default 200)
        session: Injected async DB session

    Returns:
        JSON array of candle objects ordered by timestamp DESC.
        Returns [] if no data found (never 404).

    Raises:
        HTTPException 422: If interval is not in VALID_INTERVALS
    """
    if interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid interval '{interval}'. "
                f"Must be one of: {sorted(VALID_INTERVALS)}"
            ),
        )

    result = await session.execute(
        select(MarketData)
        .where(
            and_(
                MarketData.symbol == symbol.upper(),
                MarketData.interval == interval,
            )
        )
        .order_by(MarketData.timestamp.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    log.debug(
        "GET /market-data/%s?interval=%s&limit=%d → %d rows",
        symbol,
        interval,
        limit,
        len(rows),
    )

    return [
        {
            "symbol": r.symbol,
            "market": r.market,
            "interval": r.interval,
            "timestamp": r.timestamp.isoformat(),
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
        }
        for r in rows
    ]
