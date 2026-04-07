# Pitfalls Research

**Domain:** AI Trading Bot
**Researched:** 2026-04-06
**Confidence:** HIGH (multiple verified sources, community consensus, official documentation)

---

## Critical Pitfalls

### Pitfall 1: Look-Ahead Bias in Backtesting

**What goes wrong:**
The backtest uses data that would not have been available at the time the trading decision should have been made. The most common form: using today's closing price to generate a buy signal that executes at today's open. Another form: calculating a moving average that includes the current bar's close before the bar has closed. A third form: applying split/dividend adjustments retroactively to historical prices without accounting for what was actually visible at each point in time.

**Why it happens:**
Vectorized backtesting (operating on full dataframes) makes it trivially easy to accidentally shift data by the wrong number of periods. Developers compute signals with `df['close']` rather than `df['close'].shift(1)`, creating the illusion of perfect prediction. This error is invisible in results — the strategy looks profitable and the developer has no reason to suspect a problem.

**How to avoid:**
- Use an event-driven backtesting framework (Backtrader, Zipline) that processes one bar at a time and enforces chronological access
- If using vectorized backtesting (vectorbt, pandas), rigorously apply `.shift(1)` to all feature columns before signal generation
- Always execute at the OPEN of the next bar, never the CLOSE of the signal bar
- Use walk-forward validation: train on Period A, test on Period B, never let the model see B during training
- Build a "timestamp audit" test: confirm no signal at time T uses any data with timestamp >= T

**Warning signs:**
- Backtest Sharpe ratio above 3 (extremely rare in legitimate strategies)
- Backtest performance is nearly perfect with minimal drawdowns
- Strategy performs dramatically worse in paper trading than backtesting
- Returns are consistent across all market regimes (bull, bear, sideways)

**Phase to address:** Backtesting Engine phase — must be the foundational design constraint, not an afterthought. Do not build the backtesting module without explicitly designing for this.

---

### Pitfall 2: Overfitting / Curve Fitting

**What goes wrong:**
A model (or a rule-based strategy) is tuned to the historical data so precisely that it captures noise rather than genuine signal. The strategy "memorizes" the training period. A 2025 Stanford study found 58% of retail algo-trading models collapse within 3 months due to curve-fitting.

**Why it happens:**
With enough parameters, any model can fit any historical data perfectly. Developers run hundreds of parameter combinations, find the best-performing set, and declare it the strategy — without accounting for the probability that the best result out of N trials is spurious (multiple-hypothesis testing problem). This is sometimes called "p-hacking" or "data snooping."

**How to avoid:**
- Reserve a strict out-of-sample holdout set before any strategy development begins — never touch it until final validation
- Apply walk-forward analysis rather than full-history optimization
- Penalize model complexity (fewer parameters is better, all else equal)
- Require that performance degrades *somewhat* but not *collapses* on out-of-sample data
- For AI/ML signals: use cross-validation with temporal splits (never random splits, which leak future data)
- Limit the number of features in any single model; prefer simple strategies that generalize

**Warning signs:**
- Strategy stops working immediately when tested on the next 6 months of data
- Optimal parameters are highly specific (e.g., "RSI period = 14.37")
- Adding more technical indicators keeps improving backtest performance
- The strategy has never been tested on data from a different market regime

**Phase to address:** Backtesting Engine phase and AI Signal generation phase. The feature engineering for the AI model must be validated on separate data.

---

### Pitfall 3: Survivorship Bias in Historical Data

**What goes wrong:**
Historical datasets for stocks only include companies that still exist today. Companies that went bankrupt, were delisted, or were acquired are absent. A backtest on "the S&P 500" using today's S&P 500 composition is testing a universe of successful companies — the failures were never included. This inflates backtest performance by 1-3% annually on average.

**Why it happens:**
Free data sources (Yahoo Finance, yfinance) provide data for tickers that currently exist. There is no free, easily accessible "point-in-time" constituent list for most indices. Developers don't realize this bias exists until they read about it.

**How to avoid:**
- For the MVP, acknowledge this limitation explicitly in the UI ("Past performance figures may be subject to survivorship bias")
- Avoid backtesting "pick the best stocks from the S&P 500" strategies using current constituents
- For crypto backtesting: use full market history including delisted tokens, not just current top-N by market cap
- Use point-in-time data providers for production (paid feature — defer to v2)

**Warning signs:**
- "Buy and hold the top 20 S&P stocks" strategy shows implausibly high returns
- Historical backtests on crypto use only coins that are still trading today

