"""
Tests for ForexProvider (app.ingestion.providers.forex_provider).

All tests mock httpx — no real Alpha Vantage API calls.
Tests verify:
  1. Graceful fallback when API key not set (returns [], logs warning)
  2. Successful fetch and normalization of FX_DAILY response
  3. Handles rate-limit "Information" key gracefully
  4. Handles malformed candle rows gracefully (skips, continues)
  5. Returns candles sorted oldest-first
  6. fetch_historical filters by date range
"""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ingestion.providers.forex_provider import (
    FOREX_INTERVAL,
    FOREX_SYMBOLS,
    ForexProvider,
)


# Sample Alpha Vantage FX_DAILY response
_SAMPLE_FX_RESPONSE = {
    "Meta Data": {
        "1. Information": "Forex Daily Prices (open, high, low, close)",
        "2. From Symbol": "EUR",
        "3. To Symbol": "USD",
    },
    "Time Series FX (Daily)": {
        "2024-01-15": {
            "1. open": "1.0952",
            "2. high": "1.0968",
            "3. low": "1.0921",
            "4. close": "1.0941",
        },
        "2024-01-14": {
            "1. open": "1.0901",
            "2. high": "1.0955",
            "3. low": "1.0888",
            "4. close": "1.0950",
        },
        "2024-01-13": {
            "1. open": "1.0855",
            "2. high": "1.0910",
            "3. low": "1.0840",
            "4. close": "1.0898",
        },
    },
}


def _make_mock_response(data: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return mock_resp


def test_forex_symbols_list():
    """FOREX_SYMBOLS contains expected major pairs."""
    assert "EUR/USD" in FOREX_SYMBOLS
    assert "GBP/USD" in FOREX_SYMBOLS
    assert "USD/JPY" in FOREX_SYMBOLS
    assert "AUD/USD" in FOREX_SYMBOLS


def test_forex_interval_is_daily():
    """FOREX_INTERVAL is always 1D."""
    assert FOREX_INTERVAL == "1D"


@pytest.mark.asyncio
async def test_fetch_latest_no_api_key_returns_empty():
    """ForexProvider with empty api_key returns [] gracefully."""
    provider = ForexProvider(api_key="")
    result = await provider.fetch_latest("EUR/USD", "1D")
    assert result == []


@pytest.mark.asyncio
async def test_fetch_historical_no_api_key_returns_empty():
    """ForexProvider with empty api_key returns [] for historical too."""
    provider = ForexProvider(api_key="")
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 31, tzinfo=timezone.utc)
    result = await provider.fetch_historical("EUR/USD", "1D", start, end)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_latest_normalizes_candles():
    """fetch_latest parses FX_DAILY response and returns OHLCVCandle instances."""
    provider = ForexProvider(api_key="fake-key")
    mock_resp = _make_mock_response(_SAMPLE_FX_RESPONSE)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.ingestion.providers.forex_provider.httpx.AsyncClient", return_value=mock_client):
        candles = await provider.fetch_latest("EUR/USD", "1D")

    assert len(candles) == 3
    # Sorted oldest-first
    assert candles[0].timestamp < candles[1].timestamp < candles[2].timestamp
    # First candle = 2024-01-13 (oldest)
    assert candles[0].timestamp.date().isoformat() == "2024-01-13"
    assert candles[0].symbol == "EUR/USD"
    assert candles[0].market == "forex"
    assert candles[0].interval == "1D"
    assert candles[0].open == pytest.approx(1.0855)
    assert candles[0].high == pytest.approx(1.0910)
    assert candles[0].low == pytest.approx(1.0840)
    assert candles[0].close == pytest.approx(1.0898)
    assert candles[0].volume == 0.0  # FX has no volume


@pytest.mark.asyncio
async def test_fetch_historical_filters_by_date():
    """fetch_historical returns only candles within the given range."""
    provider = ForexProvider(api_key="fake-key")
    mock_resp = _make_mock_response(_SAMPLE_FX_RESPONSE)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    start = datetime(2024, 1, 14, tzinfo=timezone.utc)
    end = datetime(2024, 1, 15, tzinfo=timezone.utc)

    with patch("app.ingestion.providers.forex_provider.httpx.AsyncClient", return_value=mock_client):
        candles = await provider.fetch_historical("EUR/USD", "1D", start, end)

    # Only Jan 14 and Jan 15 should be returned
    assert len(candles) == 2
    dates = [c.timestamp.date().isoformat() for c in candles]
    assert "2024-01-14" in dates
    assert "2024-01-15" in dates
    assert "2024-01-13" not in dates


@pytest.mark.asyncio
async def test_fetch_rate_limited_returns_empty():
    """Alpha Vantage 'Information' key (rate limit) results in empty list."""
    provider = ForexProvider(api_key="fake-key")
    rate_limit_response = {
        "Information": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."
    }
    mock_resp = _make_mock_response(rate_limit_response)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.ingestion.providers.forex_provider.httpx.AsyncClient", return_value=mock_client):
        candles = await provider.fetch_latest("EUR/USD", "1D")

    assert candles == []


@pytest.mark.asyncio
async def test_fetch_http_error_returns_empty():
    """HTTP request failure returns empty list without raising."""
    provider = ForexProvider(api_key="fake-key")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

    with patch("app.ingestion.providers.forex_provider.httpx.AsyncClient", return_value=mock_client):
        candles = await provider.fetch_latest("EUR/USD", "1D")

    assert candles == []


@pytest.mark.asyncio
async def test_fetch_invalid_symbol_format_returns_empty():
    """Symbol without '/' separator returns [] with an error log."""
    provider = ForexProvider(api_key="fake-key")
    candles = await provider.fetch_latest("EURUSD", "1D")  # missing slash
    assert candles == []


@pytest.mark.asyncio
async def test_fetch_skips_malformed_rows():
    """Candle rows missing required keys are skipped; valid rows still returned."""
    provider = ForexProvider(api_key="fake-key")
    response_with_bad_row = {
        "Time Series FX (Daily)": {
            "2024-01-15": {
                "1. open": "1.0952",
                "2. high": "1.0968",
                "3. low": "1.0921",
                "4. close": "1.0941",
            },
            "2024-01-14": {
                # Missing required keys — should be skipped
                "bad_key": "not a candle",
            },
        }
    }
    mock_resp = _make_mock_response(response_with_bad_row)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.ingestion.providers.forex_provider.httpx.AsyncClient", return_value=mock_client):
        candles = await provider.fetch_latest("EUR/USD", "1D")

    assert len(candles) == 1
    assert candles[0].timestamp.date().isoformat() == "2024-01-15"
