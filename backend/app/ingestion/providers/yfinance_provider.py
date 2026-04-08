"""
YfinanceProvider: batch historical OHLCV data for US stocks via yfinance.

Design constraints:
- yfinance is an unofficial scraper — it breaks without warning and returns 429 errors
  under load. Use ONLY for batch historical data, never for real-time polling.
- Per-symbol TTL cache (60 seconds) prevents hammering the API on repeated calls.
- Exponential backoff with jitter on 429 responses: wait = 2^attempt + random(0,1),
  max 3 retries.

Rate-limit guidance (from RESEARCH.md Pitfall 2):
- Never call yfinance faster than once per symbol per minute.
- For real-time prices, use FinnhubProvider WebSocket instead.
"""
import asyncio
import logging
import random
from datetime import datetime

import yfinance as yf

from app.ingestion.base_provider import OHLCVCandle, OHLCVProvider
from app.ingestion.cache import TTLCache
from app.ingestion.normalizer import normalize_yfinance

__all__ = ["YfinanceProvider", "YFINANCE_MAX_HISTORY"]

logger = logging.getLogger(__name__)

# Maps interval string to the maximum history period supported by yfinance.
# Requests beyond this window silently return an empty DataFrame.
# Source: yfinance documentation + RESEARCH.md Pitfall 2.
YFINANCE_MAX_HISTORY: dict[str, str] = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "1h": "60d",
    "4h": "60d",
    "1d": "2y",
    "1wk": "10y",
}

_CACHE_TTL_SECONDS = 60  # Never call yfinance faster than once per symbol per minute
_MAX_RETRIES = 3
_LATEST_CANDLE_LIMIT = 200


class YfinanceProvider(OHLCVProvider):
    """
    Fetches US stock OHLCV data from yfinance.

    - Uses a TTL cache to prevent duplicate API calls within the same minute.
    - Applies exponential backoff with jitter on HTTP 429 responses.
    - Validates requested intervals against YFINANCE_MAX_HISTORY.
    """

    def __init__(self) -> None:
        self._cache = TTLCache()

    async def fetch_historical(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVCandle]:
        """
        Fetch historical OHLCV candles for a symbol within the given date range.

        Args:
            symbol: Stock ticker (e.g., "AAPL")
            interval: Candle size — must be a key in YFINANCE_MAX_HISTORY
            start: Start datetime (timezone-aware recommended)
            end: End datetime (timezone-aware recommended)

        Returns:
            List of OHLCVCandle instances with market == "stock"

        Raises:
            ValueError: If interval is not in YFINANCE_MAX_HISTORY
        """
        if interval not in YFINANCE_MAX_HISTORY:
            raise ValueError(
                f"Unsupported yfinance interval: '{interval}'. "
                f"Supported: {list(YFINANCE_MAX_HISTORY.keys())}"
            )

        cache_key = f"{symbol}:{interval}:hist"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for %s %s historical", symbol, interval)
            return cached

        period = YFINANCE_MAX_HISTORY[interval]
        candles = await self._fetch_with_backoff(symbol, interval, period)

        self._cache.set(cache_key, candles, ttl_seconds=_CACHE_TTL_SECONDS)
        return candles

    async def fetch_latest(
        self,
        symbol: str,
        interval: str,
    ) -> list[OHLCVCandle]:
        """
        Fetch the most recent candles for a symbol.

        Uses the maximum allowed period for the interval, then returns the
        last _LATEST_CANDLE_LIMIT candles.

        Args:
            symbol: Stock ticker (e.g., "AAPL")
            interval: Candle size — must be a key in YFINANCE_MAX_HISTORY

        Returns:
            List of the most recent OHLCVCandle instances (up to 200)

        Raises:
            ValueError: If interval is not in YFINANCE_MAX_HISTORY
        """
        if interval not in YFINANCE_MAX_HISTORY:
            raise ValueError(
                f"Unsupported yfinance interval: '{interval}'. "
                f"Supported: {list(YFINANCE_MAX_HISTORY.keys())}"
            )

        cache_key = f"{symbol}:{interval}:latest"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for %s %s latest", symbol, interval)
            return cached

        period = YFINANCE_MAX_HISTORY[interval]
        candles = await self._fetch_with_backoff(symbol, interval, period)
        recent = candles[-_LATEST_CANDLE_LIMIT:]

        self._cache.set(cache_key, recent, ttl_seconds=_CACHE_TTL_SECONDS)
        return recent

    async def _fetch_with_backoff(
        self,
        symbol: str,
        interval: str,
        period: str,
    ) -> list[OHLCVCandle]:
        """
        Call yf.Ticker().history() with exponential backoff on 429 errors.

        Retries up to _MAX_RETRIES times. After exhausting retries, re-raises
        the last exception.
        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                )
                candles = normalize_yfinance(df, symbol, interval)
                logger.debug(
                    "Fetched %d candles for %s %s (attempt %d)",
                    len(candles),
                    symbol,
                    interval,
                    attempt + 1,
                )
                return candles
            except Exception as exc:
                last_exc = exc
                exc_str = str(exc).lower()
                if "429" in exc_str or "too many requests" in exc_str:
                    wait = (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        "yfinance 429 for %s (attempt %d/%d), retrying in %.2fs",
                        symbol,
                        attempt + 1,
                        _MAX_RETRIES,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    # Non-rate-limit error — re-raise immediately
                    raise

        raise last_exc  # type: ignore[misc]
