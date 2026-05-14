"""
Rule-based weighted confluence signal scorer.

Pure function: takes IndicatorSet, returns SignalResult.
No DB access — testable without any infrastructure.

Scoring weights (total possible: 100):
  RSI extreme:    25 pts  (< 35 oversold / > 65 overbought)
  MACD direction: 30 pts  (line vs signal line)
  BB position:    25 pts  (< 0.2 near lower / > 0.8 near upper)
  Volume surge:   10 pts  (volume > 1.5x SMA, amplifies leading direction)
  EMA trend:      10 pts  (close vs EMA50)

Direction threshold: >= 55 pts AND strictly greater than opposite direction.
"""
from dataclasses import dataclass, field
from typing import Literal

from app.analysis.indicators import IndicatorSet

__all__ = ["SignalResult", "score_signal"]


@dataclass
class SignalResult:
    """Result of rule-based confluence scoring for one asset."""
    direction: Literal["BUY", "SELL", "HOLD"]
    confidence: int             # 0-100, clamped
    entry_price: float
    stop_loss: float | None     # None for SELL and HOLD
    target_price: float | None  # None for SELL and HOLD
    reasons: list[str] = field(default_factory=list)
    # LLM advisory fields — populated when LLM is enabled
    llm_adjustment: int = 0              # -15 to +15 confidence adjustment
    llm_reasoning: str = ""              # LLM's 1-2 sentence explanation
    llm_patterns: list[str] = field(default_factory=list)  # Detected patterns


THRESHOLD = 55  # Minimum score for a directional signal


def score_signal(ind: IndicatorSet) -> SignalResult:
    """
    Compute a BUY/SELL/HOLD signal with confidence from an IndicatorSet.

    All None fields in ind are handled gracefully — the component is simply
    skipped (no points awarded or deducted).
    """
    bull_score = 0
    bear_score = 0
    reasons: list[str] = []

    # RSI (25 pts)
    if ind.rsi_14 is not None:
        if ind.rsi_14 < 35:
            bull_score += 25
            reasons.append(f"RSI oversold ({ind.rsi_14:.1f})")
        elif ind.rsi_14 > 65:
            bear_score += 25
            reasons.append(f"RSI overbought ({ind.rsi_14:.1f})")

    # MACD (30 pts)
    if ind.macd_val is not None and ind.macd_signal is not None:
        if ind.macd_val > ind.macd_signal:
            bull_score += 30
            reasons.append("MACD above signal line")
        else:
            bear_score += 30
            reasons.append("MACD below signal line")

    # Bollinger Band position (25 pts)
    if ind.bb_pct is not None:
        if ind.bb_pct < 0.2:
            bull_score += 25
            reasons.append(f"Price near lower BB ({ind.bb_pct:.2f})")
        elif ind.bb_pct > 0.8:
            bear_score += 25
            reasons.append(f"Price near upper BB ({ind.bb_pct:.2f})")

    # Volume surge (10 pts) — guard against zero vol_sma_20 (CoinGecko)
    if (
        ind.vol_sma_20 is not None
        and ind.vol_sma_20 > 0
        and ind.volume > ind.vol_sma_20 * 1.5
    ):
        if bull_score >= bear_score:
            bull_score += 10
        else:
            bear_score += 10
        reasons.append(f"Volume surge ({ind.volume / ind.vol_sma_20:.1f}x avg)")

    # EMA50 trend alignment (10 pts)
    if ind.ema_50 is not None:
        if ind.close > ind.ema_50:
            bull_score += 10
            reasons.append("Price above EMA50")
        else:
            bear_score += 10
            reasons.append("Price below EMA50")

    # ATR-based stop-loss and target (only for BUY)
    stop_loss = None
    target_price = None
    if ind.atr_14 is not None:
        stop_loss = ind.close - 2 * ind.atr_14
        target_price = ind.close + 3 * ind.atr_14  # 1.5:1 reward:risk

    if bull_score >= THRESHOLD and bull_score > bear_score:
        return SignalResult(
            direction="BUY",
            confidence=min(bull_score, 100),
            entry_price=ind.close,
            stop_loss=stop_loss,
            target_price=target_price,
            reasons=reasons,
        )
    elif bear_score >= THRESHOLD and bear_score > bull_score:
        return SignalResult(
            direction="SELL",
            confidence=min(bear_score, 100),
            entry_price=ind.close,
            stop_loss=None,
            target_price=None,
            reasons=reasons,
        )
    else:
        return SignalResult(
            direction="HOLD",
            confidence=min(max(bull_score, bear_score), 100),
            entry_price=ind.close,
            stop_loss=None,
            target_price=None,
            reasons=reasons,
        )


def apply_llm_advisory(signal: SignalResult, advisory) -> SignalResult:
    """
    Apply LLM advisory adjustment to a signal's confidence score.

    The adjustment is added to confidence, clamped to [0, 100].
    If the adjusted confidence crosses the THRESHOLD boundary, the direction
    may change (e.g., BUY with confidence dropping below 55 becomes HOLD).

    Args:
        signal: Original SignalResult from score_signal().
        advisory: LLMAdvisory dataclass with adjustment, reasoning, patterns.

    Returns:
        New SignalResult with adjusted confidence and LLM fields populated.
    """
    if advisory.adjustment == 0 and not advisory.reasoning:
        # No advisory — return signal as-is with empty LLM fields
        return signal

    adjusted_confidence = max(0, min(100, signal.confidence + advisory.adjustment))

    # Re-check direction threshold — if confidence drops below THRESHOLD, switch to HOLD
    direction = signal.direction
    if direction in ("BUY", "SELL") and adjusted_confidence < THRESHOLD:
        direction = "HOLD"

    return SignalResult(
        direction=direction,
        confidence=adjusted_confidence,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss if direction == "BUY" else None,
        target_price=signal.target_price if direction == "BUY" else None,
        reasons=signal.reasons,
        llm_adjustment=advisory.adjustment,
        llm_reasoning=advisory.reasoning,
        llm_patterns=advisory.patterns_detected,
    )
