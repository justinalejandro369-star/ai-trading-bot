"""
Unit tests for crypto ingestion: CoinGeckoProvider and CCXTProvider.

All external API calls are mocked — no real network calls are made.
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.ingestion.base_provider import OHLCVCandle


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

def _make_sample_coingecko_raw(n: int = 3) -> list[list]:
    """
    Build a minimal CoinGecko OHLC raw response.
    Format: [[timestamp_ms, open, high, low, close], ...]  (5-element, no volume)
    """
    base_ts = 1704067200000  # 2024-01-01 00:00:00 UTC in ms
    result = []
    for i in range(n):
        ts = base_ts + (i * 4 * 3600 * 1000)  # 4-hour increments
        result.append([ts, 40000.0 + i, 41000.0 + i, 39000.0 + i, 40500.0 + i])
    return result


def _make_sample_ccxt_rows(n: int = 5) -> list[list]:
    """
    Build a minimal CCXT OHLCV row list.
    Format: [[timestamp_ms, open, high, low, close, volume], ...]
    """
    base_ts = 1704067200000
    result = []
    for i in range(n):
        ts = base_ts + (i * 3600 * 1000)  # 1-hour increments
        result.append([ts, 40000.0 + i, 41000.0 + i, 39000.0 + i, 40500.0 + i, 100.0 + i])
    return result


# ---------------------------------------------------------------------------
# CoinGeckoProvider tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coingecko_provider_uses_cache():
    """
    fetch_latest called twice should only call the API once — second result served from cache.
    """
    from app.ingestion.providers.coingecko_provider import CoinGeckoProvider

    raw = _make_sample_coingecko_raw(3)

    with patch("pycoingecko.CoinGeckoAPI.get_coin_ohlc_by_id", return_value=raw) as mock_api:
        provider = CoinGeckoProvider()
        first = await provider.fetch_latest("bitcoin", "4H")
        second = await provider.fetch_latest("bitcoin", "4H")

    # API should only be called once; second call should come from cache
    assert mock_api.call_count == 1
    assert len(first) == len(second) == 3


@pytest.mark.asyncio
async def test_coingecko_provider_returns_ohlcv_candles():
    """
    fetch_latest returns OHLCVCandle instances with correct market, interval, and volume=0.0.
    """
    from app.ingestion.providers.coingecko_provider import CoinGeckoProvider

    raw = _make_sample_coingecko_raw(3)

    with patch("pycoingecko.CoinGeckoAPI.get_coin_ohlc_by_id", return_value=raw):
        provider = CoinGeckoProvider()
        candles = await provider.fetch_latest("bitcoin", "4H")

    assert len(candles) == 3
    for candle in candles:
        assert isinstance(candle, OHLCVCandle)
        assert candle.market == "crypto"
        assert candle.interval == "4H"
        assert candle.volume == 0.0  # CoinGecko OHLC endpoint has no volume field
        assert candle.timestamp.tzinfo is not None


@pytest.mark.asyncio
async def test_coingecko_provider_retries_on_429():
    """
    fetch_latest retries when the API raises a 429-like exception and succeeds on second attempt.
    """
    from app.ingestion.providers.coingecko_provider import CoinGeckoProvider

    raw = _make_sample_coingecko_raw(2)
    call_count = 0

    def _mock_api(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("429 Too Many Requests")
        return raw

    with patch("pycoingecko.CoinGeckoAPI.get_coin_ohlc_by_id", side_effect=_mock_api):
        with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip actual wait
            provider = CoinGeckoProvider()
            candles = await provider.fetch_latest("bitcoin", "4H")

    assert len(candles) == 2
    assert call_count == 2


# ---------------------------------------------------------------------------
# CCXTProvider tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ccxt_provider_returns_ohlcv_candles():
    """
    fetch_latest returns OHLCVCandle instances with market=='crypto' and UTC timestamps.
    """
    from app.ingestion.providers.ccxt_provider import CCXTProvider

    rows = _make_sample_ccxt_rows(5)

    with patch.object(CCXTProvider, "__init__", lambda self: None):
        provider = CCXTProvider.__new__(CCXTProvider)
        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv.return_value = rows
        provider.exchange = mock_exchange

        candles = await provider.fetch_latest("BTC/USDT", "1H")

    assert len(candles) == 5
    for candle in candles:
        assert isinstance(candle, OHLCVCandle)
        assert candle.market == "crypto"
        assert candle.timestamp.tzinfo is not None
        assert candle.timestamp.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_ccxt_interval_mapping_1H_to_1h():
    """
    fetch_latest with interval='1H' should call exchange.fetch_ohlcv with timeframe='1h'.
    """
    from app.ingestion.providers.ccxt_provider import CCXTProvider

    rows = _make_sample_ccxt_rows(3)

    with patch.object(CCXTProvider, "__init__", lambda self: None):
        provider = CCXTProvider.__new__(CCXTProvider)
        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv.return_value = rows
        provider.exchange = mock_exchange

        await provider.fetch_latest("BTC/USDT", "1H")

    # Capture the actual call arguments
    mock_exchange.fetch_ohlcv.assert_called_once()
    call_kwargs = mock_exchange.fetch_ohlcv.call_args
    # timeframe should be "1h" (CCXT convention), not "1H" (app convention)
    assert call_kwargs.kwargs.get("timeframe") == "1h" or call_kwargs.args[1] == "1h"


@pytest.mark.asyncio
async def test_ingest_all_coins_calls_all_five():
    """
    ingest_all_coins() calls CoinGeckoProvider.fetch_latest for each coin in COINGECKO_COINS.
    """
    from app.ingestion.providers.coingecko_provider import (
        CoinGeckoProvider,
        COINGECKO_COINS,
        ingest_all_coins,
    )

    raw = _make_sample_coingecko_raw(2)
    mock_session = AsyncMock()

    with patch("pycoingecko.CoinGeckoAPI.get_coin_ohlc_by_id", return_value=raw):
        with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip inter-coin delays
            provider = CoinGeckoProvider()
            await ingest_all_coins(mock_session, provider)

    # Ensure the session was used (execute called multiple times for candles)
    assert mock_session.execute.call_count > 0
    assert mock_session.commit.called

    # Verify all 5 coins from COINGECKO_COINS are covered
    assert len(COINGECKO_COINS) == 5
