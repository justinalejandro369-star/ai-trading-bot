"""
Trading concept explanations dictionary.

Each entry keyed by slug (URL-safe) with plain-language definitions
suited for new traders. Used by GET /api/education/concepts endpoints.
"""
from __future__ import annotations

__all__ = ["CONCEPTS", "get_concept"]

CONCEPTS: dict[str, dict] = {
    "rsi": {
        "slug": "rsi",
        "name": "RSI (Relative Strength Index)",
        "short": "Momentum oscillator measuring speed and change of price movements.",
        "explanation": (
            "RSI measures how quickly prices are rising or falling on a scale of 0 to 100. "
            "A reading above 70 suggests the asset may be overbought — it has risen too fast "
            "and could pull back. A reading below 30 suggests oversold conditions — the asset "
            "may have fallen too far and could bounce. Values between 30 and 70 are neutral."
        ),
        "thresholds": {"oversold": 30, "overbought": 70},
        "how_we_use_it": (
            "Our scanner adds a BUY signal weight when RSI is below 35 (potential recovery) "
            "and a SELL weight when RSI is above 65 (potential reversal). RSI is one of "
            "several indicators combined into a confidence score."
        ),
        "category": "momentum",
    },
    "macd": {
        "slug": "macd",
        "name": "MACD (Moving Average Convergence Divergence)",
        "short": "Trend-following indicator showing momentum and direction changes.",
        "explanation": (
            "MACD compares two exponential moving averages (12-period and 26-period) to "
            "reveal changes in momentum, direction, and duration of a trend. "
            "The MACD line crossing above the Signal line is a bullish signal. "
            "The histogram shows the distance between MACD and Signal — growing bars "
            "indicate strengthening momentum."
        ),
        "thresholds": {},
        "how_we_use_it": (
            "A positive MACD value (MACD line above zero) contributes to BUY confidence. "
            "A negative MACD value contributes to SELL confidence. Signal line crossovers "
            "are the primary trigger for trend-reversal alerts."
        ),
        "category": "trend",
    },
    "bollinger-bands": {
        "slug": "bollinger-bands",
        "name": "Bollinger Bands",
        "short": "Volatility bands placed above and below a moving average.",
        "explanation": (
            "Bollinger Bands consist of a 20-period simple moving average (the middle band) "
            "plus upper and lower bands set 2 standard deviations away. "
            "When price touches the upper band the asset may be overbought; touching the "
            "lower band may signal oversold. A 'squeeze' (bands narrowing) often precedes "
            "a large price move — direction unknown until breakout."
        ),
        "thresholds": {"std_devs": 2, "period": 20},
        "how_we_use_it": (
            "Price closing below the lower band adds BUY weight (potential reversion). "
            "Price closing above the upper band adds SELL weight. Band width is used in "
            "regime detection — narrow bands indicate a ranging market."
        ),
        "category": "volatility",
    },
    "adx": {
        "slug": "adx",
        "name": "ADX (Average Directional Index)",
        "short": "Measures trend strength without indicating direction.",
        "explanation": (
            "ADX ranges from 0 to 100. Values below 20 indicate a weak or absent trend "
            "(ranging market). Values above 25 indicate a strong trend — either up or down. "
            "Values above 40 signal a very strong trend. ADX does NOT tell you whether the "
            "trend is bullish or bearish — combine it with directional indicators like MACD."
        ),
        "thresholds": {"weak_trend": 20, "strong_trend": 25, "very_strong": 40},
        "how_we_use_it": (
            "ADX above 25 boosts confidence for any directional signal (BUY or SELL). "
            "ADX below 20 reduces confidence — signals in ranging markets have lower "
            "win rates. Regime detection uses ADX to label assets as 'trending' vs 'ranging'."
        ),
        "category": "trend",
    },
    "atr": {
        "slug": "atr",
        "name": "ATR (Average True Range)",
        "short": "Measures market volatility as the average price range per candle.",
        "explanation": (
            "ATR calculates the average of the true price range (high minus low, accounting "
            "for gaps) over 14 periods. A rising ATR means increasing volatility. "
            "ATR itself is not directional — a high ATR can occur in both bull and bear markets. "
            "It is primarily used for position sizing and setting stop-loss distances."
        ),
        "thresholds": {},
        "how_we_use_it": (
            "Stop-loss levels in our signals are set at entry_price ± 1.5× ATR, giving "
            "enough room to avoid being stopped out by normal volatility. ATR SMA is used "
            "in regime detection to classify assets as 'volatile' vs 'trending'."
        ),
        "category": "volatility",
    },
    "sharpe-ratio": {
        "slug": "sharpe-ratio",
        "name": "Sharpe Ratio",
        "short": "Risk-adjusted return — how much return per unit of risk.",
        "explanation": (
            "The Sharpe ratio divides a strategy's excess return (above the risk-free rate) "
            "by its standard deviation of returns. A Sharpe above 1.0 is considered good; "
            "above 2.0 is excellent; below 0 means the strategy underperforms cash. "
            "Higher is better — it rewards consistent returns and penalizes wild swings."
        ),
        "thresholds": {"poor": 0, "acceptable": 1.0, "good": 2.0},
        "how_we_use_it": (
            "Backtest results display the Sharpe ratio alongside win rate and max drawdown. "
            "A strategy with a high win rate but low Sharpe may be taking on excessive risk. "
            "Use Sharpe to compare strategies on an equal risk-adjusted footing."
        ),
        "category": "performance",
    },
}


def get_concept(slug: str) -> dict | None:
    """Return concept dict by slug, or None if not found."""
    return CONCEPTS.get(slug)
