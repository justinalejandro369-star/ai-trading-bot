"""
TDD tests for the OHLCVCandle dataclass, OHLCVProvider ABC,
and normalizer functions.

Write these BEFORE implementing (TDD RED phase).
"""
import sys
import os
from datetime import datetime, timezone

import pytest

# Add the backend directory to sys.path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def test_ohlcv_candle_is_frozen():
    """OHLCVCandle must be a frozen dataclass — attribute assignment must raise FrozenInstanceError."""
    from dataclasses import FrozenInstanceError
    from app.ingestion.base_provider import OHLCVCandle

    candle = OHLCVCandle(
        symbol="AAPL",
        market="stock",
        interval="1D",
        timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc),
        open=150.0,
        high=155.0,
        low=149.0,
        close=153.0,
        volume=1000000.0,
    )
    with pytest.raises(FrozenInstanceError):
        candle.symbol = "GOOG"  # type: ignore[misc]


def test_abstract_provider_cannot_instantiate():
    """OHLCVProvider cannot be instantiated directly (it is an ABC)."""
    from app.ingestion.base_provider import OHLCVProvider

    with pytest.raises(TypeError):
        OHLCVProvider()  # type: ignore[abstract]


def test_partial_provider_missing_method_raises():
    """
    A concrete subclass that only implements fetch_historical (but not fetch_latest)
    must raise TypeError on instantiation.
    """
    from datetime import datetime
    from app.ingestion.base_provider import OHLCVCandle, OHLCVProvider

    class IncompleteProvider(OHLCVProvider):
        async def fetch_historical(
            self,
            symbol: str,
            interval: str,
            start: datetime,
            end: datetime,
        ) -> list[OHLCVCandle]:
            return []
        # fetch_latest is intentionally not implemented

    with pytest.raises(TypeError):
        IncompleteProvider()


def test_normalize_yfinance_returns_ohlcv_candles(sample_yfinance_df):
    """
    normalize_yfinance should return a list of 3 OHLCVCandle instances
    with market == 'stock' and timezone-aware timestamps.
    """
    from app.ingestion.base_provider import OHLCVCandle
    from app.ingestion.normalizer import normalize_yfinance

    candles = normalize_yfinance(sample_yfinance_df, symbol="AAPL", interval="1D")

    assert len(candles) == 3
    for candle in candles:
        assert isinstance(candle, OHLCVCandle)
        assert candle.market == "stock"
        assert candle.symbol == "AAPL"
        assert candle.interval == "1D"
        assert candle.timestamp.tzinfo is not None


def test_normalize_coingecko_returns_ohlcv_candles(sample_coingecko_raw):
    """
    normalize_coingecko should return a list of 3 OHLCVCandle instances
    with market == 'crypto', interval == '4H', timezone-aware timestamps,
    and volume == 0.0 (CoinGecko OHLC endpoint has no volume field).
    """
    from app.ingestion.base_provider import OHLCVCandle
    from app.ingestion.normalizer import normalize_coingecko

    candles = normalize_coingecko(sample_coingecko_raw, coin_id="bitcoin")

    assert len(candles) == 3
    for candle in candles:
        assert isinstance(candle, OHLCVCandle)
        assert candle.market == "crypto"
        assert candle.interval == "4H"
        assert candle.symbol == "bitcoin"
        assert candle.timestamp.tzinfo is not None
        # Known limitation: CoinGecko OHLC endpoint returns no volume
        assert candle.volume == 0.0
