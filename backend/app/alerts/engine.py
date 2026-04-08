"""
Alert engine: pure functions that evaluate candle data and signals
against alert rules to detect triggerable conditions.

Detectable conditions:
  - price_spike: last close moved > threshold % from prior close
  - volume_surge: last volume > threshold × 20-period average volume
  - trend_reversal: RSI crosses 30 (oversold->recovery) or 70 (overbought->reversal)

Design:
  - check_alerts() is a pure function — no DB I/O, easily testable
  - Returns list of (AlertRule, message) tuples for each triggered rule
  - Caller (scheduler job) handles persistence + notification dispatch
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from app.models.alert import AlertRule

__all__ = ["AlertTrigger", "check_alerts"]

log = logging.getLogger(__name__)


@dataclass
class AlertTrigger:
    """Represents a triggered alert condition."""
    rule_id: int
    symbol: str
    threshold_type: str
    message: str


def check_alerts(
    candles: pd.DataFrame,
    rules: list["AlertRule"],
    rsi_series: pd.Series | None = None,
) -> list[AlertTrigger]:
    """
    Evaluate a list of alert rules against OHLCV candle data.

    Args:
        candles: DataFrame with columns [timestamp, open, high, low, close, volume]
                 ordered oldest-first (same as scanner.py convention).
        rules: List of AlertRule ORM instances to evaluate.
        rsi_series: Optional precomputed RSI series for trend_reversal detection.

    Returns:
        List of AlertTrigger for each rule that fired.
    """
    if candles.empty or len(candles) < 2:
        return []

    triggers: list[AlertTrigger] = []
    latest = candles.iloc[-1]
    prior = candles.iloc[-2]

    latest_close: float = float(latest["close"])
    prior_close: float = float(prior["close"])
    latest_volume: float = float(latest["volume"]) if "volume" in candles.columns else 0.0

    # 20-period average volume (excluding the latest candle to avoid self-reference)
    vol_window = candles["volume"].iloc[:-1].tail(20) if "volume" in candles.columns else pd.Series(dtype=float)
    avg_volume: float = float(vol_window.mean()) if len(vol_window) > 0 else 0.0

    for rule in rules:
        try:
            _evaluate_rule(
                rule=rule,
                latest_close=latest_close,
                prior_close=prior_close,
                latest_volume=latest_volume,
                avg_volume=avg_volume,
                rsi_series=rsi_series,
                triggers=triggers,
            )
        except Exception as exc:
            log.error("check_alerts: error evaluating rule %s for %s: %s", rule.id, rule.symbol, exc)

    return triggers


def _evaluate_rule(
    rule: "AlertRule",
    latest_close: float,
    prior_close: float,
    latest_volume: float,
    avg_volume: float,
    rsi_series: pd.Series | None,
    triggers: list[AlertTrigger],
) -> None:
    """Evaluate a single rule and append to triggers if it fires."""
    threshold = float(rule.threshold_value)

    if rule.threshold_type == "price_spike":
        if prior_close <= 0:
            return
        pct_change = abs((latest_close - prior_close) / prior_close) * 100.0
        if pct_change >= threshold:
            direction = "up" if latest_close > prior_close else "down"
            triggers.append(AlertTrigger(
                rule_id=rule.id,
                symbol=rule.symbol,
                threshold_type="price_spike",
                message=(
                    f"[ALERT] {rule.symbol} price spike {direction}: "
                    f"{pct_change:.2f}% change "
                    f"(close: {latest_close:.4f}, prev: {prior_close:.4f})"
                ),
            ))

    elif rule.threshold_type == "volume_surge":
        if avg_volume <= 0:
            return
        volume_ratio = latest_volume / avg_volume
        if volume_ratio >= threshold:
            triggers.append(AlertTrigger(
                rule_id=rule.id,
                symbol=rule.symbol,
                threshold_type="volume_surge",
                message=(
                    f"[ALERT] {rule.symbol} volume surge: "
                    f"{volume_ratio:.1f}x average "
                    f"(volume: {latest_volume:,.0f}, avg: {avg_volume:,.0f})"
                ),
            ))

    elif rule.threshold_type == "trend_reversal":
        if rsi_series is None or len(rsi_series) < 2:
            return
        rsi_now = float(rsi_series.iloc[-1])
        rsi_prev = float(rsi_series.iloc[-2])
        # Oversold recovery: RSI crosses above 30
        if rsi_prev < 30 and rsi_now >= 30:
            triggers.append(AlertTrigger(
                rule_id=rule.id,
                symbol=rule.symbol,
                threshold_type="trend_reversal",
                message=(
                    f"[ALERT] {rule.symbol} potential trend reversal (bullish): "
                    f"RSI crossed above 30 (RSI={rsi_now:.1f})"
                ),
            ))
        # Overbought reversal: RSI crosses below 70
        elif rsi_prev >= 70 and rsi_now < 70:
            triggers.append(AlertTrigger(
                rule_id=rule.id,
                symbol=rule.symbol,
                threshold_type="trend_reversal",
                message=(
                    f"[ALERT] {rule.symbol} potential trend reversal (bearish): "
                    f"RSI crossed below 70 (RSI={rsi_now:.1f})"
                ),
            ))
