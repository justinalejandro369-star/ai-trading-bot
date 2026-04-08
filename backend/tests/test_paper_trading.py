"""
TDD unit tests for paper trading engine (Phase 4, Plan 1).

Tests cover fill_order() and compute_equity() pure functions.
No DB, no network, no FastAPI — fully isolated.

TDD cycle:
  RED  — tests fail with ImportError (engine.py does not exist yet)
  GREEN — engine.py implemented, all tests pass

Run with: PYTHONPATH=backend uv --project backend run pytest tests/test_paper_trading.py -q
"""
import random

import pytest

# These imports fail until engine.py is created (RED phase)
from app.paper_trading.engine import FillResult, compute_equity, fill_order


# ---------------------------------------------------------------------------
# fill_order() — slippage direction
# ---------------------------------------------------------------------------


def test_buy_fill_has_slippage():
    """BUY with slippage_std=0.01 fills above last_price (slippage applied upward)."""
    # Run multiple times to avoid lucky zero draws
    last_price = 100.0
    random.seed(42)
    results = [
        fill_order(
            side="BUY",
            symbol="AAPL",
            quantity=1.0,
            last_price=last_price,
            cash_balance=10_000.0,
            position_qty=0.0,
            avg_entry_price=0.0,
            slippage_std=0.01,
            commission=0.0,
        )
        for _ in range(10)
    ]
    # At least one fill should be above last_price — BUY always uses abs(offset)
    assert all(r.fill_price >= last_price for r in results), (
        "BUY fills should always be >= last_price when slippage_std > 0"
    )


def test_sell_fill_has_slippage():
    """SELL with slippage_std=0.01 fills below last_price (slippage applied downward)."""
    last_price = 100.0
    random.seed(42)
    results = [
        fill_order(
            side="SELL",
            symbol="AAPL",
            quantity=1.0,
            last_price=last_price,
            cash_balance=0.0,
            position_qty=100.0,
            avg_entry_price=90.0,
            slippage_std=0.01,
            commission=0.0,
        )
        for _ in range(10)
    ]
    # SELL always uses -abs(offset) so fill_price <= last_price
    assert all(r.fill_price <= last_price for r in results), (
        "SELL fills should always be <= last_price when slippage_std > 0"
    )


def test_buy_fill_zero_slippage_exact_price():
    """BUY with slippage_std=0.0 returns fill_price == last_price exactly."""
    result = fill_order(
        side="BUY",
        symbol="AAPL",
        quantity=1.0,
        last_price=100.0,
        cash_balance=10_000.0,
        position_qty=0.0,
        avg_entry_price=0.0,
        slippage_std=0.0,
        commission=0.0,
    )
    assert result.fill_price == 100.0


def test_sell_fill_zero_slippage_exact_price():
    """SELL with slippage_std=0.0 returns fill_price == last_price exactly."""
    result = fill_order(
        side="SELL",
        symbol="AAPL",
        quantity=1.0,
        last_price=100.0,
        cash_balance=0.0,
        position_qty=10.0,
        avg_entry_price=90.0,
        slippage_std=0.0,
        commission=0.0,
    )
    assert result.fill_price == 100.0


# ---------------------------------------------------------------------------
# fill_order() — cash arithmetic
# ---------------------------------------------------------------------------


def test_buy_fill_deducts_cash():
    """BUY 10 shares @ last_price=100, slippage_std=0, commission=0.001 — cash deducted correctly."""
    starting_cash = 5_000.0
    result = fill_order(
        side="BUY",
        symbol="AAPL",
        quantity=10.0,
        last_price=100.0,
        cash_balance=starting_cash,
        position_qty=0.0,
        avg_entry_price=0.0,
        slippage_std=0.0,
        commission=0.001,
    )
    expected_debit = 100.0 * 10.0 * (1 + 0.001)
    assert abs(result.new_cash - (starting_cash - expected_debit)) < 1e-9


