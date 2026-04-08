"""
OHLCV data contracts: canonical candle dataclass and provider abstract base class.

Any code importing OHLCVProvider can define a new data source without touching
any other module. This is the immutable interface contract for all data providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

__all__ = ["OHLCVCandle", "OHLCVProvider"]


@dataclass(frozen=True)
class OHLCVCandle:
    """
    Canonical OHLCV candle record.

    All data providers must normalize their source format into this structure.
    The frozen flag ensures candles are immutable once constructed — they represent
    historical facts that should not change.
    """
    symbol: str
    market: str       # "stock" | "crypto"
    interval: str     # "1m" | "5m" | "15m" | "1H" | "4H" | "1D"
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCVProvider(ABC):
    """
    Abstract base class for all OHLCV data providers.

    Concrete providers (yfinance, CoinGecko, Finnhub, etc.) implement this interface.
    The scheduler and ingestion pipeline call only the interface — never provider-specific code.
    """

    @abstractmethod
    async def fetch_historical(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVCandle]:
        """
        Backfill: fetch historical candles for a given date range.

        Args:
            symbol: Ticker or asset identifier (e.g., "AAPL", "bitcoin")
            interval: Candle size (e.g., "1m", "5m", "1H", "1D")
            start: Start of the time range (timezone-aware recommended)
            end: End of the time range (timezone-aware recommended)

        Returns:
            List of OHLCVCandle instances in ascending timestamp order.
        """
        ...

    @abstractmethod
    async def fetch_latest(
        self,
        symbol: str,
        interval: str,
    ) -> list[OHLCVCandle]:
        """
        Incremental: fetch the most recent N candles since the last stored timestamp.

        Args:
            symbol: Ticker or asset identifier
            interval: Candle size

        Returns:
            List of the most recent OHLCVCandle instances.
        """
        ...
