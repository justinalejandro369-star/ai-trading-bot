"""
ForexProvider: daily OHLCV data for major forex pairs via Alpha Vantage FX_DAILY.

Design constraints (from CLAUDE.md):
  - Alpha Vantage free tier: 25 req/day. Forex is scoped to daily/swing timeframes only.
  - No intraday forex — too rate-limited on free tier.
  - Graceful fallback when ALPHA_VANTAGE_API_KEY not set (returns empty list, logs warning).
  - Implements OHLCVProvider ABC to integrate with existing ingestion pipeline.

Supported symbols (forex pairs as "{FROM}/{TO}"):
  - EUR/USD, GBP/USD, USD/JPY, AUD/USD

Alpha Vantage FX_DAILY endpoint:
  GET https://www.alphavantage.co/query?function=FX_DAILY
      &from_symbol={FROM}&to_symbol={TO}&outputsize=full&apikey={KEY}

Response shape (JSON):
  {
    "Time Series FX (Daily)": {
      "2024-01-15": {
        "1. open": "1.0952",
        "2. high": "1.0968",
        "3. low": "1.0921",
        "4. close": "1.0941"
      },
      ...
    }
  }

Note: FX_DAILY has no volume field — volume is set to 0.0 (consistent with CoinGecko pattern).
"""
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.ingestion.base_provider import OHLCVCandle, OHLCVProvider

__all__ = ["ForexProvider", "FOREX_SYMBOLS", "FOREX_INTERVAL"]

log = logging.getLogger(__name__)

#: Supported forex pairs — stored as "FROM/TO" to match provider convention
FOREX_SYMBOLS: list[str] = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

#: Forex is daily only — intraday is too rate-limited on Alpha Vantage free tier
FOREX_INTERVAL: str = "1D"

_ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
_REQUEST_TIMEOUT = 30.0
_MAX_CANDLES = 365  # Limit historical depth to 1 year for MVP


class ForexProvider(OHLCVProvider):
    """
    Fetches daily OHLCV data for major forex pairs from Alpha Vantage FX_DAILY.

    - Gracefully returns [] when ALPHA_VANTAGE_API_KEY is empty (no crash).
    - Sets volume=0.0 for all candles (FX_DAILY has no volume field).
    - market="forex" on all returned candles.
    """

    def __init__(self, api_key: str = "") -> None:
        """
        Args:
            api_key: Alpha Vantage API key. If empty, all fetch methods return []
                     with a warning log (no exception).
        """
        self._api_key = api_key

    async def fetch_historical(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVCandle]:
        """
        Fetch historical daily candles for a forex pair within the given range.

        Args:
            symbol: Forex pair as "FROM/TO" (e.g., "EUR/USD")
            interval: Must be "1D" — only daily forex is supported
            start: Start datetime (inclusive)
            end: End datetime (inclusive)

        Returns:
            List of OHLCVCandle instances with market="forex", volume=0.0
            Returns [] if API key not set or request fails.
        """
        all_candles = await self._fetch_all_daily(symbol)
        # Filter by date range
        return [
            c for c in all_candles
            if start.replace(tzinfo=timezone.utc) <= c.timestamp <= end.replace(tzinfo=timezone.utc)
        ]

    async def fetch_latest(
        self,
        symbol: str,
        interval: str,
    ) -> list[OHLCVCandle]:
        """
        Fetch the most recent daily candles for a forex pair.

        Returns last _MAX_CANDLES candles (up to 1 year of daily data).

        Args:
            symbol: Forex pair as "FROM/TO" (e.g., "EUR/USD")
            interval: Must be "1D"

        Returns:
            List of recent OHLCVCandle instances with market="forex", volume=0.0
            Returns [] if API key not set or request fails.
        """
        all_candles = await self._fetch_all_daily(symbol)
        return all_candles[-_MAX_CANDLES:]

    async def _fetch_all_daily(self, symbol: str) -> list[OHLCVCandle]:
        """
        Fetch all available daily candles for a forex pair.

        Internal method — handles API key check, HTTP request, and normalization.

        Returns:
            Sorted list of OHLCVCandle (oldest first), or [] on any error.
        """
        if not self._api_key:
            log.warning(
                "ForexProvider: ALPHA_VANTAGE_API_KEY not set — skipping %s. "
                "Set ALPHA_VANTAGE_API_KEY in .env to enable forex data.",
                symbol,
            )
            return []

        # Parse "EUR/USD" → from_symbol="EUR", to_symbol="USD"
        if "/" not in symbol:
            log.error("ForexProvider: invalid symbol format '%s' — expected 'FROM/TO'", symbol)
            return []

        from_symbol, to_symbol = symbol.split("/", 1)

        params = {
            "function": "FX_DAILY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "outputsize": "full",  # full = up to 20 years of daily data
            "apikey": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.get(_ALPHA_VANTAGE_BASE, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            log.error("ForexProvider: HTTP error fetching %s: %s", symbol, exc)
            return []

        # Alpha Vantage returns an "Information" key when rate limited
        if "Information" in data:
            log.warning("ForexProvider: Alpha Vantage rate limited for %s: %s", symbol, data["Information"])
            return []

        time_series = data.get("Time Series FX (Daily)")
        if not time_series:
            log.warning("ForexProvider: no time series data for %s. Response keys: %s", symbol, list(data.keys()))
            return []

        candles: list[OHLCVCandle] = []
        for date_str, values in time_series.items():
            try:
                timestamp = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                candle = OHLCVCandle(
                    symbol=symbol,
                    market="forex",
                    interval=FOREX_INTERVAL,
                    timestamp=timestamp,
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=0.0,  # FX_DAILY has no volume field
                )
                candles.append(candle)
            except (KeyError, ValueError) as exc:
                log.warning("ForexProvider: skipping malformed row %s for %s: %s", date_str, symbol, exc)
                continue

        # Return oldest-first (Alpha Vantage returns newest-first)
        candles.sort(key=lambda c: c.timestamp)
        log.info("ForexProvider: fetched %d daily candles for %s", len(candles), symbol)
        return candles
