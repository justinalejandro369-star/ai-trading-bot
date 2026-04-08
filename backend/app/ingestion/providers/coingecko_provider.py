"""
CoinGeckoProvider: crypto OHLCV data via CoinGecko API.

Design constraints (from RESEARCH.md Pattern 3, Pitfall 1, Pitfall 5):
- Free Demo plan: 30 req/min, 10,000 calls/month.
- 5 coins * 48 calls/day * 30 days = 7,200 calls/month — within cap.
- Inter-coin delay: asyncio.sleep(2) between coins keeps rate under 2.5 req/min (safe).
- TTL cache: 120 seconds prevents redundant API calls during rapid consecutive requests.
- CoinGecko OHLC endpoint does NOT return volume; all candles have volume=0.0 (known limitation).
- Anti-pattern to avoid: do NOT try to build fine-grained intraday candles from CoinGecko.
  The API auto-selects granularity based on the 'days' parameter; use CCXT for intraday.

Security: API key sourced exclusively from COINGECKO_API_KEY env var (never hardcoded).
"""
import asyncio
import logging
import random
from datetime import datetime

from pycoingecko import CoinGeckoAPI

from app.ingestion.base_provider import OHLCVCandle, OHLCVProvider
from app.ingestion.cache import TTLCache
from app.ingestion.normalizer import normalize_coingecko
from app.core.config import settings

__all__ = ["CoinGeckoProvider", "COINGECKO_COINS"]

logger = logging.getLogger(__name__)

# Default coins to ingest in the scheduled batch job.
# Covers the top-5 crypto assets by market cap; sufficient for MVP watchlist.
COINGECKO_COINS: list[str] = [
    "bitcoin",
    "ethereum",
    "solana",
    "binancecoin",
    "ripple",
]

_CACHE_TTL_SECONDS = 120  # 2-minute TTL prevents burning the monthly call budget
_INTER_COIN_DELAY_SECONDS = 2  # asyncio.sleep between coins → max 2.5 req/min
_MAX_RETRIES = 3
_OHLCV_DAYS = 30  # CoinGecko returns 4H candles for 3-30 day window


class CoinGeckoProvider(OHLCVProvider):
    """
    Fetches crypto OHLCV data from CoinGecko.

    - TTL cache: 120-second cache prevents duplicate API calls.
    - Exponential backoff: retries on 429 / rate limit errors.
    - Inter-coin delay: enforced in ingest_all_coins() to stay under free tier limits.
    """

    def __init__(self) -> None:
        self.cg = CoinGeckoAPI(api_key=settings.COINGECKO_API_KEY)
        self._cache = TTLCache()

    async def fetch_historical(
        self,
        symbol: str,
        interval: str,
        start: datetime | None,
        end: datetime | None,
    ) -> list[OHLCVCandle]:
        """
        Fetch OHLCV data for a CoinGecko coin ID.

        Note: `interval` parameter is ignored — CoinGecko auto-selects granularity
        based on the number of days. For a 30-day window, the returned candles are
        4-hour intervals (auto-selected by CoinGecko). The normalizer sets interval="4H".

        Args:
            symbol: CoinGecko coin ID (e.g., "bitcoin", "ethereum")
            interval: Ignored (kept for interface compatibility)
            start: Ignored (kept for interface compatibility)
            end: Ignored (kept for interface compatibility)

        Returns:
            List of OHLCVCandle instances with market=="crypto", interval=="4H",
            and volume==0.0 (CoinGecko OHLC endpoint limitation).
        """
        cache_key = f"cg:{symbol}:ohlc"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for CoinGecko %s", symbol)
            return cached

        raw = await self._fetch_with_backoff(symbol)
        candles = normalize_coingecko(raw, symbol)

        self._cache.set(cache_key, candles, ttl_seconds=_CACHE_TTL_SECONDS)
        return candles

    async def fetch_latest(
        self,
        symbol: str,
        interval: str,
    ) -> list[OHLCVCandle]:
        """
        Fetch the most recent candles for a CoinGecko coin.

        Delegates to fetch_historical (same endpoint) and returns the last 50 candles.

        Args:
            symbol: CoinGecko coin ID (e.g., "bitcoin")
            interval: Ignored (CoinGecko auto-selects granularity)

        Returns:
            List of the most recent 50 OHLCVCandle instances.
        """
        candles = await self.fetch_historical(symbol, interval, None, None)
        return candles[-50:]

    async def _fetch_with_backoff(self, coin_id: str) -> list[list]:
        """
        Call CoinGecko OHLC endpoint with exponential backoff on rate limit errors.

        Returns raw OHLC list [[timestamp_ms, open, high, low, close], ...].
        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                # CoinGeckoAPI.get_coin_ohlc_by_id is synchronous — run in executor
                # for async compatibility, but for MVP simplicity call directly
                # (CoinGecko calls are infrequent and short-lived).
                raw = self.cg.get_coin_ohlc_by_id(
                    id=coin_id,
                    vs_currency="usd",
                    days=_OHLCV_DAYS,
                )
                logger.debug("CoinGecko returned %d rows for %s", len(raw), coin_id)
                return raw
            except Exception as exc:
                last_exc = exc
                exc_str = str(exc).lower()
                if "429" in exc_str or "rate limit" in exc_str:
                    wait = (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        "CoinGecko 429 for %s (attempt %d/%d), retrying in %.2fs",
                        coin_id,
                        attempt + 1,
                        _MAX_RETRIES,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

        raise last_exc  # type: ignore[misc]


async def ingest_all_coins(session: object, cg_provider: CoinGeckoProvider) -> None:
    """
    Batch ingest OHLCV data for all coins in COINGECKO_COINS.

    Enforces an inter-coin delay (asyncio.sleep(2)) to stay under the CoinGecko
    free-tier rate limit of 30 req/min. Upserts candles via ON CONFLICT DO NOTHING
    to ensure idempotency.

    Args:
        session: SQLAlchemy async session (used for DB upserts)
        cg_provider: An initialized CoinGeckoProvider instance
    """
    from sqlalchemy import text

    for i, coin_id in enumerate(COINGECKO_COINS):
        candles = await cg_provider.fetch_latest(coin_id, "4H")
        logger.info("Ingested %d candles for %s", len(candles), coin_id)

        for candle in candles:
            await session.execute(
                text(
                    """
                    INSERT INTO market_data (symbol, market, interval, timestamp, open, high, low, close, volume)
                    VALUES (:symbol, :market, :interval, :timestamp, :open, :high, :low, :close, :volume)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "symbol": candle.symbol,
                    "market": candle.market,
                    "interval": candle.interval,
                    "timestamp": candle.timestamp,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                },
            )

        # Inter-coin delay: prevents exceeding 2.5 req/min (well under 30/min limit)
        if i < len(COINGECKO_COINS) - 1:
            await asyncio.sleep(_INTER_COIN_DELAY_SECONDS)

    await session.commit()
    logger.info("ingest_all_coins: committed %d coins", len(COINGECKO_COINS))
