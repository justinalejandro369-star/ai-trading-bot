"""
Tests for timeframes, upsert, scheduler, and market data endpoint.

Phase 01 Plan 03: Scheduler, upsert layer, and REST endpoint.
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# TDD RED phase: timeframe validation tests
# ---------------------------------------------------------------------------


def test_all_stock_intervals_are_valid_yfinance_keys():
    """All STOCK_INTERVALS must be keys in YFINANCE_MAX_HISTORY (prevents runtime errors)."""
    from app.ingestion.providers.yfinance_provider import YFINANCE_MAX_HISTORY
    from app.ingestion.scheduler import STOCK_INTERVALS

    for interval in STOCK_INTERVALS:
        assert interval in YFINANCE_MAX_HISTORY, (
            f"STOCK_INTERVAL '{interval}' is not a valid yfinance key. "
            f"Valid keys: {list(YFINANCE_MAX_HISTORY.keys())}"
        )


def test_all_ccxt_intervals_are_valid_ccxt_keys():
    """All CCXT_INTERVALS must be keys in CCXT_INTERVAL_MAP (prevents runtime errors)."""
    from app.ingestion.providers.ccxt_provider import CCXT_INTERVAL_MAP
    from app.ingestion.scheduler import CCXT_INTERVALS

    for interval in CCXT_INTERVALS:
        assert interval in CCXT_INTERVAL_MAP, (
            f"CCXT_INTERVAL '{interval}' is not a valid CCXT key. "
            f"Valid keys: {list(CCXT_INTERVAL_MAP.keys())}"
        )


# ---------------------------------------------------------------------------
# In-memory SQLite helpers for upsert tests
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS market_data (
    symbol    TEXT NOT NULL,
    market    TEXT NOT NULL,
    interval  TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open      REAL NOT NULL,
    high      REAL NOT NULL,
    low       REAL NOT NULL,
    close     REAL NOT NULL,
    volume    REAL NOT NULL,
    PRIMARY KEY (symbol, interval, timestamp)
)
"""


def _make_candle(symbol="AAPL", interval="1D", offset=0):
    """Create a test OHLCVCandle."""
    from app.ingestion.base_provider import OHLCVCandle
    return OHLCVCandle(
        symbol=symbol,
        market="stock",
        interval=interval,
        timestamp=datetime(2024, 1, offset + 1, tzinfo=timezone.utc),
        open=100.0 + offset,
        high=105.0 + offset,
        low=99.0 + offset,
        close=103.0 + offset,
        volume=1000000.0,
    )


async def _make_test_session():
    """Create an in-memory SQLite session with market_data table."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.execute(text(_DDL))
    return factory


@pytest.mark.asyncio
async def test_upsert_candles_empty_list_returns_zero():
    """upsert_candles with empty list returns 0 without executing SQL."""
    from app.ingestion.upsert import upsert_candles

    factory = await _make_test_session()
    async with factory() as session:
        result = await upsert_candles(session, [])
    assert result == 0


@pytest.mark.asyncio
async def test_upsert_candles_inserts_and_returns_count():
    """upsert_candles inserts 3 candles and returns count 3."""
    from app.ingestion.upsert import upsert_candles

    factory = await _make_test_session()
    candles = [_make_candle(offset=i) for i in range(3)]

    async with factory() as session:
        count = await upsert_candles(session, candles)
        # Verify via COUNT(*)
        result = await session.execute(text("SELECT COUNT(*) FROM market_data"))
        db_count = result.scalar()

    assert count == 3
    assert db_count == 3


@pytest.mark.asyncio
async def test_upsert_candles_idempotent():
    """Upserting same candles twice results in no duplicates."""
    from app.ingestion.upsert import upsert_candles

    factory = await _make_test_session()
    candles = [_make_candle(offset=i) for i in range(3)]

    async with factory() as session:
        await upsert_candles(session, candles)
        await upsert_candles(session, candles)
        result = await session.execute(text("SELECT COUNT(*) FROM market_data"))
        db_count = result.scalar()

    assert db_count == 3


# ---------------------------------------------------------------------------
# Endpoint tests (Task 2 RED)
# ---------------------------------------------------------------------------

_test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_TestSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)

# Create the market_data table in the in-memory DB for endpoint tests
_ENDPOINT_DDL = """
CREATE TABLE IF NOT EXISTS market_data (
    symbol    TEXT NOT NULL,
    market    TEXT NOT NULL,
    interval  TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open      REAL NOT NULL,
    high      REAL NOT NULL,
    low       REAL NOT NULL,
    close     REAL NOT NULL,
    volume    REAL NOT NULL,
    PRIMARY KEY (symbol, interval, timestamp)
)
"""


def _init_endpoint_db():
    """Synchronously initialize the in-memory DB schema for endpoint tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        async def _create():
            async with _test_engine.begin() as conn:
                await conn.execute(text(_ENDPOINT_DDL))
        loop.run_until_complete(_create())
    finally:
        loop.close()


# Initialize schema at import time (once for all endpoint tests in this module)
_init_endpoint_db()


async def override_get_session() -> AsyncSession:
    """Override get_session to use in-memory SQLite for endpoint tests."""
    async with _TestSessionLocal() as session:
        yield session


def _get_test_client():
    """Return a configured TestClient with DB and auth overrides applied."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.routes.market_data import get_session
    from app.core.auth import get_current_user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test_user"}
    return TestClient(app)


def test_market_data_endpoint_returns_empty_for_unknown_symbol():
    """GET /api/market-data/UNKNOWN?interval=1H returns 200 with empty array."""
    client = _get_test_client()
    resp = client.get("/api/market-data/UNKNOWN?interval=1H")
    assert resp.status_code == 200
    assert resp.json() == []


def test_market_data_endpoint_invalid_interval_returns_422():
    """GET /api/market-data/AAPL?interval=2d returns 422 for invalid interval."""
    client = _get_test_client()
    resp = client.get("/api/market-data/AAPL?interval=2d")
    assert resp.status_code == 422


def test_market_data_endpoint_limit_too_large_returns_422():
    """GET /api/market-data/AAPL?interval=1H&limit=9999 returns 422."""
    client = _get_test_client()
    resp = client.get("/api/market-data/AAPL?interval=1H&limit=9999")
    assert resp.status_code == 422
