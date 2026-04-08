"""
Integration test scaffolding for the paper trading REST API (Phase 4, Wave 2).

These tests are RED stubs — they are intentionally written to FAIL until
Wave 2 implements the /api/paper/* endpoints. This file establishes the
expected API contract so Wave 2 has a green target to work toward.

All test bodies contain `assert False, "implement in Wave 2"` to ensure
this file remains in RED state during Plan 1 execution.

Run with: PYTHONPATH=backend uv --project backend run pytest tests/test_paper_trading_api.py -q
"""
import pytest

# Import ORM models to register tables with Base.metadata (required for in-memory DB)
from app.models.paper_trading import (  # noqa: F401
    EquitySnapshot,
    PaperAccount,
    PaperPosition,
)


# ---------------------------------------------------------------------------
# REST API integration stubs (Wave 2 implements these)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_account_returns_200():
    """POST /api/paper/accounts should return 200 with created account."""
    assert False, "implement in Wave 2"


@pytest.mark.asyncio
async def test_get_account_summary():
    """GET /api/paper/accounts/1 should return 200 with account summary."""
    assert False, "implement in Wave 2"


@pytest.mark.asyncio
async def test_place_buy_order_creates_position():
    """POST /api/paper/accounts/1/orders with BUY should return 201 and create a position."""
    assert False, "implement in Wave 2"


@pytest.mark.asyncio
async def test_order_no_market_data_422():
    """POST /api/paper/accounts/1/orders for unknown symbol should return 422."""
    assert False, "implement in Wave 2"


@pytest.mark.asyncio
async def test_equity_curve_shape():
    """GET /api/paper/accounts/1/equity should return a list of [ts, float] pairs."""
    assert False, "implement in Wave 2"


@pytest.mark.asyncio
async def test_compare_returns_both_series():
    """GET /api/paper/accounts/1/compare should return {'paper': [...], 'backtest': [...]}."""
    assert False, "implement in Wave 2"


@pytest.mark.asyncio
async def test_compare_null_backtest():
    """GET /api/paper/accounts/1/compare when no backtest linked should return {'paper': [...], 'backtest': null}."""
    assert False, "implement in Wave 2"
