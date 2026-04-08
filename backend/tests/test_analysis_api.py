"""
Integration tests for the indicators and signals REST endpoints.

Uses an in-memory SQLite database. Tests verify endpoint response shapes and
SQL query correctness — no actual indicator computation happens here (that's
covered by test_indicators.py and test_signals.py).

Run with: PYTHONPATH=backend uv --project backend run pytest tests/test_analysis_api.py -q
"""
import json
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.market_data import Base
from app.models.signal import TradingSignal
from app.api.routes.signals import get_session as signals_get_session
from app.api.routes.indicators import get_session as indicators_get_session

# --- Test database setup ---

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(test_session_factory):
    """FastAPI test client with DB dependency overrides."""

    async def override_signals_session():
        async with test_session_factory() as session:
            yield session

    async def override_indicators_session():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[signals_get_session] = override_signals_session
    app.dependency_overrides[indicators_get_session] = override_indicators_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def _make_signal(symbol="AAPL", interval="1D", direction="BUY", confidence=70,
                 regime="trending", close=150.0) -> TradingSignal:
    return TradingSignal(
        symbol=symbol,
        interval=interval,
        scanned_at=datetime.now(tz=timezone.utc),
        direction=direction,
        confidence=confidence,
        regime=regime,
        close=close,
        entry_price=close,
        stop_loss=close - 4.0,
        target_price=close + 6.0,
        rsi_14=30.0,
        macd_val=1.0,
        adx_14=28.0,
        atr_14=2.0,
        reasons=json.dumps(["RSI oversold (30.0)", "MACD above signal line"]),
    )


# --- Indicators endpoint tests ---

@pytest.mark.asyncio
async def test_get_indicators_no_data_returns_404(client, test_session_factory):
    """No candle data for symbol → 404 with detail message."""
    resp = await client.get("/api/indicators/AAPL?interval=1D")
    assert resp.status_code == 404


# --- Signals endpoint tests ---

@pytest.mark.asyncio
async def test_get_signals_empty_returns_empty_list(client):
    """Empty signals table → GET /api/signals returns 200 with []."""
    resp = await client.get("/api/signals")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_signals_top_empty_returns_empty_list(client):
    """Empty signals table → GET /api/signals/top returns 200 with []."""
    resp = await client.get("/api/signals/top")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_signals_returns_signal_fields(client, test_session_factory):
    """One signal in DB → response includes required fields."""
    async with test_session_factory() as session:
        session.add(_make_signal())
        await session.commit()

    resp = await client.get("/api/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    sig = data[0]
    assert sig["symbol"] == "AAPL"
    assert sig["direction"] == "BUY"
    assert sig["confidence"] == 70
    assert sig["regime"] == "trending"
    assert "close" in sig
    assert "reasons" in sig


@pytest.mark.asyncio
async def test_get_signals_top_sorted_by_confidence_desc(client, test_session_factory):
    """Three signals with confidence 40, 70, 55 → /top returns [70, 55, 40]."""
    async with test_session_factory() as session:
        session.add(_make_signal(symbol="AAPL", confidence=40, direction="HOLD"))
        session.add(_make_signal(symbol="MSFT", confidence=70, direction="BUY"))
        session.add(_make_signal(symbol="NVDA", confidence=55, direction="BUY"))
        await session.commit()

    resp = await client.get("/api/signals/top")
    assert resp.status_code == 200
    data = resp.json()
    confidences = [s["confidence"] for s in data]
    assert confidences == sorted(confidences, reverse=True)


@pytest.mark.asyncio
async def test_get_signals_top_limit_param(client, test_session_factory):
    """GET /api/signals/top?limit=2 with 3 signals → exactly 2 returned."""
    async with test_session_factory() as session:
        session.add(_make_signal(symbol="AAPL", confidence=80, direction="BUY"))
        session.add(_make_signal(symbol="MSFT", confidence=70, direction="BUY"))
        session.add(_make_signal(symbol="NVDA", confidence=60, direction="BUY"))
        await session.commit()

    resp = await client.get("/api/signals/top?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
