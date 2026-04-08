"""
Integration tests for the paper trading REST API (Phase 4, Wave 2).

Tests cover all five paper trading endpoints using in-memory SQLite seeded
with synthetic data. No external DB, no network calls, no mocking of
business logic — real fill_order() and compute_equity() are exercised.

Run with:
    PYTHONPATH=backend uv --project backend run pytest tests/test_paper_trading_api.py -q
"""
import json
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.market_data import get_session
from app.main import app
from app.models.backtest import BacktestRun  # noqa: F401 — registers table with Base.metadata
from app.models.market_data import Base, MarketData  # noqa: F401 — registers table with Base.metadata
from app.models.paper_trading import (  # noqa: F401 — registers tables with Base.metadata
    EquitySnapshot,
    PaperAccount,
    PaperPosition,
)

# ---------------------------------------------------------------------------
# In-memory SQLite test database
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


def _make_market_data_row(symbol: str = "TEST", interval: str = "1D", close: float = 100.0) -> dict:
    """Return a dict suitable for inserting into market_data."""
    return {
        "symbol": symbol,
        "market": "stock",
        "interval": interval,
        "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "open": close * 0.99,
        "high": close * 1.01,
        "low": close * 0.98,
        "close": close,
        "volume": 1_000_000.0,
    }


@pytest_asyncio.fixture
async def client(monkeypatch):
    """
    AsyncClient with in-memory SQLite.

    Seeded with one market_data row for symbol=TEST/interval=1D/close=100.0
    so that order fill tests have a price to work with.

    The get_session dependency is overridden to use the test DB.
    """
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed one market_data row
    async with TestSession() as session:
        row = _make_market_data_row()
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

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper: create an account via the API
# ---------------------------------------------------------------------------


