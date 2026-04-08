"""
CCXTProvider: intraday crypto OHLCV via Binance public API (no auth required).

Design constraints:
- Uses ccxt.binance with enableRateLimit=True — CCXT auto-throttles to stay within
  Binance rate limits. No additional rate limiting logic needed for single-user MVP.
- All timestamps are returned as UTC-aware datetime objects.
- Interval naming: app convention uses "1H", "4H", "1D"; CCXT/Binance uses "1h", "4h", "1d".
  CCXT_INTERVAL_MAP translates between conventions before every API call.
- Symbol format uses "/" separator: "BTC/USDT" NOT "BTCUSDT" (CCXT convention).

Public API: no API key needed. Binance public endpoints have generous rate limits.
"""
import logging
from datetime import datetime, timezone

import ccxt

from app.ingestion.base_provider import OHLCVCandle, OHLCVProvider

__all__ = ["CCXTProvider", "CCXT_INTERVAL_MAP"]

logger = logging.getLogger(__name__)

# Maps app-convention interval names to CCXT/Binance timeframe strings.
# App uses uppercase H/D (e.g., "1H", "4H", "1D"); CCXT uses lowercase (e.g., "1h").
CCXT_INTERVAL_MAP: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1H": "1h",
    "4H": "4h",
    "1D": "1d",
    # Also accept lowercase input for convenience
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

_HISTORICAL_LIMIT = 500
_LATEST_LIMIT = 200


class CCXTProvider(OHLCVProvider):
    """
    Fetches crypto OHLCV data from Binance via CCXT (public endpoints, no API key).

    - enableRateLimit=True: CCXT auto-throttles API calls to respect Binance limits.
    - Translates interval names from app convention to CCXT convention.
    - Returns timezone-aware UTC timestamps for all candles.
    """

    def __init__(self) -> None:
        # enableRateLimit=True tells CCXT to automatically sleep between requests
        # to stay within Binance's rate limits. Essential for single-process use.
        self.exchange = ccxt.binance({"enableRateLimit": True})

    def _ms_to_candle(
        self,
        row: list,
        symbol: str,
        interval: str,
    ) -> OHLCVCandle:
        """
        Convert a CCXT OHLCV row to an OHLCVCandle.

        CCXT format: [timestamp_ms, open, high, low, close, volume]

        Args:
            row: 6-element list from ccxt.exchange.fetch_ohlcv()
            symbol: Crypto symbol (e.g., "BTC/USDT")
            interval: App-convention interval string (e.g., "1H", "4H")

        Returns:
            OHLCVCandle with market=="crypto" and UTC-aware timestamp
        """
        ts_ms, open_, high, low, close, volume = row
        timestamp = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        return OHLCVCandle(
            symbol=symbol,
            market="crypto",
            interval=interval,
            timestamp=timestamp,
            open=float(open_),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=float(volume),
        )

    def _translate_interval(self, interval: str) -> str:
        """
        Translate app-convention interval to CCXT timeframe string.

        Raises:
            ValueError: If interval is not in CCXT_INTERVAL_MAP
        """
        if interval not in CCXT_INTERVAL_MAP:
            raise ValueError(
                f"Unsupported CCXT interval: '{interval}'. "
                f"Supported: {list(CCXT_INTERVAL_MAP.keys())}"
            )
        return CCXT_INTERVAL_MAP[interval]

    async def fetch_historical(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVCandle]:
        """
        Fetch historical OHLCV candles from Binance via CCXT.

        Args:
            symbol: Crypto pair in CCXT format (e.g., "BTC/USDT")
            interval: App-convention interval (e.g., "1H", "4H", "1D")
            start: Start datetime (converted to milliseconds for CCXT)
            end: End datetime (unused — CCXT limit param controls window size)

        Returns:
            List of OHLCVCandle instances with market=="crypto"
        """
        timeframe = self._translate_interval(interval)
        start_ms = int(start.timestamp() * 1000) if start else None

        rows = self.exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            since=start_ms,
            limit=_HISTORICAL_LIMIT,
        )
        candles = [self._ms_to_candle(row, symbol, interval) for row in rows]
        logger.debug(
            "CCXT Binance: fetched %d candles for %s %s",
            len(candles),
            symbol,
            interval,
        )
        return candles

    async def fetch_latest(
        self,
        symbol: str,
        interval: str,
    ) -> list[OHLCVCandle]:
        """
        Fetch the most recent candles from Binance via CCXT.

        Args:
            symbol: Crypto pair in CCXT format (e.g., "BTC/USDT")
            interval: App-convention interval (e.g., "1H", "4H", "1D")

        Returns:
            List of the most recent 200 OHLCVCandle instances
        """
        timeframe = self._translate_interval(interval)

        rows = self.exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=_LATEST_LIMIT,
        )
        candles = [self._ms_to_candle(row, symbol, interval) for row in rows]
        logger.debug(
            "CCXT Binance: fetched %d latest candles for %s %s",
            len(candles),
            symbol,
            interval,
        )
        return candles