**Phase to address:** Backtesting Engine phase — document the limitation, add a disclaimer to the UI, and design the data ingestion layer to record which assets were in-universe at each date.

---

### Pitfall 4: Ignoring Transaction Costs and Slippage

**What goes wrong:**
Backtests assume trades execute at the exact signal price with zero cost. In reality, every trade has: (1) commission/fee, (2) bid-ask spread cost, (3) market impact (moving the price against yourself), and (4) slippage from delayed execution. Research shows ignoring these can slash reported returns by more than 50%.

**Why it happens:**
It's easier to build a backtester that ignores costs, and the costs feel small per trade. But a strategy that trades frequently (day trading) can have these costs compound enormously. A 0.1% round-trip cost on 100 trades/month is 10%/month in costs alone.

**How to avoid:**
- Build transaction cost modeling into the backtesting engine from day one: configurable commission rate, configurable slippage model
- Default slippage model: assume fills at the worse of bid or ask, not the midpoint
- For stocks: add 0.01-0.05% per side for liquid names; 0.1-0.3% for illiquid
- For crypto: add the exchange fee (typically 0.1-0.25% per trade) plus spread
- For high-frequency signals: add market impact proportional to order size vs. daily volume
- Display estimated net-of-costs return prominently in the UI, not gross return

**Warning signs:**
- Backtest assumes fills at exact close price with no spread
- Strategy's "edge" per trade is smaller than 0.2% (easily consumed by realistic costs)
- Strategy generates many small trades (each incurring full cost)
- Paper trading result significantly exceeds live-equivalent result

**Phase to address:** Backtesting Engine phase. Must be built into the cost model before any strategy is evaluated.

---

### Pitfall 5: yfinance and Free Data Source Unreliability

**What goes wrong:**
yfinance is not an official API — it is a scraper of Yahoo Finance HTML and endpoints. As of 2025, Yahoo has significantly tightened rate limits. Users regularly receive 429 "Too Many Requests" errors. The library breaks whenever Yahoo changes its page structure (multiple breaking changes per year, tracked in active GitHub issues). For continuous data ingestion (needed for real-time scanning), yfinance is fundamentally unsuitable.

**Why it happens:**
yfinance is popular, easy to use, and free. Developers use it for prototyping and then attempt to use it in production. The failure mode is non-obvious: data appears to work fine at low query rates, then silently fails or returns stale data under any sustained load.

**How to avoid:**
- Use yfinance only for historical OHLCV data in the backtesting engine (batch, not continuous)
- For real-time/near-real-time market scanning: use Finnhub free tier (requires API key, proper rate limiting, more stable) or Alpha Vantage free tier
- For crypto: use CoinGecko free Demo plan (30 calls/min, 10,000 calls/month — plan data pipeline around this cap)
- Build a caching layer around all free data sources: cache responses for the maximum reasonable TTL to avoid re-requesting the same data
- Design the data layer with provider abstraction so the source can be swapped without touching strategy code
- CoinGecko public (no key): only 5-15 calls/minute — insufficient for multi-coin scanning; get a Demo API key

**Warning signs:**
- Data pipeline has no retry/backoff logic
- Application makes data calls directly without a caching layer
- Using yfinance in a polling loop with intervals shorter than 60 seconds
- No health monitoring on data freshness

**Phase to address:** Data Ingestion phase (Phase 1). The architecture decision to abstract data providers must be made before the first line of strategy code.

---

### Pitfall 6: Paper Trading Does Not Equal Live Trading

**What goes wrong:**
Paper trading assumes perfect execution at the signal price. Live trading introduces: partial fills, slippage, delayed execution, and spread costs. A 2025 Alpaca Markets study found paper trading overestimates performance by 15-30%. Option Alpha community data shows paper bots close at mid-prices 90% of the time; live bots only 60% of the time.

**Why it happens:**
Paper trading simulators are optimistic by design — they want users to feel success before committing real money. The gap is invisible until real execution is attempted.

**How to avoid:**
- Label the paper trading simulator prominently as a simulation with known optimism bias
- Add configurable "realism penalty" to the paper trading engine: random fill delay (0-2 seconds), slippage offset (configurable %), partial fill simulation
- Track and display the paper-to-live gap metric for users who have both paper and live experience
- In the educational layer, explain why paper results are consistently better than live

**Warning signs:**
- Paper trading simulator fills all orders at exact signal price
- No spread or slippage is modeled in paper trades
- Users report "it worked in paper trading but not in live" — this is expected, not a bug

