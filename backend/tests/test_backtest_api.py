"""
Integration tests for POST /api/backtest.

Uses in-memory SQLite populated with synthetic candle rows — no external DB,
no network, no vectorbt mocking (real run_backtest() is called).

Run with: PYTHONPATH=backend uv --project backend run pytest tests/test_backtest_api.py -q
"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.market_data import get_session
from app.core.auth import get_current_user
from app.main import app
from app.models.backtest import BacktestRun  # noqa: F401 — registers table with Base.metadata
from app.models.market_data import Base, MarketData  # noqa: F401 — registers table with Base.metadata
from app.analysis.indicators import MIN_CANDLES
from tests.conftest import override_get_current_user

# ---------------------------------------------------------------------------
# In-memory SQLite test database
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


def _make_candle_rows(symbol: str, n: int, seed: int = 42) -> list[dict]:
    """Generate n synthetic OHLCV row dicts for the market_data table."""
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0, 1, n))
    close = np.maximum(close, 1.0)
    high = close + rng.uniform(0.1, 2.0, n)
    low = close - rng.uniform(0.1, 2.0, n)
    low = np.maximum(low, 0.5)
    open_ = close + rng.normal(0, 0.5, n)
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)

    base_ts = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "symbol": symbol,
            "market": "stock",
            "interval": "1D",
            "timestamp": base_ts + timedelta(days=i),
            "open": float(open_[i]),
            "high": float(high[i]),
            "low": float(low[i]),
            "close": float(close[i]),
            "volume": float(volume[i]),
        }
        for i in range(n)
    ]


@pytest_asyncio.fixture
async def client_with_data(monkeypatch):
    """
    AsyncClient with in-memory SQLite seeded with MIN_CANDLES+50 candles for TEST.
    The get_session dependency is overridden to use the test DB.
    """
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Insert enough candle rows to satisfy MIN_CANDLES
    n_rows = MIN_CANDLES + 50
    rows = _make_candle_rows("TEST", n_rows)
    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestSession() as session:
        for row in rows:
            await session.execute(
                text(
                    """
                    INSERT INTO market_data
                        (symbol, market, interval, timestamp, open, high, low, close, volume)
                    VALUES
                        (:symbol, :market, :interval, :timestamp, :open, :high, :low, :close, :volume)
                    """
                ),
                row,
            )
        await session.commit()

    async def override_get_session():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client_empty(monkeypatch):
    """AsyncClient with empty in-memory SQLite (no candle rows)."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_backtest_returns_metrics(client_with_data):
    """POST /api/backtest returns 200 with all 7 required metric fields."""
    response = await client_with_data.post(
        "/api/backtest",
        json={"symbol": "TEST", "interval": "1D"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "sharpe_ratio" in data
    assert "max_drawdown" in data
    assert "win_rate" in data
    assert "profit_factor" in data
    assert "total_return" in data
    assert "total_trades" in data
    assert "equity_curve" in data


@pytest.mark.asyncio
async def test_post_backtest_response_has_equity_curve_list(client_with_data):
    """equity_curve in response is a non-empty list."""
    response = await client_with_data.post(
        "/api/backtest",
        json={"symbol": "TEST", "interval": "1D"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["equity_curve"], list)
    assert len(data["equity_curve"]) > 0


@pytest.mark.asyncio
async def test_win_rate_in_valid_range(client_with_data):
    """win_rate in response is between 0.0 and 1.0 (fraction, not percent)."""
    response = await client_with_data.post(
        "/api/backtest",
        json={"symbol": "TEST", "interval": "1D"},
    )
    assert response.status_code == 200
    win_rate = response.json()["win_rate"]
    assert 0.0 <= win_rate <= 1.0


@pytest.mark.asyncio
async def test_post_backtest_no_data_returns_422(client_empty):
    """POST /api/backtest for unknown symbol with empty DB returns 422."""
    response = await client_empty.post(
        "/api/backtest",
        json={"symbol": "UNKNOWN", "interval": "1D"},
    )
    assert response.status_code == 422
    assert "Insufficient data" in response.json()["detail"]


@pytest.mark.asyncio
async def test_post_backtest_insufficient_rows_returns_422(monkeypatch):
    """POST /api/backtest with only 10 candle rows returns 422."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    rows = _make_candle_rows("FEW", 10)  # 10 rows < MIN_CANDLES
    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestSession() as session:
        for row in rows:
            await session.execute(
                text(
                    """
                    INSERT INTO market_data
                        (symbol, market, interval, timestamp, open, high, low, close, volume)
                    VALUES
                        (:symbol, :market, :interval, :timestamp, :open, :high, :low, :close, :volume)
                    """
                ),
                row,
            )
        await session.commit()

    async def override_get_session():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/backtest",
                json={"symbol": "FEW", "interval": "1D"},
            )
        assert response.status_code == 422
        assert "Insufficient data" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
