"""
backend/app/analysis/llm_advisor.py
LLM advisory module for signal confidence adjustment.
Pure async function — asks the LLM to review indicator values and suggest
a small confidence adjustment based on pattern recognition.

RELEVANT FILES: app/analysis/signals.py, app/analysis/scanner.py, app/knowledge/base.py
"""
import json
import logging
from dataclasses import dataclass, field

from app.analysis.indicators import IndicatorSet
from app.core.config import settings

__all__ = ["LLMAdvisory", "get_llm_advisory"]

log = logging.getLogger(__name__)


@dataclass
class LLMAdvisory:
    """LLM's advisory adjustment to a signal's confidence score."""
    adjustment: int = 0            # -15 to +15, clamped
    reasoning: str = ""            # 1-2 sentence explanation
    patterns_detected: list[str] = field(default_factory=list)  # e.g. ["bullish divergence", "squeeze breakout"]


_ADVISORY_PROMPT = """You are a quantitative trading analyst. Review these indicator values and the signal direction.
Suggest a small confidence adjustment (-15 to +15) based on patterns you detect.

Asset: {symbol}
Direction: {direction}
Current confidence: {confidence}/100
Regime: {regime}

Indicators:
- RSI(14): {rsi_14}
- MACD: {macd_val} (signal: {macd_signal}, histogram: {macd_hist})
- BB%B: {bb_pct}
- ADX(14): {adx_14}
- ATR(14): {atr_14}
- EMA50: {ema_50}, EMA200: {ema_200}
- Close: {close}

{knowledge_context}

Respond ONLY with valid JSON (no markdown, no backticks):
{{"adjustment": <int -15 to 15>, "reasoning": "<1-2 sentences>", "patterns": ["<pattern1>", "<pattern2>"]}}"""


async def get_llm_advisory(
    ind: IndicatorSet,
    regime: str,
    direction: str,
    confidence: int,
    knowledge_context: str = "",
) -> LLMAdvisory:
    """
    Ask the LLM to review indicator values and suggest a confidence adjustment.

    Returns LLMAdvisory with adjustment clamped to [-15, +15].
    On any failure, returns a neutral advisory (adjustment=0) — never raises.

    Args:
        ind: Computed indicator values for the asset.
        regime: Market regime string (trending/ranging/volatile).
        direction: Current signal direction (BUY/SELL/HOLD).
        confidence: Current confidence score (0-100).
        knowledge_context: Optional knowledge base context string.
    """
    # Guard: return neutral advisory if LLM is disabled
    if not settings.llm_enabled or not settings.openrouter_api_key:
        return LLMAdvisory()

    try:
        from langchain_core.messages import HumanMessage, SystemMessage  # noqa: PLC0415
        from langchain_openai import ChatOpenAI  # noqa: PLC0415

        llm = ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.2,
            max_tokens=200,
            default_headers={
                "HTTP-Referer": settings.frontend_url,
                "X-Title": "Trading Bot",
            },
        )

        # Format indicator values, handling None gracefully
        prompt_text = _ADVISORY_PROMPT.format(
            symbol=ind.symbol,
            direction=direction,
            confidence=confidence,
            regime=regime,
            rsi_14=f"{ind.rsi_14:.1f}" if ind.rsi_14 is not None else "N/A",
            macd_val=f"{ind.macd_val:.4f}" if ind.macd_val is not None else "N/A",
            macd_signal=f"{ind.macd_signal:.4f}" if ind.macd_signal is not None else "N/A",
            macd_hist=f"{ind.macd_hist:.4f}" if ind.macd_hist is not None else "N/A",
            bb_pct=f"{ind.bb_pct:.2f}" if ind.bb_pct is not None else "N/A",
            adx_14=f"{ind.adx_14:.1f}" if ind.adx_14 is not None else "N/A",
            atr_14=f"{ind.atr_14:.4f}" if ind.atr_14 is not None else "N/A",
            ema_50=f"{ind.ema_50:.2f}" if ind.ema_50 is not None else "N/A",
            ema_200=f"{ind.ema_200:.2f}" if ind.ema_200 is not None else "N/A",
            close=f"{ind.close:.2f}",
            knowledge_context=f"Reference knowledge:\n{knowledge_context}" if knowledge_context else "",
        )

        messages = [
            SystemMessage(content="You are a quantitative trading analyst. Always respond with valid JSON only."),
            HumanMessage(content=prompt_text),
        ]

        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        # Parse JSON response — strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            # Remove ```json ... ``` wrapper
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        data = json.loads(content)

        # Validate and clamp the adjustment to [-15, +15]
        adjustment = int(data.get("adjustment", 0))
        adjustment = max(-15, min(15, adjustment))

        reasoning = str(data.get("reasoning", ""))[:200]  # Cap reasoning length
        patterns = data.get("patterns", [])
        if not isinstance(patterns, list):
            patterns = []
        # Ensure all patterns are strings and cap at 5
        patterns = [str(p)[:50] for p in patterns[:5]]

        log.info(
            "get_llm_advisory: %s %s adj=%+d patterns=%s",
            ind.symbol, direction, adjustment, patterns,
        )
        return LLMAdvisory(
            adjustment=adjustment,
            reasoning=reasoning,
            patterns_detected=patterns,
        )

    except Exception as exc:
        log.warning("get_llm_advisory: failed for %s: %s", ind.symbol, exc)
        return LLMAdvisory()