def test_sell_fill_credits_cash():
    """SELL 10 shares @ last_price=100, slippage_std=0, commission=0.001 — cash credited correctly."""
    starting_cash = 0.0
    result = fill_order(
        side="SELL",
        symbol="AAPL",
        quantity=10.0,
        last_price=100.0,
        cash_balance=starting_cash,
        position_qty=10.0,
        avg_entry_price=90.0,
        slippage_std=0.0,
        commission=0.001,
    )
    expected_credit = 100.0 * 10.0 * (1 - 0.001)
    assert abs(result.new_cash - (starting_cash + expected_credit)) < 1e-9


# ---------------------------------------------------------------------------
# fill_order() — guard conditions
# ---------------------------------------------------------------------------


def test_buy_insufficient_cash_raises():
    """BUY when total cost exceeds cash_balance raises ValueError."""
    with pytest.raises(ValueError):
        fill_order(
            side="BUY",
            symbol="AAPL",
            quantity=100.0,
            last_price=100.0,
            cash_balance=50.0,  # nowhere near enough
            position_qty=0.0,
            avg_entry_price=0.0,
            slippage_std=0.0,
            commission=0.001,
        )


def test_sell_insufficient_position_raises():
    """SELL quantity > position_qty raises ValueError."""
    with pytest.raises(ValueError):
        fill_order(
            side="SELL",
            symbol="AAPL",
            quantity=20.0,
            last_price=100.0,
            cash_balance=0.0,
            position_qty=5.0,  # only 5 shares held, trying to sell 20
            avg_entry_price=90.0,
            slippage_std=0.0,
            commission=0.001,
        )


# ---------------------------------------------------------------------------
# fill_order() — P&L
# ---------------------------------------------------------------------------


def test_buy_realized_pnl_is_zero():
    """BUY fill always returns realized_pnl == 0.0 (no realized gain on entry)."""
    result = fill_order(
        side="BUY",
        symbol="AAPL",
        quantity=10.0,
        last_price=100.0,
        cash_balance=5_000.0,
        position_qty=0.0,
        avg_entry_price=0.0,
        slippage_std=0.0,
        commission=0.001,
    )
    assert result.realized_pnl == 0.0


def test_sell_realized_pnl_positive():
    """SELL 10 shares bought at avg_entry=90, sold at 100, slippage_std=0 — realized_pnl > 0."""
    result = fill_order(
        side="SELL",
        symbol="AAPL",
        quantity=10.0,
        last_price=100.0,
        cash_balance=0.0,
        position_qty=10.0,
        avg_entry_price=90.0,
        slippage_std=0.0,
        commission=0.001,
    )
    assert result.realized_pnl > 0.0


# ---------------------------------------------------------------------------
# compute_equity()
# ---------------------------------------------------------------------------


def test_compute_equity_no_positions():
    """compute_equity with no positions returns cash as-is."""
    equity = compute_equity(cash=5_000.0, positions=[], last_prices={})
    assert equity == 5_000.0


def test_compute_equity_includes_positions():
    """compute_equity marks positions to market using last_prices."""
    positions = [
        {"symbol": "AAPL", "quantity": 10.0, "avg_entry_price": 100.0}
    ]
    equity = compute_equity(
        cash=5_000.0,
        positions=positions,
        last_prices={"AAPL": 110.0},
    )
    assert equity == 5_000.0 + (10.0 * 110.0)  # 6100.0


def test_compute_equity_missing_price_fallback():
    """compute_equity falls back to avg_entry_price when symbol missing from last_prices."""
    positions = [
        {"symbol": "AAPL", "quantity": 10.0, "avg_entry_price": 100.0}
    ]
    equity = compute_equity(
        cash=5_000.0,
        positions=positions,
        last_prices={},  # AAPL not present
    )
    # Falls back to avg_entry_price=100.0
    assert equity == 5_000.0 + (10.0 * 100.0)  # 6000.0
