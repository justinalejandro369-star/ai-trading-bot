"""
LLM-powered signal explanation generator.

Generates plain-language explanations for trading signals, grounding each
explanation in actual IndicatorSet values — no hallucinated numbers.

Design:
  - Gracefully disabled when llm_enabled=False or openrouter_api_key="" (no key)
  - Uses LangChain PromptTemplate + ChatOpenAI pointed at OpenRouter
  - Explanation is cached on the signal row — no duplicate LLM calls per signal
  - try/except guard prevents LangChain import errors when disabled

Usage:
  from app.analysis.explainer import generate_explanation
  explanation = await generate_explanation(signal_row, ind)
"""
import logging

from app.analysis.indicators import IndicatorSet
from app.core.config import settings

__all__ = ["generate_explanation"]

log = logging.getLogger(__name__)

# Template string — uses actual indicator values, zero hallucination risk
_EXPLANATION_TEMPLATE = """You are a concise trading assistant. Explain this {direction} signal for {symbol} in 2-3 sentences.
Use ONLY these exact verified indicator values — do not invent any other numbers.

Verified data:
- RSI(14): {rsi_14} {rsi_note}
- MACD: {macd_status}
- Bollinger Band position: {bb_pct} (0=lower band, 1=upper band)
- ATR(14): {atr_14} ({atr_pct_note}% of price)
- ADX(14): {adx_14} (trend strength, >25 = trending)
- Price vs EMA50: {ema_note}
- Confidence score: {confidence}/100
- Signal reasons: {reasons}

{knowledge_context}

Write a plain-language explanation citing the specific numbers above. Be direct and informative. No disclaimers."""


def _build_prompt_values(
    symbol: str,
    direction: str,
    confidence: int,
    ind: IndicatorSet,
    reasons: list[str],
    knowledge_context: str = "",
) -> dict:
    """Build template substitution dict from verified indicator values."""
    rsi_14 = f"{ind.rsi_14:.1f}" if ind.rsi_14 is not None else "N/A"
    rsi_note = ""
    if ind.rsi_14 is not None:
        if ind.rsi_14 < 35:
            rsi_note = "(oversold < 35)"
        elif ind.rsi_14 > 65:
            rsi_note = "(overbought > 65)"

    macd_status = "N/A"
    if ind.macd_val is not None and ind.macd_signal is not None:
        rel = "above" if ind.macd_val > ind.macd_signal else "below"
        macd_status = f"MACD {ind.macd_val:.4f} is {rel} signal line {ind.macd_signal:.4f}"

    bb_pct = f"{ind.bb_pct:.2f}" if ind.bb_pct is not None else "N/A"

    atr_14 = f"{ind.atr_14:.4f}" if ind.atr_14 is not None else "N/A"
    atr_pct_note = "N/A"
    if ind.atr_14 is not None and ind.close > 0:
        atr_pct_note = f"{(ind.atr_14 / ind.close * 100):.1f}"

    adx_14 = f"{ind.adx_14:.1f}" if ind.adx_14 is not None else "N/A"

    ema_note = "N/A"
    if ind.ema_50 is not None:
        rel = "above" if ind.close > ind.ema_50 else "below"
        ema_note = f"Price {ind.close:.2f} is {rel} EMA50 {ind.ema_50:.2f}"

    return {
        "symbol": symbol,
        "direction": direction,
        "confidence": confidence,
        "rsi_14": rsi_14,
        "rsi_note": rsi_note,
        "macd_status": macd_status,
        "bb_pct": bb_pct,
        "atr_14": atr_14,
        "atr_pct_note": atr_pct_note,
        "adx_14": adx_14,
        "ema_note": ema_note,
        "reasons": "; ".join(reasons) if reasons else "none",
        "knowledge_context": knowledge_context,
    }


async def generate_explanation(
    symbol: str,
    direction: str,
    confidence: int,
    ind: IndicatorSet,
    reasons: list[str],
) -> str:
    """
    Generate a plain-language LLM explanation for a trading signal.

    Grounded in actual IndicatorSet values — the prompt contains only verified
    numbers and the LLM is instructed not to invent others.

    Gracefully disabled when:
      - settings.llm_enabled is False
      - settings.openrouter_api_key is empty string

    In either disabled case, returns "" immediately with no LangChain import error.

    Args:
        symbol: Asset symbol (e.g. "AAPL")
        direction: "BUY" | "SELL" | "HOLD"
        confidence: Signal confidence score 0-100
        ind: IndicatorSet with actual computed values
        reasons: List of human-readable reasons from score_signal()

    Returns:
        Plain-language explanation string, or "" if LLM disabled or error.
    """
    try:
        if not settings.llm_enabled or not settings.openrouter_api_key:
            log.debug("generate_explanation: LLM disabled or no API key — returning empty")
            return ""

        # Deferred imports — no ImportError if langchain-openai not installed when llm_enabled=False
        from langchain_core.prompts import PromptTemplate  # noqa: PLC0415
        from langchain_openai import ChatOpenAI  # noqa: PLC0415

        # Fetch relevant knowledge context based on signal reasons
        knowledge_context = ""
        try:
            from app.knowledge.base import get_relevant_context  # noqa: PLC0415
            # Extract keywords from reasons for knowledge lookup
            keywords = [r.split("(")[0].strip().lower() for r in reasons if r]
            knowledge_context = get_relevant_context(keywords, max_chars=2000)
            if knowledge_context:
                knowledge_context = f"Reference knowledge:\n{knowledge_context}"
        except ImportError:
            pass  # Knowledge base module not available — proceed without it

        prompt_values = _build_prompt_values(
            symbol, direction, confidence, ind, reasons, knowledge_context
        )

        prompt = PromptTemplate(
            input_variables=list(prompt_values.keys()),
            template=_EXPLANATION_TEMPLATE,
        )

        # OpenRouter-compatible: ChatOpenAI accepts base_url to redirect to any OpenAI-compatible API
        llm = ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.3,
            max_tokens=200,
            default_headers={
                "HTTP-Referer": settings.frontend_url,
                "X-Title": "Trading Bot",
            },
        )

        chain = prompt | llm
        response = await chain.ainvoke(prompt_values)

        # ChatOpenAI returns an AIMessage; extract content string
        explanation = response.content if hasattr(response, "content") else str(response)
        log.info("generate_explanation: generated for %s (%d chars)", symbol, len(explanation))
        return explanation.strip()

    except Exception as exc:
        log.warning("generate_explanation: failed for %s: %s", symbol, exc)
        return ""
