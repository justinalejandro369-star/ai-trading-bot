# Market Concepts

## Market Regimes
Markets cycle through three regimes:
- **Trending**: ADX > 25, clear directional movement. Trend-following and momentum strategies excel.
- **Ranging**: ADX < 25, price oscillates in a band. Mean reversion strategies work best.
- **Volatile**: ADX > 25 AND ATR > 1.2x its 20-period SMA. High risk — wider stops needed, smaller position sizes.

The bot automatically detects the regime and factors it into signal generation.

## Risk Management
The most important factor in trading profitability is risk management, not signal accuracy.

Core principles:
- **Position sizing**: Never risk more than 1-2% of account on a single trade
- **Stop-losses**: Always use them. The bot uses 2x ATR for volatility-adjusted stops
- **Risk-reward ratio**: The bot targets 1.5:1 (target = 3x ATR, stop = 2x ATR)
- **Diversification**: Don't concentrate in one asset or sector
- **Drawdown limits**: Consider pausing trading if drawdown exceeds 10-15%

## Position Sizing
Calculate position size based on risk tolerance:
- Position size = (Account risk per trade) / (Entry price - Stop loss)
- Example: $10,000 account, 1% risk = $100 risk per trade
- If stop-loss is $2 below entry: position = $100 / $2 = 50 shares

## Confidence Score Interpretation
The bot's confidence score (0-100) reflects how many technical indicators agree:
- **80-100**: Strong confluence — multiple indicators align (rare but high conviction)
- **55-79**: Moderate confluence — enough agreement for a directional signal
- **Below 55**: Insufficient confluence — HOLD signal issued
- Higher confidence doesn't guarantee profit — it means more indicators agree

## Paper Trading
Paper trading simulates real trading with virtual money. Use it to:
- Validate signal accuracy before risking real capital
- Test different strategies without financial risk
- Build confidence in the system's signals
- Track win rate and drawdown over time

## Backtesting
Backtesting applies trading rules to historical data. Key metrics:
- **Sharpe ratio**: Risk-adjusted return (> 1.0 is good, > 2.0 is excellent)
- **Max drawdown**: Worst peak-to-trough decline (lower is better)
- **Win rate**: Percentage of profitable trades (> 50% with good risk-reward is solid)
- **Profit factor**: Gross profit / gross loss (> 1.5 is good)

**Caution**: Past performance doesn't guarantee future results. Overfitting to historical data is a common trap.
