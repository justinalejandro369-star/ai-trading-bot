# Bot Internals

## Signal Scoring System
The bot uses a weighted confluence scoring system. Each indicator contributes points to a bull or bear score:

| Component | Max Points | Bullish Condition | Bearish Condition |
|-----------|-----------|-------------------|-------------------|
| RSI(14) | 25 | RSI < 35 (oversold) | RSI > 65 (overbought) |
| MACD | 30 | MACD above signal line | MACD below signal line |
| Bollinger Band | 25 | BB%B < 0.2 (near lower) | BB%B > 0.8 (near upper) |
| Volume surge | 10 | Volume > 1.5x SMA (amplifies leading direction) | Same |
| EMA50 trend | 10 | Price above EMA(50) | Price below EMA(50) |

Total possible: 100 points. A directional signal (BUY or SELL) requires >= 55 points AND the winning direction must be strictly greater than the opposite.

## How Signals Are Generated
1. The scanner fetches the latest 220 candles for each asset
2. Technical indicators are computed (RSI, MACD, BB, ADX, ATR, EMA)
3. The confluence scorer assigns points to bull/bear directions
4. Market regime is detected (trending/ranging/volatile)
5. If LLM is enabled, an AI explanation is generated grounding in exact values
6. Signal is upserted to the database (always refreshed on each scan)

## Data Sources
- **Stocks**: Yahoo Finance (yfinance) — updated every 5 minutes
- **Crypto**: CoinGecko (4H candles, top-5 coins) + CCXT/Binance (OHLCV)
- **Forex**: Alpha Vantage (daily, optional)
- **Live ticks**: Finnhub WebSocket for real-time price updates

## Stop-Loss and Target Calculation
For BUY signals, the bot calculates:
- **Stop-loss** = Entry price - 2 * ATR(14) — gives breathing room for normal volatility
- **Target** = Entry price + 3 * ATR(14) — 1.5:1 reward-to-risk ratio

SELL and HOLD signals don't include stop-loss/target (no long entry recommended).

## LLM Explanations
When enabled, the AI generates plain-language explanations for each signal. The explanation is grounded in exact indicator values — the AI is instructed to cite only the numbers provided (no hallucination). This helps users understand WHY a signal was generated without needing to read raw numbers.

## Multi-Timeframe Agreement
The bot checks if signals on different timeframes (1H, 4H, 1D) align. When multiple timeframes agree on the same direction, the signal has higher conviction. The "Aligned" badge appears when all available timeframes agree.
