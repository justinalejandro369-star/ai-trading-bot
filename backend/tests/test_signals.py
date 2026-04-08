"""
Unit tests for score_signal() and detect_regime().

All tests use hand-crafted IndicatorSet instances — no DB or pandas required.
Run with: PYTHONPATH=backend uv --project backend run pytest tests/test_signals.py -q
"""
import pytest

from app.analysis.indicators import IndicatorSet
from app.analysis.signals import SignalResult, score_signal
from app.analysis.regime import RegimeType, detect_regime


def _make_ind(**overrides) -> IndicatorSet:
    """Build an IndicatorSet with sensible defaults, override specific fields."""
    defaults = dict(
        symbol="TEST",
        interval="1D",
        rsi_14=50.0,
        macd_val=None,
        macd_signal=None,
        macd_hist=None,
        bb_upper=None,
        bb_lower=None,
        bb_pct=0.5,
        adx_14=20.0,
        atr_14=2.0,
        ema_50=100.0,
        ema_200=95.0,
        vol_sma_20=None,
        close=100.0,
        volume=1_000_000.0,
    )
    defaults.update(overrides)
    return IndicatorSet(**defaults)


# --- score_signal tests ---

def test_score_signal_buy_when_rsi_oversold_and_macd_bullish():
    """RSI oversold (25 pts) + MACD bullish (30 pts) = 55 bull → BUY."""
    ind = _make_ind(rsi_14=30.0, macd_val=1.0, macd_signal=0.5, bb_pct=0.5,
                    ema_50=95.0, close=100.0, atr_14=2.0, vol_sma_20=None)
    result = score_signal(ind)
    assert result.direction == "BUY"


def test_score_signal_sell_when_rsi_overbought_and_macd_bearish():
    """RSI overbought (25 pts) + MACD bearish (30 pts) = 55 bear → SELL."""
    ind = _make_ind(rsi_14=70.0, macd_val=0.5, macd_signal=1.0, bb_pct=0.5,
                    ema_50=105.0, close=100.0, atr_14=2.0, vol_sma_20=None)
    result = score_signal(ind)
    assert result.direction == "SELL"


def test_score_signal_hold_when_mixed_signals():
    """MACD bullish (30 pts) + EMA above (10 pts) = 40 bull — below 55 → HOLD."""
    ind = _make_ind(rsi_14=50.0, macd_val=1.0, macd_signal=0.5, bb_pct=0.5,
                    ema_50=99.0, close=100.0, vol_sma_20=None)
    result = score_signal(ind)
    assert result.direction == "HOLD"


def test_score_signal_confidence_bounded_0_to_100():
    """Confidence must always be in [0, 100] — no overflow."""
    # Max possible: 25 + 30 + 25 + 10 + 10 = 100
    ind = _make_ind(rsi_14=30.0, macd_val=1.0, macd_signal=0.5, bb_pct=0.1,
                    ema_50=95.0, close=100.0, vol_sma_20=1_000_000.0,
                    volume=2_000_000.0, atr_14=2.0)
    result = score_signal(ind)
    assert 0 <= result.confidence <= 100


def test_score_signal_buy_has_stop_loss_and_target():
    """BUY signal with atr_14=2.0 → stop=close-4.0, target=close+6.0."""
    ind = _make_ind(rsi_14=30.0, macd_val=1.0, macd_signal=0.5, bb_pct=0.5,
                    ema_50=95.0, close=100.0, atr_14=2.0, vol_sma_20=None)
    result = score_signal(ind)
    assert result.direction == "BUY"
    assert result.stop_loss is not None
    assert abs(result.stop_loss - (100.0 - 2 * 2.0)) < 1e-9
    assert result.target_price is not None
    assert abs(result.target_price - (100.0 + 3 * 2.0)) < 1e-9


def test_score_signal_sell_has_no_stop_or_target():
    """SELL result has stop_loss=None and target_price=None (per research spec)."""
    ind = _make_ind(rsi_14=70.0, macd_val=0.5, macd_signal=1.0, bb_pct=0.5,
                    ema_50=105.0, close=100.0, atr_14=2.0, vol_sma_20=None)
    result = score_signal(ind)
    assert result.direction == "SELL"
    assert result.stop_loss is None
    assert result.target_price is None


def test_score_signal_none_indicators_handled_gracefully():
    """All indicator fields None except close — no exception, returns HOLD."""
    ind = _make_ind(rsi_14=None, macd_val=None, macd_signal=None, bb_pct=None,
                    adx_14=None, atr_14=None, ema_50=None, vol_sma_20=None)
    result = score_signal(ind)
    assert result.direction == "HOLD"
    assert isinstance(result, SignalResult)


def test_score_signal_volume_surge_amplifies_bull():
    """Volume surge (volume > 1.5x vol_sma) adds 10 pts to leading direction."""
    # Without volume surge: bull = 30 (MACD) + 10 (EMA) = 40
    ind_no_surge = _make_ind(rsi_14=50.0, macd_val=1.0, macd_signal=0.5,
                              bb_pct=0.5, ema_50=99.0, close=100.0,
                              vol_sma_20=1_000_000.0, volume=1_000_000.0)
    result_no_surge = score_signal(ind_no_surge)
    # With volume surge: bull = 30 + 10 (EMA) + 10 (vol) = 50
    ind_surge = _make_ind(rsi_14=50.0, macd_val=1.0, macd_signal=0.5,
                          bb_pct=0.5, ema_50=99.0, close=100.0,
                          vol_sma_20=1_000_000.0, volume=2_000_000.0)
    result_surge = score_signal(ind_surge)
    assert result_surge.confidence >= result_no_surge.confidence


def test_score_signal_volume_zero_does_not_crash():
    """volume=0.0 and vol_sma_20=0.0 (CoinGecko) — no ZeroDivisionError."""
    ind = _make_ind(volume=0.0, vol_sma_20=0.0)
    result = score_signal(ind)
    assert isinstance(result, SignalResult)


# --- detect_regime tests ---

def test_detect_regime_ranging_when_adx_none():
    """adx_14=None → fallback to 'ranging'."""
    ind = _make_ind(adx_14=None, atr_14=1.0)
    result = detect_regime(ind, atr_sma_20=1.0)
    assert result == "ranging"


def test_detect_regime_ranging_when_adx_low():
    """ADX <= 25 → 'ranging' regardless of ATR."""
    ind = _make_ind(adx_14=15.0, atr_14=2.0)
    result = detect_regime(ind, atr_sma_20=1.0)
    assert result == "ranging"


def test_detect_regime_trending_when_adx_high_atr_normal():
    """ADX > 25 and ATR <= 1.2x SMA → 'trending'."""
    ind = _make_ind(adx_14=30.0, atr_14=1.0)
    result = detect_regime(ind, atr_sma_20=1.0)
    assert result == "trending"


def test_detect_regime_volatile_when_adx_high_atr_spike():
    """ADX > 25 and ATR > 1.2x SMA → 'volatile'."""
    ind = _make_ind(adx_14=30.0, atr_14=1.5)
    result = detect_regime(ind, atr_sma_20=1.0)  # 1.5 > 1.0 * 1.2
    assert result == "volatile"


def test_detect_regime_no_atr_sma_defaults_to_trending():
    """When atr_sma_20=None and ADX > 25, defaults to 'trending' (not volatile)."""
    ind = _make_ind(adx_14=30.0, atr_14=2.0)
    result = detect_regime(ind, atr_sma_20=None)
    assert result == "trending"
