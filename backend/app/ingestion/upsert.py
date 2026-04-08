"""
Upsert helper for OHLCV candles.

Uses raw SQL with ON CONFLICT (symbol, interval, timestamp) DO NOTHING for
idempotent inserts. This ensures duplicate candle ingestion (e.g., on scheduler
restart) does not create duplicate rows in market_data.

Security note: All SQL values come from OHLCVCandle dataclass fields (typed
floats/str/datetime). No user input reaches the SQL parameters. Parameterized
via SQLAlchemy text() with named params — no injection risk.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.base_provider import OHLCVCandle

__all__ = ["upsert_candles"]

log = logging.getLogger(__name__)


async def upsert_candles(session: AsyncSession, candles: list[OHLCVCandle]) -> int:
    """
    Insert OHLCV candles into market_data using ON CONFLICT DO NOTHING.

    Idempotent: inserting the same candle twice produces no duplicate rows.
    The composite primary key (symbol, interval, timestamp) determines uniqueness.

    Args:
        session: SQLAlchemy async session (caller is responsible for lifecycle)
        candles: List of OHLCVCandle instances to persist

    Returns:
        Number of candles attempted (not deduplicated — includes skipped conflicts)
    """
    if not candles:
        return 0

    for c in candles:
        await session.execute(
            text(
                """
                INSERT INTO market_data
                    (symbol, market, interval, timestamp, open, high, low, close, volume)
                VALUES
                    (:symbol, :market, :interval, :timestamp, :open, :high, :low, :close, :volume)
                ON CONFLICT (symbol, interval, timestamp) DO NOTHING
                """
            ),
            {
                "symbol": c.symbol,
                "market": c.market,
                "interval": c.interval,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            },
        )

    await session.commit()
    log.info("Upserted %d candles", len(candles))
    return len(candles)
