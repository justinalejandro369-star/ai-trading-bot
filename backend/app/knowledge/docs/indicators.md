# Technical Indicators Guide

## RSI (Relative Strength Index)
RSI measures momentum on a 0-100 scale. RSI below 30 indicates oversold conditions (potential buying opportunity). RSI above 70 indicates overbought conditions (potential selling pressure). The trading bot uses RSI(14) with thresholds at 35 (oversold) and 65 (overbought) for signal scoring.

Key RSI strategies:
- **Divergence**: Price makes new low but RSI makes higher low = bullish divergence
- **Centerline crossover**: RSI crossing above 50 confirms bullish momentum
- **Failure swing**: RSI fails to break previous high/low = trend reversal signal

## MACD (Moving Average Convergence Divergence)
MACD uses two EMAs (12 and 26 period) and a signal line (9-period EMA of MACD). When MACD crosses above the signal line, it's a bullish signal. When it crosses below, it's bearish. The histogram (MACD - signal) shows momentum strength.

Key MACD patterns:
- **Bullish crossover**: MACD crosses above signal line (momentum shifting up)
- **Bearish crossover**: MACD crosses below signal line (momentum shifting down)
- **Zero line cross**: MACD crossing zero indicates trend change
- **Divergence**: Price and MACD moving in opposite directions suggests reversal

## Bollinger Bands
Bollinger Bands consist of a 20-period SMA with upper and lower bands at 2 standard deviations. BB%B (Band Position) measures where price sits: 0 = at lower band, 1 = at upper band. The bot uses BB%B < 0.2 as oversold and > 0.8 as overbought.

Key BB strategies:
- **Squeeze**: Bands narrowing = low volatility, potential breakout coming
- **Walk the band**: Price staying near upper/lower band = strong trend
- **Mean reversion**: Price returning to middle band from extremes

## ADX (Average Directional Index)
ADX measures trend strength on a 0-100 scale. ADX > 25 indicates a trending market. ADX < 20 indicates a ranging/sideways market. ADX does not indicate trend direction — only strength.

Interpretation:
- 0-20: Weak or no trend (range-bound, mean reversion strategies work better)
- 20-40: Developing trend (trend-following strategies start to work)
- 40-60: Strong trend (ride the trend, avoid counter-trend trades)
- 60+: Extremely strong trend (rare, possible exhaustion)

## ATR (Average True Range)
ATR measures volatility as the average of true ranges over 14 periods. It is used for position sizing, stop-loss placement, and regime detection. The bot places stop-losses at 2x ATR below entry and targets at 3x ATR above entry (1.5:1 reward:risk ratio).

ATR applications:
- **Stop-loss**: Entry price - 2 * ATR(14) gives a volatility-adjusted stop
- **Position sizing**: Smaller positions when ATR is high (more volatile)
- **Regime detection**: ATR > 1.2x its 20-period SMA = volatile regime

## EMA (Exponential Moving Average)
EMA gives more weight to recent prices than SMA. The bot uses EMA(50) for medium-term trend and EMA(200) for long-term trend. Price above EMA(50) = bullish trend alignment. The "golden cross" (EMA50 crossing above EMA200) is a strong bullish signal.

## Volume Analysis
Volume confirms price moves. A price breakout on high volume is more reliable. The bot flags volume > 1.5x the 20-period SMA as a "volume surge" which amplifies the leading signal direction.
