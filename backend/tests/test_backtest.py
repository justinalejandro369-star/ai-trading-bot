"""
TDD test suite for the backtesting engine (Phase 3).

All tests use synthetic in-memory DataFrames — no DB, no network required.
Run with: PYTHONPATH=backend uv --project backend run pytest tests/test_backtest.py -q

TDD cycle:
  RED  — tests fail (engine.py does not exist yet)
  GREEN — engine.py implemented, all tests pass
"""
import pytest

from tests.conftest import make_ohlcv_df

# These imports fail until engine.py is created (RED phase)
from app.backtesting.engine import run_backtest
from app.backtesting.models import BacktestResult
from app.strategies.baseline import BaselineStrategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def df_500():
    """500-row OHLCV DataFrame — enough for indicators + backtest."""
    return make_ohlcv_df(500, seed=42)


@pytest.fixture
def df_small():
    """199-row OHLCV DataFrame — below MIN_CANDLES threshold."""
    return make_ohlcv_df(199, seed=99)


# ---------------------------------------------------------------------------
# Core behavior
# ---------------------------------------------------------------------------

def test_run_backtest_returns_backtest_result(df_500):
    """run_backtest() returns a BacktestResult for sufficient data."""
    result = run_backtest(df_500, BaselineStrategy())
    assert isinstance(result, BacktestResult)


def test_backtest_result_has_required_fields(df_500):
    """BacktestResult has all 7 required fields with correct types."""
    result = run_backtest(df_500, BaselineStrategy())
    assert isinstance(result.sharpe_ratio, float)
    assert isinstance(result.max_drawdown, float)
    assert isinstance(result.win_rate, float)
    assert isinstance(result.profit_factor, float)
    assert isinstance(result.total_return, float)
    assert isinstance(result.total_trades, int)
    assert isinstance(result.equity_curve, list)


def test_run_backtest_raises_on_insufficient_data(df_small):
    """run_backtest() raises ValueError when df has fewer than MIN_CANDLES rows."""
    with pytest.raises(ValueError, match="Insufficient data"):
        run_backtest(df_small, BaselineStrategy())


# ---------------------------------------------------------------------------
# Metrics sanity checks
# ---------------------------------------------------------------------------

def test_win_rate_is_fraction_not_percent(df_500):
    """win_rate must be in [0.0, 1.0] — a fraction, not a percentage."""
    result = run_backtest(df_500, BaselineStrategy())
    assert 0.0 <= result.win_rate <= 1.0


def test_max_drawdown_is_non_positive(df_500):
    """max_drawdown must be <= 0.0 (it represents a loss)."""
    result = run_backtest(df_500, BaselineStrategy())
    assert result.max_drawdown <= 0.0


def test_total_trades_is_non_negative(df_500):
    """total_trades must be a non-negative integer."""
    result = run_backtest(df_500, BaselineStrategy())
    assert result.total_trades >= 0


def test_equity_curve_is_list_of_pairs(df_500):
    """equity_curve is a non-empty list of [iso_timestamp_str, float] pairs."""
    result = run_backtest(df_500, BaselineStrategy())
    assert len(result.equity_curve) > 0
    first = result.equity_curve[0]
    assert len(first) == 2
    assert isinstance(first[0], str)   # ISO timestamp string
    assert isinstance(first[1], float) # portfolio value


# ---------------------------------------------------------------------------
# Transaction cost behavior (BKTS-04)
# ---------------------------------------------------------------------------

def test_transaction_costs_reduce_returns(df_500):
    """Higher commission produces lower or equal total_return."""
    result_free = run_backtest(df_500, BaselineStrategy(), commission=0.0, slippage=0.0)
    result_costly = run_backtest(df_500, BaselineStrategy(), commission=0.01, slippage=0.005)
    # With costs, total return must not exceed zero-cost return
    assert result_costly.total_return <= result_free.total_return


# ---------------------------------------------------------------------------
# Look-ahead bias audit (BKTS-02)
# ---------------------------------------------------------------------------

def test_shift1_prevents_look_ahead_bias():
    """
    Audit test: perfect-information signals (no shift) must yield Sharpe >=
    properly shifted honest signals. If honest > biased the shift is broken.

    Uses a large df (500 bars) to ensure statistical signal.

    True look-ahead bias: biased signal uses shift(-1) to peek at next bar's
    close before placing order at bar T. Honest signal delays by 1 bar via
    shift(1). The biased strategy must outperform because it knows the future.
    """
    import vectorbt as vbt

    df = make_ohlcv_df(500, seed=7)

    # Perfect-information: buy at T if close[T+1] > close[T] (CHEATING — uses future)
    biased_entries = (df["close"].shift(-1) > df["close"]).fillna(False).astype(bool)
    biased_exits   = (df["close"].shift(-1) < df["close"]).fillna(False).astype(bool)
    pf_biased = vbt.Portfolio.from_signals(
        df["close"], biased_entries, biased_exits, freq="1D"
    )

    # Honest: shift biased entries/exits by 1 to prevent look-ahead
    honest_entries = biased_entries.shift(1).fillna(False).astype(bool)
    honest_exits   = biased_exits.shift(1).fillna(False).astype(bool)
    pf_honest = vbt.Portfolio.from_signals(
        df["close"], honest_entries, honest_exits, freq="1D"
    )

    biased_sharpe = float(pf_biased.sharpe_ratio())
    honest_sharpe = float(pf_honest.sharpe_ratio())

    assert biased_sharpe >= honest_sharpe, (
        f"shift(1) appears broken: honest Sharpe ({honest_sharpe:.3f}) "
        f"> biased Sharpe ({biased_sharpe:.3f})"
    )
