# Trading Strategies Guide

## Momentum Trading
Momentum strategies profit from assets continuing in their current direction. Buy assets with rising prices and strong indicators; sell when momentum fades.

Key signals for momentum:
- RSI between 50-70 (bullish momentum without overbought)
- MACD above signal line and rising
- ADX > 25 (confirming trend exists)
- Price above EMA(50)
- Volume surge confirming the move

## Mean Reversion
Mean reversion assumes prices tend to return to their average. Buy when price is significantly below average; sell when above.

Key signals for mean reversion:
- RSI below 30 (deeply oversold)
- BB%B below 0.1 (price at or below lower Bollinger Band)
- ADX < 20 (no strong trend, range-bound)
- Price far from EMA(50) — likely to revert

**Warning**: Mean reversion fails in strong trends. Check ADX first.

## Breakout Trading
Breakout strategies enter when price breaks through support/resistance levels with conviction.

Breakout confirmation:
- Price breaks above previous high or below previous low
- Volume surge (> 1.5x average) on the breakout candle
- Bollinger Band squeeze preceding the breakout (narrow bands)
- ADX rising from below 20 to above 25

## Trend Following
Trend following rides established trends. Enter in the direction of the trend; exit when the trend reverses.

Trend following rules:
- Only buy when EMA(50) > EMA(200) (golden cross territory)
- Only sell when EMA(50) < EMA(200) (death cross territory)
- Use ADX > 25 to confirm trend strength
- Trail stop-loss using ATR (e.g., 2x ATR below current price)

## Multi-Timeframe Analysis
Checking signals across multiple timeframes increases conviction. A BUY signal on 1D + 4H + 1H is stronger than one timeframe alone. The bot computes multi-timeframe agreement and flags when all timeframes align.
