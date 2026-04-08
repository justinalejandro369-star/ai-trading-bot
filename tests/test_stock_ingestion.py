"""
Unit tests for stock ingestion: TTLCache, YfinanceProvider, FinnhubProvider.

All external API calls are mocked — no real network calls are made.
"""
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock

import pandas as pd
import pytest

from app.ingestion.cache import TTLCache
from app.ingestion.base_provider import OHLCVCandle


# ---------------------------------------------------------------------------
# TTLCache tests
# ---------------------------------------------------------------------------

def test_ttl_cache_miss_returns_none():
    """get() on an empty cache returns None."""
    cache = TTLCache()
    assert cache.get("nonexistent") is None


def test_ttl_cache_hit_returns_value():
    """set() then get() within TTL returns the stored value."""
    cache = TTLCache()
    cache.set("key1", "hello", ttl_seconds=60)
    result = cache.get("key1")
    assert result == "hello"


def test_ttl_cache_expired_returns_none():
    """set() with ttl=0 then a short sleep means get() returns None (entry expired)."""
    cache = TTLCache()
    cache.set("key2", "world", ttl_seconds=0)
    time.sleep(0.01)
    result = cache.get("key2")
    assert result is None


def test_ttl_cache_invalidate_removes_entry():
    """invalidate() removes a cached key so subsequent get() returns None."""
    cache = TTLCache()
    cache.set("key3", "value", ttl_seconds=60)
    cache.invalidate("key3")
    assert cache.get("key3") is None


# ---------------------------------------------------------------------------
# YfinanceProvider tests
# ---------------------------------------------------------------------------

def _make_sample_yfinance_df():
    """Build a minimal DataFrame that mirrors yfinance .history() output."""
    idx = pd.DatetimeIndex(
        [
            pd.Timestamp("2024-01-02 14:30:00", tz="UTC"),
            pd.Timestamp("2024-01-03 14:30:00", tz="UTC"),
        ]
    )
    df = pd.DataFrame(
        {
            "Open": [150.0, 152.0],
            "High": [155.0, 157.0],
            "Low": [148.0, 150.0],
            "Close": [153.0, 155.0],
            "Volume": [1_000_000, 1_200_000],
        },
        index=idx,
    )
    return df


@pytest.mark.asyncio
async def test_yfinance_provider_returns_ohlcv_candles():
    """fetch_latest returns list[OHLCVCandle] with market=='stock'."""
    from app.ingestion.providers.yfinance_provider import YfinanceProvider

    sample_df = _make_sample_yfinance_df()

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = sample_df
        mock_ticker_cls.return_value = mock_ticker

        provider = YfinanceProvider()
        candles = await provider.fetch_latest("AAPL", "1d")

    assert len(candles) > 0
    for candle in candles:
        assert isinstance(candle, OHLCVCandle)
        assert candle.market == "stock"
        assert candle.symbol == "AAPL"
        assert candle.interval == "1d"
        assert candle.timestamp.tzinfo is not None


@pytest.mark.asyncio
async def test_yfinance_invalid_interval_raises():
    """fetch_historical with unsupported interval raises ValueError."""
    from app.ingestion.providers.yfinance_provider import YfinanceProvider

    provider = YfinanceProvider()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 10, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="2d"):
        await provider.fetch_historical("AAPL", "2d", start, end)


# ---------------------------------------------------------------------------
# FinnhubProvider tests
# ---------------------------------------------------------------------------

def test_finnhub_subscribe_too_many_raises():
    """subscribe() with more than 50 symbols raises ValueError."""
    from app.ingestion.providers.finnhub_provider import FinnhubProvider

    provider = FinnhubProvider()
    symbols = ["SYM"] * 51

    with pytest.raises(ValueError):
        provider.subscribe(symbols)


@pytest.mark.asyncio
async def test_finnhub_fetch_historical_raises_not_implemented():
    """fetch_historical raises NotImplementedError (Finnhub is tick-only)."""
    from app.ingestion.providers.finnhub_provider import FinnhubProvider

    provider = FinnhubProvider()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 10, tzinfo=timezone.utc)

    with pytest.raises(NotImplementedError):
        await provider.fetch_historical("AAPL", "1m", start, end)


@pytest.mark.asyncio
async def test_finnhub_fetch_latest_raises_not_implemented():
    """fetch_latest raises NotImplementedError (Finnhub is tick-only)."""
    from app.ingestion.providers.finnhub_provider import FinnhubProvider

    provider = FinnhubProvider()

    with pytest.raises(NotImplementedError):
        await provider.fetch_latest("AAPL", "1m")