**Phase to address:** Paper Trading Simulator phase. Design the simulator with realistic execution from the start.

---

### Pitfall 7: Options and Forex Are Fundamentally More Complex Than Stocks/Crypto

**What goes wrong:**
Options require: strike selection, expiry selection, Greeks (Delta, Gamma, Theta, Vega) computation, IV skew modeling, and proper pricing models (Black-Scholes is the minimum; more sophisticated models are needed for accuracy). Free APIs do not provide Greeks or IV — developers must compute them, which requires a separate interest rate feed and significant domain expertise. Forex requires: pip sizing, spread modeling per broker, leverage risk management, and 24/5 data feeds. Neither options nor forex has reliable free real-time data at production quality.

**Why it happens:**
The project goal is all 4 markets. Developers often underestimate the delta in complexity between equities/crypto and options/forex. An options "opportunity" suggestion without proper Greeks context is misleading or dangerous for inexperienced users.

**How to avoid:**
- MVP should prioritize stocks and crypto only
- Forex: can be added in Phase 2 using Finnhub's forex data (free tier)
- Options: defer to v2 with a dedicated "options complexity" research spike before building
- If options are included in MVP: limit to basic covered calls / cash-secured puts with educational explanations, and clearly label as "simplified analysis"
- Never surface options suggestions without displaying Delta, Theta, and break-even price

**Warning signs:**
- Options strategy logic uses only price, ignoring IV and time decay
- Forex implementation ignores spread modeling
- "Options backtesting" uses stock price data without modeling the options chain

**Phase to address:** Market scope decision must be made in planning. Recommend stocks + crypto for MVP, forex as Phase 2, options as Phase 3+.

---

### Pitfall 8: AI Signal Hallucination and Overconfidence

**What goes wrong:**
LLMs used for market analysis or signal generation can hallucinate data, fabricate earnings figures, invent regulatory announcements, and misread sarcasm in social sentiment. In 2023, a finance LLM provided a false SEC regulatory update; in another case, AI-generated stock summaries included clinical trial results that didn't exist. A bot using LLM-generated signals left unmonitored for 48 hours in a volatile environment is "almost guaranteed to hit its Stop Loss."

**Why it happens:**
LLMs generate statistically plausible text — they cannot distinguish real market data from invented data. When asked about a specific stock, the model may confidently provide accurate-seeming but fabricated information.

**How to avoid:**
- Never let LLM output be the direct source of numerical data (prices, earnings, dates) — always ground these in verified API data
- Use LLMs only for reasoning about data already retrieved from verified sources ("given these confirmed indicators, what patterns do you see?")
- Display clear disclaimers: "AI analysis is based on pattern recognition, not financial advice"
- Implement a "grounding check": if the LLM cites a specific price or date, verify it against the live data feed before displaying it
- Log and periodically audit AI reasoning outputs for factual accuracy
- The educational explanations (why a signal was generated) should be templated from actual indicator values, not free-form LLM generation

**Warning signs:**
- LLM is given a stock ticker and asked "what should I do?" without first feeding it verified current data
- AI explanations reference specific numbers that weren't explicitly provided to the model
- No human-readable audit trail of what data the AI was given vs. what it generated

**Phase to address:** AI Signal Engine phase. The data grounding architecture must be designed before LLM integration.

---

### Pitfall 9: Set-and-Forget Mentality / Lack of Monitoring

**What goes wrong:**
73% of automated crypto trading accounts fail within six months, with a primary cause being insufficient monitoring. Markets change regime (trending vs. ranging, high volatility vs. low). A strategy optimized for trending markets will lose money in a ranging market. Without monitoring, a bot silently destroys capital.

**Why it happens:**
The appeal of algorithmic trading is passive automation. Developers build the bot, watch it work for a week, then walk away. The bot has no concept of "current market regime is outside training distribution."

**How to avoid:**
- Build alerting into the dashboard: notify when win rate drops below a threshold over a rolling window
- Display "data freshness" prominently — if the bot is running on stale data, it should be obvious
- Implement a circuit breaker: if the suggestion engine hasn't been confirmed accurate in N days, flag it
- For the MVP, the suggestions-only model is actually safer here — the user must manually execute, providing a human review step
- Add a "regime indicator" to the dashboard (e.g., VIX level, trend strength) to give users context about current conditions

**Warning signs:**
- Dashboard has no data freshness indicator
- No alerting when performance metrics degrade
- No concept of "strategy health" — just raw suggestions without context

