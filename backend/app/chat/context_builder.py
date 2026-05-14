"""
backend/app/chat/context_builder.py
Builds system prompts for the chatbot based on the active dashboard tab.
Pure function — no DB, no FastAPI imports. Fully testable in isolation.

RELEVANT FILES: app/chat/engine.py, app/api/routes/chat.py, app/knowledge/base.py
"""
from app.knowledge.base import get_relevant_context

__all__ = ["build_system_prompt"]

_BASE_PERSONA = """You are a knowledgeable trading assistant for an AI-powered trading bot. You help users understand:
- Trading signals and their technical indicators (RSI, MACD, Bollinger Bands, ADX, ATR, EMA)
- Market regimes (trending, ranging, volatile) and what strategies work in each
- Backtesting results and what the metrics mean
- Paper trading portfolio performance
- Risk management and position sizing

Be concise, informative, and reference specific numbers when available. No financial advice disclaimers — the user understands this is an educational tool. Keep responses under 200 words unless the question requires more detail."""

# Per-tab context templates that inject relevant page data into the system prompt
_TAB_CONTEXTS = {
    "chart": """The user is viewing the price chart for {symbol}. Recent close: ${close}. Help them understand price action, chart patterns, and what the technical indicators suggest for this asset.""",
    "signals": """The user is viewing the trading signals feed. Current signals data:
{signals_summary}
Help them understand why these signals were generated, what the confidence scores mean, and how to interpret the indicators.""",
    "portfolio": """The user is viewing their paper trading portfolio.
{portfolio_summary}
Help them understand their positions, P&L, and suggest risk management improvements.""",
    "backtest": """The user is viewing backtesting results.
{backtest_summary}
Help them understand what the metrics mean (Sharpe ratio, max drawdown, win rate, profit factor) and how to improve their strategy.""",
    "education": """The user is on the education/learning tab. Answer their trading questions with educational depth. Use the knowledge base to provide accurate, helpful explanations.""",
}


def build_system_prompt(
    active_tab: str,
    page_context: dict,
    user_message: str,
) -> str:
    """
    Build a complete system prompt from base persona + tab context + knowledge.

    Args:
        active_tab: Current dashboard tab (chart, signals, portfolio, backtest, education).
        page_context: Dict with tab-specific data (symbol, signals, portfolio, etc.).
        user_message: The user's question — used for knowledge base keyword extraction.

    Returns:
        Complete system prompt string ready for LLM.
    """
    parts = [_BASE_PERSONA]

    # Add tab-specific context
    tab_template = _TAB_CONTEXTS.get(active_tab, "")
    if tab_template:
        # Build summary strings from page_context for each tab type
        context_vars = _extract_context_vars(active_tab, page_context)
        try:
            tab_context = tab_template.format(**context_vars)
            parts.append(tab_context)
        except (KeyError, ValueError):
            pass  # Skip tab context if formatting fails

    # Add relevant knowledge from the knowledge base
    # Extract keywords from the user message for context lookup
    keywords = _extract_keywords(user_message)
    knowledge = get_relevant_context(keywords, max_chars=2000)
    if knowledge:
        parts.append(f"Reference knowledge:\n{knowledge}")

    return "\n\n".join(parts)


def _extract_context_vars(active_tab: str, page_context: dict) -> dict:
    """Extract template variables from page_context based on active tab."""
    if active_tab == "chart":
        return {
            "symbol": page_context.get("symbol", "unknown"),
            "close": page_context.get("close", "N/A"),
        }
    elif active_tab == "signals":
        signals = page_context.get("signals", [])
        if signals:
            lines = []
            for s in signals[:5]:  # Limit to top 5 signals
                lines.append(
                    f"- {s.get('symbol', '?')}: {s.get('direction', '?')} "
                    f"(confidence {s.get('confidence', '?')}%, regime: {s.get('regime', '?')})"
                )
            summary = "\n".join(lines)
        else:
            summary = "No active signals."
        return {"signals_summary": summary}
    elif active_tab == "portfolio":
        portfolio = page_context.get("portfolio", {})
        positions = portfolio.get("open_positions", [])
        pos_lines = [
            f"- {p.get('symbol', '?')}: {p.get('quantity', 0)} shares @ ${p.get('avg_entry_price', 0):.2f}"
            for p in positions[:5]
        ]
        summary = (
            f"Cash: ${portfolio.get('cash_balance', 0):,.2f}\n"
            f"Total equity: ${portfolio.get('total_equity', 0):,.2f}\n"
            f"Positions:\n" + ("\n".join(pos_lines) if pos_lines else "No open positions")
        )
        return {"portfolio_summary": summary}
    elif active_tab == "backtest":
        bt = page_context.get("backtest", {})
        if bt:
            summary = (
                f"Sharpe ratio: {bt.get('sharpe_ratio', 'N/A')}\n"
                f"Max drawdown: {bt.get('max_drawdown', 'N/A')}\n"
                f"Win rate: {bt.get('win_rate', 'N/A')}\n"
                f"Profit factor: {bt.get('profit_factor', 'N/A')}\n"
                f"Total return: {bt.get('total_return', 'N/A')}\n"
                f"Total trades: {bt.get('total_trades', 'N/A')}"
            )
        else:
            summary = "No backtest results available."
        return {"backtest_summary": summary}
    return {}


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from user message for knowledge base lookup."""
    # Split on spaces and common delimiters, filter short/common words
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "what", "why", "how",
        "when", "where", "which", "who", "this", "that", "these", "those",
        "do", "does", "did", "can", "could", "would", "should", "will",
        "my", "your", "its", "our", "their", "it", "i", "me", "we", "you",
        "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
        "about", "from", "up", "down", "out", "off", "over", "under",
        "not", "no", "so", "if", "than", "too", "very", "just", "also",
    }
    words = text.lower().replace("?", "").replace("!", "").replace(",", "").split()
    return [w for w in words if len(w) > 2 and w not in stop_words]
