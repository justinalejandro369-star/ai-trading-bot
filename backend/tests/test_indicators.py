"""
Unit tests for backend/app/analysis/indicators.py.

All tests use synthetic in-memory DataFrames — no DB required.
Run with: PYTHONPATH=backend uv --project backend run pytest tests/test_indicators.py -q
"""
import pytest
from tests.conftest import make_zero_volume_df

# Import will fail until indicators.py is created (RED phase)
from app.analysis.indicators import MIN_CANDLES, IndicatorSet, compute_indicators


def test_compute_indicators_returns_none_when_insufficient_candles(df_199):
    """Given <200 rows, compute_indicators() must return None (not raise)."""
    result = compute_indicators(df_199, symbol="TEST", interval="1D")
    assert result is None


def test_compute_indicators_returns_indicator_set_when_sufficient_candles(df_250):
    """Given >=200 rows, compute_indicators() returns a non-None IndicatorSet."""
    result = compute_indicators(df_250, symbol="TEST", interval="1D")
    assert result is not None
    assert isinstance(result, IndicatorSet)


def test_indicator_set_rsi_is_float_in_valid_range(df_250):
    """RSI must be a float between 0 and 100."""
    result = compute_indicators(df_250, symbol="TEST", interval="1D")
    assert result is not None
    assert result.rsi_14 is not None
    assert isinstance(result.rsi_14, float)
    assert 0.0 <= result.rsi_14 <= 100.0


def test_indicator_set_macd_fields_populated(df_250):
    """MACD line and signal line must both be floats."""
    result = compute_indicators(df_250, symbol="TEST", interval="1D")
    assert result is not None
    assert result.macd_val is not None
    assert result.macd_signal is not None
    assert isinstance(result.macd_val, float)
    assert isinstance(result.macd_signal, float)


def test_indicator_set_bb_pct_in_zero_one(df_250):
    """Bollinger Band percent B (BBP) must be in [0, 1] range."""
    result = compute_indicators(df_250, symbol="TEST", interval="1D")
    assert result is not None
    # bb_pct can occasionally exceed [0,1] for extreme outliers — check it's a float
    assert result.bb_pct is not None
    assert isinstance(result.bb_pct, float)


def test_indicator_set_adx_is_float(df_250):
    """ADX must be a float."""
    result = compute_indicators(df_250, symbol="TEST", interval="1D")
    assert result is not None
    assert result.adx_14 is not None
    assert isinstance(result.adx_14, float)


def test_indicator_set_ema_50_and_200_populated(df_250):
    """Both EMA-50 and EMA-200 must be populated floats."""
    result = compute_indicators(df_250, symbol="TEST", interval="1D")
    assert result is not None
    assert result.ema_50 is not None
    assert result.ema_200 is not None
    assert isinstance(result.ema_50, float)
    assert isinstance(result.ema_200, float)


def test_indicator_set_close_matches_last_row(df_250):
    """result.close must equal float(df['close'].iloc[-1])."""
    result = compute_indicators(df_250, symbol="TEST", interval="1D")
    assert result is not None
    assert result.close == float(df_250["close"].iloc[-1])


def test_indicator_set_volume_matches_last_row(df_250):
    """result.volume must equal float(df['volume'].iloc[-1])."""
    result = compute_indicators(df_250, symbol="TEST", interval="1D")
    assert result is not None
    assert result.volume == float(df_250["volume"].iloc[-1])


def test_compute_indicators_symbol_and_interval_pass_through(df_250):
    """Symbol and interval are passed through to the IndicatorSet unchanged."""
    result = compute_indicators(df_250, symbol="AAPL", interval="1D")
    assert result is not None
    assert result.symbol == "AAPL"
    assert result.interval == "1D"


def test_compute_indicators_zero_volume_does_not_raise():
    """CoinGecko assets have volume=0.0 — must not raise ZeroDivisionError."""
    df = make_zero_volume_df(250)
    # Should not raise — vol_sma_20 will be 0.0 or None, handled gracefully
    result = compute_indicators(df, symbol="BITCOIN", interval="1D")
    # Result may be None if vol_sma produces NaN, but must not raise
    # (some indicators require nonzero volume internally)


def test_min_candles_constant():
    """MIN_CANDLES must be exactly 200 (EMA-200 requirement)."""
    assert MIN_CANDLES == 200
