"""
Tests for the pluggable strategy interface.

Verifies:
    1. Registry discovers bundled strategies (baseline + example).
    2. BaselineStrategy().generate_signal(ind) matches the legacy
       score_signal(ind) — locks zero-behavior-change on the wrap.
    3. BaselineStrategy().generate_entries_exits(df) returns two boolean
       Series aligned with the input DataFrame.
    4. Example strategy round-trips through run_backtest() and produces a
       result distinct from baseline (sanity: actually different algo).
    5. get_strategy('unknown') raises KeyError.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app.analysis.indicators import IndicatorSet, compute_indicators
from app.analysis.signals import score_signal
from app.backtesting.engine import run_backtest
from app.strategies import STRATEGY_REGISTRY, get_strategy, list_strategies
from app.strategies.baseline import BaselineStrategy
from app.strategies.example_ma_crossover import MACrossoverStrategy
from tests.conftest import make_ohlcv_df


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registry_contains_bundled_strategies():
    """Both bundled strategies register at import time."""
    assert "baseline" in STRATEGY_REGISTRY
    assert "ma_crossover" in STRATEGY_REGISTRY
    assert STRATEGY_REGISTRY["baseline"] is BaselineStrategy
    assert STRATEGY_REGISTRY["ma_crossover"] is MACrossoverStrategy


def test_list_strategies_returns_metadata_for_each():
    """list_strategies() exposes name, version, description, required_indicators."""
    metas = list_strategies()
    names = {m["name"] for m in metas}
    assert {"baseline", "ma_crossover"}.issubset(names)
    for meta in metas:
        assert meta["name"]
        assert meta["version"]
        assert meta["description"]
        assert isinstance(meta["required_indicators"], list)


def test_get_strategy_returns_instance_by_name():
    """get_strategy() returns a fresh BaseStrategy instance."""
    s = get_strategy("baseline")
    assert isinstance(s, BaselineStrategy)
    assert s.name == "baseline"


def test_get_strategy_raises_keyerror_on_unknown():
    """Unknown strategy name raises KeyError with a helpful message."""
    with pytest.raises(KeyError, match="Unknown strategy"):
        get_strategy("definitely_does_not_exist")


# ---------------------------------------------------------------------------
# Baseline parity — locks zero behavior change
# ---------------------------------------------------------------------------

def _make_indicator_set(close: float = 100.0, **overrides) -> IndicatorSet:
    """Build an IndicatorSet with sensible defaults; overrides win."""
    defaults: dict = {
        "symbol": "TEST",
        "interval": "1d",
        "rsi_14": 50.0,
        "macd_val": 0.5,
        "macd_signal": 0.0,
        "macd_hist": 0.5,
        "bb_upper": close + 5,
        "bb_lower": close - 5,
        "bb_pct": 0.5,
        "adx_14": 22.0,
        "atr_14": 1.2,
        "ema_50": close - 1,
        "ema_200": close - 3,
        "vol_sma_20": 1_000_000.0,
        "close": close,
        "volume": 1_200_000.0,
    }
    defaults.update(overrides)
    return IndicatorSet(**defaults)


@pytest.mark.parametrize(
    "overrides",
    [
        # Strongly oversold + bullish MACD + lower BB — BUY territory
        {"rsi_14": 25.0, "macd_val": 1.0, "macd_signal": 0.0, "bb_pct": 0.1},
        # Strongly overbought + bearish MACD + upper BB — SELL territory
        {"rsi_14": 75.0, "macd_val": 0.0, "macd_signal": 1.0, "bb_pct": 0.9, "ema_50": 105.0},
        # Mid-range — HOLD territory
        {"rsi_14": 50.0, "macd_val": 0.5, "macd_signal": 0.0, "bb_pct": 0.5},
        # Volume surge amplifying bull
        {"rsi_14": 30.0, "macd_val": 1.0, "macd_signal": 0.0, "bb_pct": 0.15, "volume": 5_000_000.0},
        # Volume surge amplifying bear
        {"rsi_14": 70.0, "macd_val": 0.0, "macd_signal": 1.0, "bb_pct": 0.85, "volume": 5_000_000.0, "ema_50": 105.0},
        # Sparse indicators — many None
        {"rsi_14": None, "macd_val": None, "macd_signal": None, "bb_pct": None, "ema_50": None, "vol_sma_20": None},
    ],
)
def test_baseline_parity_with_legacy_score_signal(overrides):
    """BaselineStrategy().generate_signal(ind) == score_signal(ind), field by field."""
    ind = _make_indicator_set(**overrides)
    s = BaselineStrategy().generate_signal(ind)
    legacy = score_signal(ind)

    assert s.direction == legacy.direction
    assert s.confidence == legacy.confidence
    assert s.entry_price == legacy.entry_price
    assert s.stop_loss == legacy.stop_loss
    assert s.target_price == legacy.target_price
    assert s.reasons == legacy.reasons


# ---------------------------------------------------------------------------
# Vectorized entries/exits
# ---------------------------------------------------------------------------

def test_baseline_generate_entries_exits_shape(df_250):
    """generate_entries_exits returns two boolean Series indexed by df.index."""
    entries, exits = BaselineStrategy().generate_entries_exits(df_250)
    assert isinstance(entries, pd.Series)
    assert isinstance(exits, pd.Series)
    assert len(entries) == len(df_250)
    assert len(exits) == len(df_250)
    assert entries.dtype == bool
    assert exits.dtype == bool
    # Series are aligned with the DataFrame index
    assert (entries.index == df_250.index).all()


def test_ma_crossover_generate_entries_exits_shape(df_250):
    """Example strategy returns aligned boolean Series too."""
    entries, exits = MACrossoverStrategy().generate_entries_exits(df_250)
    assert len(entries) == len(df_250)
    assert len(exits) == len(df_250)
    assert entries.dtype == bool
    assert exits.dtype == bool


# ---------------------------------------------------------------------------
# Round-trip through run_backtest
# ---------------------------------------------------------------------------

def test_baseline_round_trip_through_backtest():
    """run_backtest(df, BaselineStrategy()) returns a tagged BacktestResult."""
    df = make_ohlcv_df(500, seed=11)
    result = run_backtest(df, BaselineStrategy())
    assert result.strategy_name == "baseline"
    assert isinstance(result.equity_curve, list)
    assert len(result.equity_curve) > 0


def test_ma_crossover_round_trip_through_backtest():
    """Example strategy round-trips through run_backtest with the right tag."""
    df = make_ohlcv_df(500, seed=11)
    result = run_backtest(df, MACrossoverStrategy())
    assert result.strategy_name == "ma_crossover"
    assert isinstance(result.equity_curve, list)


def test_different_strategies_produce_distinguishable_results():
    """Baseline and MA crossover on the same data produce different trade counts.

    Synthetic data is random — total_return numbers can collide by chance,
    but the strategies' trade counts come from genuinely different math,
    so they should differ for at least one of the seeds we test.
    """
    seeds_with_diff = 0
    for seed in (5, 11, 23, 42, 99):
        df = make_ohlcv_df(500, seed=seed)
        baseline_result = run_backtest(df, BaselineStrategy())
        crossover_result = run_backtest(df, MACrossoverStrategy())
        if baseline_result.total_trades != crossover_result.total_trades:
            seeds_with_diff += 1
    assert seeds_with_diff >= 1, "strategies produced identical trade counts on every seed"


# ---------------------------------------------------------------------------
# Integration: scanner -> indicators -> baseline strategy
# ---------------------------------------------------------------------------

def test_baseline_works_on_real_indicator_set(df_250):
    """compute_indicators -> BaselineStrategy.generate_signal end-to-end."""
    ind = compute_indicators(df_250, symbol="TEST", interval="1d")
    assert ind is not None
    signal = BaselineStrategy().generate_signal(ind)
    assert signal.direction in ("BUY", "SELL", "HOLD")
    assert 0 <= signal.confidence <= 100