async def _create_account(ac: AsyncClient, **kwargs) -> dict:
    """POST /api/paper/accounts with defaults, return parsed JSON body."""
    payload = {"name": "Test Account", "starting_balance": 10000.0, **kwargs}
    resp = await ac.post("/api/paper/accounts", json=payload)
    assert resp.status_code == 200, f"create_account failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_account_returns_200(client):
    """POST /api/paper/accounts returns 200 with id and matching cash_balance."""
    resp = await client.post(
        "/api/paper/accounts",
        json={"name": "My Account", "starting_balance": 10000.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["cash_balance"] == 10000.0
    assert data["starting_balance"] == 10000.0
    assert data["name"] == "My Account"


@pytest.mark.asyncio
async def test_get_account_summary(client):
    """GET /api/paper/accounts/{id} returns 200 with total_equity and open_positions."""
    account = await _create_account(client)
    account_id = account["id"]

    resp = await client.get(f"/api/paper/accounts/{account_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_equity" in data
    assert "open_positions" in data
    assert isinstance(data["open_positions"], list)
    # Fresh account with no positions: equity equals cash
    assert data["total_equity"] == data["cash_balance"]


@pytest.mark.asyncio
async def test_place_buy_order_creates_position(client):
    """POST /api/paper/accounts/{id}/orders with BUY returns 201, fill_price, and new_cash < 10000."""
    account = await _create_account(client, slippage_std=0.0)  # zero slippage for determinism
    account_id = account["id"]

    resp = await client.post(
        f"/api/paper/accounts/{account_id}/orders",
        json={"symbol": "TEST", "interval": "1D", "side": "BUY", "quantity": 1.0},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "fill_price" in data
    assert "new_cash" in data
    assert data["new_cash"] < 10000.0  # cash reduced after BUY
    assert data["account_id"] == account_id


@pytest.mark.asyncio
async def test_order_no_market_data_422(client):
    """POST order for an unknown symbol returns 422 with detail message."""
    account = await _create_account(client)
    account_id = account["id"]

    resp = await client.post(
        f"/api/paper/accounts/{account_id}/orders",
        json={"symbol": "UNKNOWN", "interval": "1D", "side": "BUY", "quantity": 1.0},
    )
    assert resp.status_code == 422
    assert "No market data" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_equity_curve_shape(client):
    """GET /api/paper/accounts/{id}/equity returns equity_curve as list of [str, float] pairs."""
    account = await _create_account(client, slippage_std=0.0)
    account_id = account["id"]

    # Place an order so a snapshot is inserted immediately
    await client.post(
        f"/api/paper/accounts/{account_id}/orders",
        json={"symbol": "TEST", "interval": "1D", "side": "BUY", "quantity": 1.0},
    )

    resp = await client.get(f"/api/paper/accounts/{account_id}/equity")
    assert resp.status_code == 200
    data = resp.json()
    assert "equity_curve" in data
    assert isinstance(data["equity_curve"], list)
    assert len(data["equity_curve"]) >= 1
    # Each element must be [timestamp_string, float]
    for point in data["equity_curve"]:
        assert len(point) == 2
        assert isinstance(point[0], str)
        assert isinstance(point[1], float)


@pytest.mark.asyncio
async def test_compare_returns_both_series(client):
    """GET /api/paper/accounts/{id}/compare returns paper and backtest series when linked."""
    # Need to insert a BacktestRun row directly into the test DB via account creation fixture
    # We create a fresh mini-engine for this test to control the BacktestRun row
    from sqlalchemy.ext.asyncio import create_async_engine as _cae
    from sqlalchemy.orm import sessionmaker as _sm

    engine2 = _cae(TEST_DB_URL, echo=False)
    async with engine2.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session2 = _sm(engine2, class_=AsyncSession, expire_on_commit=False)

    # Insert a BacktestRun and a MarketData row
    async with Session2() as session:
        now = datetime.now(timezone.utc)
        backtest = BacktestRun(
            symbol="TEST",
            interval="1D",
            run_at=now,
            commission=0.001,
            slippage=0.001,
            init_cash=10000.0,
            equity_curve=json.dumps([[now.isoformat(), 10000.0]]),
        )
        session.add(backtest)
        await session.flush()
        bt_id = backtest.id

        # Market data for the order fill
        await session.execute(
            text(
                """
                INSERT INTO market_data
                    (symbol, market, interval, timestamp, open, high, low, close, volume)
                VALUES
                    (:symbol, :market, :interval, :timestamp, :open, :high, :low, :close, :volume)
                """
            ),
            _make_market_data_row(),
        )
        await session.commit()

    async def override2():
        async with Session2() as session:
            yield session

    app.dependency_overrides[get_session] = override2

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create account linked to the backtest run
        acct_resp = await ac.post(
            "/api/paper/accounts",
            json={"name": "Linked", "starting_balance": 10000.0, "backtest_run_id": bt_id},
        )
        assert acct_resp.status_code == 200
        account_id = acct_resp.json()["id"]

        # Place an order so paper series has at least one snapshot
        await ac.post(
            f"/api/paper/accounts/{account_id}/orders",
            json={"symbol": "TEST", "interval": "1D", "side": "BUY", "quantity": 1.0, "slippage_std": 0.0},
        )

        resp = await ac.get(f"/api/paper/accounts/{account_id}/compare")
        assert resp.status_code == 200
        data = resp.json()
        assert "paper" in data
        assert "backtest" in data
        assert isinstance(data["paper"], list)
        assert isinstance(data["backtest"], list)
        assert data["backtest_run_id"] == bt_id

    app.dependency_overrides.clear()
    await engine2.dispose()


@pytest.mark.asyncio
async def test_compare_null_backtest(client):
    """GET /api/paper/accounts/{id}/compare returns backtest=null when no backtest linked."""
    account = await _create_account(client)
    account_id = account["id"]

    resp = await client.get(f"/api/paper/accounts/{account_id}/compare")
    assert resp.status_code == 200
    data = resp.json()
    assert data["backtest"] is None
    assert data["backtest_run_id"] is None
    assert isinstance(data["paper"], list)