**Phase to address:** Dashboard and Win Rate Tracking phase.

---

### Pitfall 10: Over-Engineering the Strategy Before Validating the Core Loop

**What goes wrong:**
Developers build complex multi-indicator, multi-market, multi-timeframe strategies before validating that any single simple strategy works end-to-end. The result is a system too complex to debug, with no baseline to compare against.

**Why it happens:**
The vision is compelling (AI scanning all 4 markets across all timeframes). It is tempting to build for the full vision immediately. But each added dimension (market, timeframe, indicator) multiplies complexity and makes it impossible to isolate what is and isn't working.

**How to avoid:**
- Start with one market (recommend crypto for 24/7 data availability and no access restrictions)
- Start with one timeframe (daily for swing trading — simpler to validate)
- Start with one simple signal type (e.g., RSI divergence or moving average crossover)
- Get the full loop working: data in -> signal generated -> backtest validates signal -> paper trade confirms signal quality
- Add complexity only after the simple loop is validated and deployed

**Warning signs:**
- Planning document describes 6 different signal types before the first one has been tested
- Architecture includes all 4 markets in the MVP scope
- "We'll add all the signals and then backtest them all at once"

**Phase to address:** MVP scoping and Phase 1 design.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using yfinance for continuous polling | Fast to implement | Rate limit failures in production; unexplained data gaps | Acceptable for batch historical fetches only; never for real-time |
| Skipping transaction cost modeling in backtester | Simpler code | All backtest results are overstated; users build false confidence | Never acceptable — add cost model in first version |
| Hardcoding strategy parameters | Faster to ship one strategy | Cannot tune without code changes; makes A/B testing impossible | Acceptable in early prototyping only; externalize before user-facing |
| Storing API keys in .env files committed to git | Convenient | Key exposure leads to account theft / data theft | Never — use secrets manager or gitignored env files from day one |
| Vectorized backtest without shift() | Easier pandas code | Silent look-ahead bias poisons all results | Never acceptable — shift() is one line |
| Building all 4 markets simultaneously | Feels comprehensive | Quadruples debugging surface area; delays validation of anything | Unacceptable — serialize markets, ship one first |
| Using LLM to generate signal reasoning without grounding | Impressive demo output | AI hallucinations present as factual analysis | Never for production — always ground in verified data |
| Paper trading with perfect fills | Simple to implement | Users experience false confidence, then fail in live | Acceptable for v1 if prominently labeled; add realism in v2 |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| yfinance | Using in a polling loop; no error handling for 429s | Cache aggressively; use only for batch historical fetch; implement exponential backoff |
| CoinGecko free tier | Not registering for Demo API key (5-15 req/min) vs. key (30 req/min) | Always register for Demo key; cache all responses; build a rate limiter |
| Finnhub free tier | Exceeding 60 API calls/minute on free plan | Use a token bucket rate limiter; cache responses; batch requests |
| Alpha Vantage free tier | 25 requests/day limit on free tier | Cache all historical data locally; do not re-fetch what you already have |
| Yahoo Finance scraping | Page structure changes break data parsing silently | Use library wrappers that are actively maintained; monitor data freshness |
| LLM APIs (OpenAI, Anthropic) | Treating LLM output as factual market data | Always inject verified data into the prompt; never ask the LLM to recall market facts |
| WebSocket price feeds | Not handling disconnects / reconnects | Implement heartbeat monitoring and automatic reconnection with state recovery |
| CoinGecko rate limits | Burst requests on startup (fetching all coins at once) | Stagger requests across time; maintain a local cache updated on a schedule |

---

## Performance Traps

**Database query patterns for time-series data**
Storing OHLCV data in a general-purpose relational DB (e.g., PostgreSQL) with naive queries will become slow as history accumulates. For time-series data, prefer TimescaleDB (PostgreSQL extension) or InfluxDB. If using raw PostgreSQL, partition tables by date and create a composite index on (symbol, timestamp).

**Backtesting on large datasets in Python loops**
Row-by-row iteration over years of minute data in Python is prohibitively slow. Use vectorbt (vectorized, numpy-backed) for performance, or use Backtrader with data chunking. Expect: 1 year of daily stock data = fast; 1 year of 1-minute crypto data = needs vectorized processing.

**AI model inference latency in the signal loop**
If the signal scanner calls an LLM API for every ticker on every scan cycle, latency compounds quickly. 100 tickers x 2 second LLM call = 200 seconds per scan cycle. Design the AI layer to: (1) use pre-computed technical indicators as fast filters, (2) call the LLM only for top-N candidates that pass rule-based filters, (3) cache LLM analysis for a configurable TTL.

