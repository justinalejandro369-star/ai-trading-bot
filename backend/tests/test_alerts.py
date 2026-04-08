"""
Unit tests for alert engine and alert API routes.

Engine tests: pure function, no DB required.
API tests: use FastAPI TestClient with mocked DB session.
Notifier tests: mock httpx calls.
"""
from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.alerts.engine import AlertTrigger, check_alerts


# ---------------------------------------------------------------------------
# Helpers to build mock AlertRule objects
# ---------------------------------------------------------------------------

def make_rule(id: int, symbol: str, threshold_type: str, threshold_value: float):
    rule = MagicMock()
    rule.id = id
    rule.symbol = symbol
    rule.threshold_type = threshold_type
    rule.threshold_value = threshold_value
    return rule


def make_candles(closes: list[float], volumes: list[float] | None = None) -> pd.DataFrame:
    n = len(closes)
    vols = volumes if volumes is not None else [1_000_000.0] * n
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="D"),
        "open": closes,
        "high": closes,
        "low": closes,
        "close": closes,
        "volume": vols,
    })


# ---------------------------------------------------------------------------
# Engine: price_spike
# ---------------------------------------------------------------------------

class TestPriceSpike:
    def test_spike_triggers_when_above_threshold(self):
        candles = make_candles([100.0, 106.0])  # 6% move
        rule = make_rule(1, "AAPL", "price_spike", 5.0)
        triggers = check_alerts(candles, [rule])
        assert len(triggers) == 1
        assert triggers[0].threshold_type == "price_spike"
        assert "AAPL" in triggers[0].message
        assert "up" in triggers[0].message

    def test_spike_not_triggered_below_threshold(self):
        candles = make_candles([100.0, 103.0])  # 3% move
        rule = make_rule(1, "AAPL", "price_spike", 5.0)
        triggers = check_alerts(candles, [rule])
        assert triggers == []

    def test_spike_down_detected(self):
        candles = make_candles([100.0, 90.0])  # -10%
        rule = make_rule(1, "AAPL", "price_spike", 5.0)
        triggers = check_alerts(candles, [rule])
        assert len(triggers) == 1
        assert "down" in triggers[0].message

    def test_no_trigger_with_zero_prior_close(self):
        candles = make_candles([0.0, 10.0])
        rule = make_rule(1, "AAPL", "price_spike", 5.0)
        triggers = check_alerts(candles, [rule])
        assert triggers == []


# ---------------------------------------------------------------------------
# Engine: volume_surge
# ---------------------------------------------------------------------------

class TestVolumeSurge:
    def test_surge_triggers(self):
        # 19 candles with 1M volume, then 3M (3x surge)
        vols = [1_000_000.0] * 19 + [3_000_000.0]
        candles = make_candles([100.0] * 20, vols)
        rule = make_rule(2, "BTC/USDT", "volume_surge", 2.0)
        triggers = check_alerts(candles, [rule])
        assert len(triggers) == 1
        assert triggers[0].threshold_type == "volume_surge"

    def test_no_surge_below_threshold(self):
        vols = [1_000_000.0] * 20
        candles = make_candles([100.0] * 20, vols)
        rule = make_rule(2, "BTC/USDT", "volume_surge", 2.0)
        triggers = check_alerts(candles, [rule])
        assert triggers == []

    def test_no_surge_with_zero_avg_volume(self):
        vols = [0.0] * 20
        candles = make_candles([100.0] * 20, vols)
        rule = make_rule(2, "BTC/USDT", "volume_surge", 2.0)
        triggers = check_alerts(candles, [rule])
        assert triggers == []


# ---------------------------------------------------------------------------
# Engine: trend_reversal
# ---------------------------------------------------------------------------

class TestTrendReversal:
    def test_bullish_reversal_rsi_crosses_30(self):
        candles = make_candles([100.0, 100.0])
        rule = make_rule(3, "ETH/USDT", "trend_reversal", 0.0)
        rsi = pd.Series([28.0, 32.0])  # crosses above 30
        triggers = check_alerts(candles, [rule], rsi_series=rsi)
        assert len(triggers) == 1
        assert "bullish" in triggers[0].message

    def test_bearish_reversal_rsi_crosses_70(self):
        candles = make_candles([100.0, 100.0])
        rule = make_rule(3, "ETH/USDT", "trend_reversal", 0.0)
        rsi = pd.Series([72.0, 68.0])  # crosses below 70
        triggers = check_alerts(candles, [rule], rsi_series=rsi)
        assert len(triggers) == 1
        assert "bearish" in triggers[0].message

    def test_no_reversal_rsi_stable(self):
        candles = make_candles([100.0, 100.0])
        rule = make_rule(3, "ETH/USDT", "trend_reversal", 0.0)
        rsi = pd.Series([50.0, 52.0])
        triggers = check_alerts(candles, [rule], rsi_series=rsi)
        assert triggers == []

    def test_no_reversal_without_rsi(self):
        candles = make_candles([100.0, 100.0])
        rule = make_rule(3, "ETH/USDT", "trend_reversal", 0.0)
        triggers = check_alerts(candles, [rule], rsi_series=None)
        assert triggers == []


# ---------------------------------------------------------------------------
# Engine: edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_candles_returns_empty(self):
        candles = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        rule = make_rule(1, "AAPL", "price_spike", 5.0)
        triggers = check_alerts(candles, [rule])
        assert triggers == []

    def test_single_candle_returns_empty(self):
        candles = make_candles([100.0])
        rule = make_rule(1, "AAPL", "price_spike", 5.0)
        triggers = check_alerts(candles, [rule])
        assert triggers == []

    def test_multiple_rules_multiple_triggers(self):
        # 20 candles: first 19 at $100 with 1M vol, last at $110 with 3M vol
        closes = [100.0] * 19 + [110.0]
        vols = [1_000_000.0] * 19 + [3_000_000.0]
        many_candles = make_candles(closes, vols)
        rules = [
            make_rule(1, "AAPL", "price_spike", 5.0),
            make_rule(2, "AAPL", "volume_surge", 2.0),
        ]
        triggers = check_alerts(many_candles, rules)
        assert len(triggers) == 2


# ---------------------------------------------------------------------------
# Notifier tests (mock httpx)
# ---------------------------------------------------------------------------

class TestTelegramNotifier:
    @pytest.mark.asyncio
    async def test_sends_when_configured(self):
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.telegram_bot_token = "test-token"
            mock_settings.telegram_chat_id = "123456"
            with patch("app.alerts.telegram_notifier.settings", mock_settings):
                with patch("httpx.AsyncClient") as mock_client_cls:
                    mock_resp = MagicMock()
                    mock_resp.raise_for_status = MagicMock()
                    mock_client = AsyncMock()
                    mock_client.post = AsyncMock(return_value=mock_resp)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock(return_value=False)
                    mock_client_cls.return_value = mock_client

                    from app.alerts.telegram_notifier import send_telegram
                    result = await send_telegram("test message")
                    assert result is True

    @pytest.mark.asyncio
    async def test_skips_when_not_configured(self):
        with patch("app.alerts.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            mock_settings.telegram_chat_id = ""
            from app.alerts.telegram_notifier import send_telegram
            result = await send_telegram("test message")
            assert result is False


class TestDiscordNotifier:
    @pytest.mark.asyncio
    async def test_skips_when_not_configured(self):
        with patch("app.alerts.discord_notifier.settings") as mock_settings:
            mock_settings.discord_webhook_url = ""
            from app.alerts.discord_notifier import send_discord
            result = await send_discord("test message")
            assert result is False