**Real-time price feed vs. polling**
Polling Yahoo Finance every 30 seconds for 50 stocks will hit rate limits. Use WebSocket feeds (Finnhub, Alpaca market data) for real-time prices where available; poll only for data that doesn't have a WebSocket API.

---

## Security Mistakes

**API key exposure**
The most common security failure is committing API keys to git repositories. Keys for exchange accounts (Alpaca, Coinbase) act as a remote control for the account. Prevention: use `python-dotenv` with a `.env` file that is in `.gitignore` from repository initialization. Never hardcode secrets in source files.

**Exchange API key permissions**
If connecting to any exchange (even paper trading), request only the minimum required permissions. For a suggestions-only bot, no trade execution permission should ever be requested — only market data read permission.

**No rate-limit protection on the web dashboard API**
If the dashboard is exposed to the internet, the backend API endpoints (especially backtest triggers and market scan triggers) must have rate limiting to prevent resource exhaustion attacks.

**User data and PII**
If user accounts are added, apply proper password hashing (bcrypt/argon2), session management, and never store raw passwords.

---

## UX Pitfalls

**Presenting AI confidence without calibration**
Displaying "87% confidence" or "HIGH conviction" without a statistical basis creates false trust. Users will assume these numbers are meaningful probabilities. Prevention: only display win rate percentages that are derived from actual historical performance of similar signals, not model output scores.

**Win rate gambler's fallacy**
Research shows that when users see a "streak" of correct predictions, they over-trust the next prediction (hot-hand fallacy). Conversely, after a streak of losses, they under-trust even valid signals (gambler's fallacy). Prevention: display confidence intervals on win rates, not just point estimates. Show sample size ("Based on 47 similar past signals"). Warn users when sample size is too small for reliable statistics.

**Information overload on first use**
A user with no trading experience (the stated target user) who sees 20 indicators, 4 market tabs, and 6 signal types on their first visit will be overwhelmed and not understand what to do. Prevention: design a progressive disclosure UX. Start with 1-3 "top opportunities" prominently. Let users drill down for details. Teach indicator meanings in context, not up front.

**Suggestion without explanation**
Surfacing a buy/sell signal without explaining which indicators triggered it and what the thesis is produces distrust and no learning. The educational mission requires clear reasoning chains: "RSI is oversold at 28 on AAPL daily. This has historically been followed by a rebound in 68% of similar setups over the past 3 years. Entry: $X, Stop: $Y, Target: $Z."

**Backtesting result presentation without disclaimers**
Showing backtest results without prominent survivorship bias and look-ahead bias disclaimers could lead users to over-trust historical performance figures.

---

## "Looks Done But Isn't" Checklist

Before considering any module production-ready, verify:

**Data Ingestion**
- [ ] All API integrations have rate limiting and exponential backoff
- [ ] Caching layer is in place with configurable TTL per data type
- [ ] Data freshness is displayed in the UI with staleness alerts
- [ ] Provider abstraction layer allows swapping sources without touching strategy code
- [ ] API keys are in environment variables, never in source code

**Backtesting Engine**
- [ ] Transaction costs (commission + slippage) are modeled with configurable parameters
- [ ] Signals use `shift(1)` or equivalent temporal offset — no look-ahead
- [ ] All fills execute at next-bar open, not signal-bar close
- [ ] Survivorship bias disclaimer is displayed on all backtest result pages
- [ ] Walk-forward validation is available (not just full-history optimization)
- [ ] Results display net-of-cost returns, not gross returns

**AI Signal Engine**
- [ ] LLM reasoning is grounded in verified data explicitly injected into the prompt
- [ ] No LLM output is used as a source of numerical fact without verification
- [ ] All AI explanations trace back to specific indicator values in the data
- [ ] Educational explanation includes which indicators triggered and their historical context

**Paper Trading Simulator**
- [ ] Fills include configurable slippage and spread modeling
- [ ] Simulator is clearly labeled as simulation
- [ ] Performance metrics display a "simulated (may overestimate live performance)" label

**Dashboard and Win Rate Tracking**
- [ ] Win rates display sample size alongside the percentage
- [ ] Short-sample win rates are flagged as statistically unreliable (n < 30)
- [ ] Confidence intervals are shown on win rate metrics
- [ ] Performance degradation triggers an alert, not just a silent drop in numbers

---

## Sources

- [Why Most Backtests Fail: Overfitting, Look-Ahead Bias, and Data Snooping — Frontier Ledger](https://frontierledger.ai/foundations-core-concepts/why-most-backtests-fail-overfitting-look-ahead-bias-and-data-snooping)
- [Common Pitfalls in Backtesting: A Comprehensive Guide for Algorithmic Traders — Medium / Funny AI & Quant](https://medium.com/funny-ai-quant/ai-algorithmic-trading-common-pitfalls-in-backtesting-a-comprehensive-guide-for-algorithmic-ce97e1b1f7f7)
- [Backtesting Traps: Common Errors to Avoid — LuxAlgo](https://www.luxalgo.com/blog/backtesting-traps-common-errors-to-avoid/)
- [Stop Faking Your Results: The Most Common Backtesting Pitfalls — Medium / Algorithmic and Quantitative Trading](https://medium.com/algorithmic-and-quantitative-trading/stop-faking-your-results-the-most-common-backtesting-pitfalls-to-avoid-f8dd94d1ca8e)
- [Backtesting Bias: Feels Good, Until You Blow Up — Robot Wealth](https://robotwealth.com/backtesting-bias-feels-good-until-you-blow-up/)
- [Why yfinance Keeps Getting Blocked, and What to Use Instead — Medium / Trading Dude](https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01)
- [yfinance YFRateLimitError: Too Many Requests — GitHub Issue #2422](https://github.com/ranaroussi/yfinance/issues/2422)
- [CoinGecko API Rate Limit Documentation](https://support.coingecko.com/hc/en-us/articles/4538771776153-What-is-the-rate-limit-for-CoinGecko-API-public-plan)
- [Why Your Crypto Bot Keeps Failing: The Data Quality Problem — DEV Community](https://dev.to/paarthurnax_3f967358857ce/why-your-crypto-bot-keeps-failing-the-data-quality-problem-and-how-to-fix-it-a25)
- [Why Most Crypto Trading Bots Fail — DEV Community](https://dev.to/matrixtrak/why-most-crypto-trading-bots-fail-and-how-to-build-one-that-actually-works-257g)
- [Paper Trading vs. Live Trading: Key Differences — TraderPost](https://blog.traderspost.io/article/paper-trading-vs-live-trading-key-differences-and-what-to-expect)
- [Paper vs Live Bots: Execution Differences Exposed — PickMyTrade](https://blog.pickmytrade.trade/paper-vs-live-bots-execution-differences/)
- [Paper Trading vs. Live Trading Data-Backed Guide — Alpaca Markets](https://alpaca.markets/learn/paper-trading-vs-live-trading-a-data-backed-guide-on-when-to-start-trading-real-money)
- [AI Hallucinations in Finance: When Models Lie About the Market — Blueberry Fund](https://theblueberryfund.com/blogs/news/ai-hallucinations-in-finance-when-models-lie-about-the-market)
- [TradeTrap: Are LLM-based Trading Agents Truly Reliable and Faithful? — arXiv](https://arxiv.org/html/2512.02261v1)
- [Customer Advisory: AI Won't Turn Trading Bots into Money Machines — CFTC](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/AITradingBots.html)
- [11 N00b Mistakes I Made with Crypto Trading Bots — HackerNoon](https://hackernoon.com/11-n00b-mistakes-i-made-with-crypto-trading-bots-a-tale-of-lessons-learned-the-hard-way)
- [Options Chain API: Free Data Does Not Include Greeks — FlashAlpha Research](https://flashalpha.com/articles/options-chain-api-real-time-greeks-open-interest)
- [Understanding Differences in IV and Greeks Between Platforms — MarketData.app](https://www.marketdata.app/education/options/differences-in-iv-greeks/)
- [The Hot-Hand Fallacy and Gambler's Fallacy in Trading — Capital.com](https://capital.com/en-int/learn/trading-psychology/fallacies-in-trading)
- [Is AI Trading Legal? The 2026 Verdict — AdvancedAutoTrades](https://advancedautotrades.com/is-trading-with-ai-legal/)
- [AI Trading Agent Vulnerability 2026: $45M Crypto Security Breach — KuCoin](https://www.kucoin.com/blog/en-ai-trading-agent-vulnerability-2026-how-a-45m-crypto-security-breach-exposed-protocol-risks)
- [Why Most Trading Bots Lose Money — ForTraders](https://www.fortraders.com/blog/trading-bots-lose-money)

---
*Pitfalls research for: AI Trading Bot*
*Researched: 2026-04-06*
