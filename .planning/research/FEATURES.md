# Feature Research

**Domain:** AI Trading Bot (Suggestion-First, Multi-Market)
**Researched:** 2026-04-06
**Confidence:** MEDIUM-HIGH (web-verified against live platforms; some complexity estimates are experience-based)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Users who look at platforms like QuantConnect, Freqtrade, TradingView, and Danelfin expect these features as baseline. Missing any of them causes immediate churn or loss of credibility.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Backtesting engine** | Every serious trading tool has it; users won't trust signals that haven't been validated against history | High | Lookahead-bias-free implementation is the hard part; naive implementations destroy trust. Walk-forward validation is the gold standard. |
| **Paper trading / dry-run simulator** | Bridges backtest to live trading; users refuse to risk real money without it | Medium | Must use real-time market data with simulated order fills. Critically: paper trading catches overfitting that backtesting hides. |
| **Opportunity feed / signal dashboard** | Users need a single view of current suggestions across their watched assets | Medium | Cards or table showing asset, signal type, entry/exit, confidence, and timestamp. Staleness indicators are critical. |
| **Charts with signal overlays** | TradingView has conditioned users to expect annotated price charts | Medium-High | At minimum: candlestick chart + signal entry/exit markers + key indicator overlays. Full charting library (e.g., Lightweight Charts) is sufficient for MVP. |
| **Win rate and performance tracking** | Users need to validate whether the AI's track record is real | Medium | Per-signal win/loss tracking, running accuracy %, drawdown. Must be honest — inflated stats destroy trust fast. |
| **Multi-asset market coverage** | Users compare against tools that already do crypto + stocks; single-market tools feel narrow | High | Crypto is easiest (CoinGecko, free), stocks are medium (yfinance, fragile), forex is medium, options are very hard (no free real-time Greeks/IV). Prioritize crypto + stocks for MVP. |
| **Basic risk context per signal** | Users have been burned by bots with no stop-loss or risk info — they won't use a signal without it | Low-Medium | Entry, stop-loss level, take-profit level, and estimated risk/reward ratio on each suggestion. |
| **Explainability / reasoning per signal** | Black-box signals are the #1 complaint across Reddit, Forex Factory, and product reviews. Danelfin built their entire brand on solving this. | Medium | Show which indicators triggered the signal (RSI oversold, MACD crossover, volume spike, etc.). LLM-generated natural-language summaries are a differentiator but plain indicator labels are table stakes. |

---

### Differentiators (Competitive Advantage)

These features are not expected by default but create strong retention and referrals when done well. They match the project's stated mission of being educational and AI-driven.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Natural-language signal explanations (LLM)** | Competitors (Freqtrade, QuantConnect) show raw numbers. An LLM summary — "RSI crossed below 30 on high volume after a 3-day downtrend, suggesting oversold conditions typical of short-term reversals" — is transformative for beginners. | Medium | Use an LLM API (OpenAI, Anthropic) to generate per-signal narrative summaries. Keep it factual; don't claim certainty. Cache aggressively (signal doesn't change once generated). |
| **AI opportunity scoring with ranked list** | Danelfin's score-1-to-10 model is popular because it reduces decision fatigue. A ranked feed of "best opportunities right now" is far more useful than unordered alerts. | Medium | Score based on signal strength, historical win rate for that pattern, volume confirmation, and trend alignment. |
| **Educational context mode** | No competitor seriously targets beginners with explanation-first design. Freqtrade is for quant developers. QuantConnect requires C# or Python. TradingView requires Pine Script knowledge. A mode that explains concepts as it teaches is a blue ocean. | Medium | Tooltip-style explanations: "What is RSI?" linked from the signal. Concept glossary. "Why did this trade win/lose?" post-mortem on closed signals. |
| **Multi-timeframe signal correlation** | A day-trade signal is more reliable when the daily, 4H, and 1H charts all align. Most beginner tools ignore this. | Medium-High | Show timeframe agreement: "Signal confirmed on 1H and 4H; daily trend is neutral." Increases signal quality dramatically. |
| **Portfolio simulation (paper mode) with visual P&L** | Simulated portfolio with a realistic starting balance, visible P&L curve, and individual trade history turns paper trading into a game. Users stay engaged. | Medium | Show hypothetical portfolio value over time, winning/losing streak, and comparison against a buy-and-hold benchmark. |
| **Strategy transparency (show your work)** | Users trust signals more when they can see the underlying strategy logic — which indicators, which timeframes, what thresholds. Freqtrade hides this in Python files. | Low-Medium | Human-readable strategy description page: "This strategy scans for RSI(14) < 35 + MACD bullish crossover + volume > 1.5x 20-day average." |
| **Market regime awareness** | Signals generated in a ranging market vs. a trending market behave differently. Labeling market regime (trending/ranging/volatile) per signal is a quality signal in itself. | High | Use ADX or similar for trend detection. Show "Signal quality may be lower — choppy market conditions detected." |

---

### Anti-Features (Commonly Requested, Often Problematic)

These are features users will ask for, but building them in MVP creates regulatory, technical, or user-trust problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Auto-execution of live trades** | Users want a hands-off bot | Regulatory gray area (acting as investment advisor); requires brokerage API integration (Alpaca, IBKR); a single bug causes real financial loss; out of explicit scope for MVP | Keep as v2+ behind explicit opt-in with heavy disclaimers. Focus MVP on suggestion quality so users trust the system before giving it execution authority. |
| **Profit guarantees or "win rate" marketing** | Users want assurance it works | Misleading; markets are non-stationary. Win rates from backtests overfit. Displaying inflated win rates destroys trust when live performance differs. | Always show live tracked win rate with confidence intervals. Be explicit: "This is not financial advice." |
| **Real-time tick data for HFT-style signals** | Users want maximum speed | Requires paid data feeds; free sources (yfinance, CoinGecko) update on minute bars at best; sub-second data is expensive. HFT is out of scope. | Use 1-minute and 5-minute candles from free APIs. Be explicit about data latency. |
| **Social copy trading ("copy this trader's portfolio")** | Users want passive income | Regulatory exposure; if a followed trader is wrong, you become liable. Requires complex multi-user position sync. | Leaderboard of best-performing paper portfolios is safe and socializes the platform without execution risk. |
| **Paid signal subscriptions** | Monetization pressure | Creates conflict of interest between signal quality and subscription revenue. Users distrust it. | Monetize through premium features (faster scans, more markets, custom alerts), not signal quality tiers. |
| **Options trading support in MVP** | Users want all 4 markets | Options require real-time Greeks/IV (no free reliable source), understanding of expiry/strike dimensions, and significantly more complex data modeling. Free options data via yfinance is end-of-day only. | Explicitly defer to v2. Prioritize stocks + crypto for MVP where data is reliable and free. |
| **Forex in MVP** | Users want all 4 markets | Forex requires session-aware analysis (London, NY, Asia), macro event calendars, and pip-based P&L calculations. Currency pairs via free APIs (Alpha Vantage free tier: 5 req/min) are rate-limited heavily. | Defer to v1.x. Crypto + stocks give a complete enough MVP story. |

---

## Feature Dependencies

The following dependency chain determines build order:

```
Data ingestion (market data pipelines)
  └── Technical indicator calculation (RSI, MACD, Bollinger, Volume)
        ├── Signal detection engine (pattern matching across timeframes)
        │     ├── Signal scoring (strength, confidence, win rate estimate)
        │     │     └── Opportunity feed / ranked dashboard
        │     │           └── LLM natural-language explanation (per signal)
        │     │
        │     └── Backtesting engine (replay signals against history)
        │           └── Win rate tracking (backtest-validated accuracy)
        │
        └── Paper trading simulator (real-time data + simulated fills)
              └── Portfolio P&L dashboard
                    └── Performance analytics (Sharpe, drawdown, win/loss)

Charts
  └── Signal overlays (entry/exit markers on price chart)
        └── Multi-timeframe view (1H, 4H, 1D correlation panel)
```

Critical path: data ingestion → indicators → signal detection → dashboard. Everything else branches from these.

---

## MVP Definition

### Launch With (v1)

These features form a coherent, self-contained product that delivers the core value proposition: high-quality AI suggestions with clear reasoning for informed decision-making.

1. **Data ingestion**: Crypto (CoinGecko) + Stocks (yfinance). Both free, reliable enough for 1-minute to 1-day candles.
2. **Technical indicator layer**: RSI, MACD, Bollinger Bands, EMA, Volume. These cover 80% of common signal patterns.
3. **Signal detection engine**: Identify opportunities across day-trade (15m-4H) and swing-trade (4H-Daily) timeframes.
4. **Signal reasoning display**: Show which indicators triggered, in plain language. No LLM required for v1 — rule-based templates suffice.
5. **Opportunity feed dashboard**: Ranked list of current signals with asset, direction (long/short), entry, stop-loss, take-profit, confidence score.
6. **Basic chart with signal markers**: Price chart with entry/exit annotations. Use TradingView Lightweight Charts (free, open source).
7. **Backtesting engine**: Replay strategy against 1-3 years of historical data per asset. Must be lookahead-bias-free.
8. **Paper trading simulator**: Live data, simulated fills, fake starting balance ($10k), portfolio P&L tracking.
9. **Win rate dashboard**: Per-strategy accuracy, open vs. closed signals, P&L summary.
10. **Educational tooltips**: Glossary terms linked from signal UI (RSI, MACD, etc.). No separate section needed in v1 — inline is enough.

### Add After Validation (v1.x)

Features to add once MVP proves the signal quality is worth extending:

- LLM-generated natural-language signal summaries (OpenAI or Anthropic API, cached per signal)
- Forex market support (Alpha Vantage or Twelve Data free tier)
- Multi-timeframe confirmation panel (signal quality badge based on 1H/4H/Daily alignment)
- Market regime detection (trending/ranging/volatile label per signal)
- Custom alert thresholds (notify when RSI drops below user-set level on a watched asset)
- Portfolio comparison vs. buy-and-hold benchmark
- Post-mortem explainer on closed trades ("Here's why this signal won/lost")

### Future Consideration (v2+)

Features explicitly deferred in PROJECT.md, confirmed appropriate to defer by research:

- Auto-execution via brokerage API (Alpaca for stocks/crypto, IBKR for multi-asset)
- Options market support (requires paid data: ThetaData, Intrinio, or similar)
- ML model training from scratch (scikit-learn, PyTorch on user-specific historical patterns)
- Mobile push notifications
- Social leaderboard / copy portfolio (paper only, not live)
- Paid data feed integration (Polygon.io, Databento) for institutional-grade signal quality
- High-frequency / sub-minute signal detection

---

## Competitor Feature Analysis

| Feature | QuantConnect | Freqtrade | TradingView | Danelfin | Our Approach |
|---------|-------------|-----------|-------------|----------|--------------|
| **Backtesting** | Yes — event-driven, cloud-scale, realistic fills | Yes — Python-based, FreqAI-aware, walk-forward | Yes — Pine Script Strategy Tester, limited lookback on free tier | No (signal tool, not strategy tester) | Yes — lookahead-bias-free, historical data from free sources |
| **Paper trading** | Yes — full paper trading with live feeds | Yes — dry-run mode with simulated fills | Partial — "Paper trading" requires paid plan | No | Yes — real-time data, simulated fills, visual P&L |
| **Multi-asset** | Yes — stocks, options, forex, futures, crypto | Crypto only (its core strength) | Yes — all markets via data subscriptions | US + European stocks, ETFs only | MVP: crypto + stocks. Forex v1.x. Options v2+. |
| **AI/ML signals** | Yes — Mia AI assistant, Python ML via LEAN | Yes — FreqAI module (sklearn, PyTorch) | No built-in AI; community scripts only | Yes — XAI Score (10k indicators, 1-10 scale) | Yes — rule-based signals in v1; LLM explanations in v1.x |
| **Explainability** | No — code-driven; you understand what you wrote | No — strategy logic is in Python; black box to non-devs | No — Pine Script readable but not explained | Yes — best-in-class: shows which signals contributed | Yes — differentiator; plain-language reason per signal from day one |
| **Win rate tracking** | Yes — backtest stats (Sharpe, drawdown, etc.) | Yes — detailed trade stats | Yes — strategy tester stats | Yes — live historical signal accuracy since 2017 | Yes — live tracked accuracy on all suggestions |
| **Educational features** | None — assumes quant background | None — documentation is for developers | Minimal — Pine Script docs, video tutorials | Minimal — glossary in help docs | Yes — core differentiator; inline explanations built into the UI |
| **Target user** | Professional quants, algo developers | Crypto-native developers | Active traders, chartists | Retail investors wanting stock picks | Beginner-to-intermediate traders wanting AI guidance |
| **Free tier** | Yes — limited cloud compute | Yes — fully open source, self-hosted | Free plan exists; backtesting limited by bars | Yes — limited signals | Yes — free-first, all core features free for MVP |
| **Dashboard/UI quality** | Good for quants; overwhelming for beginners | FreqUI exists but is developer-oriented | Excellent — chart-first, polished | Clean and approachable | Target: TradingView-quality charts + Danelfin-quality signal clarity |

---

## Sources

- Freqtrade official documentation: [freqtrade.io/en/stable](https://www.freqtrade.io/en/stable/) — HIGH confidence
- Freqtrade FreqAI module: [freqtrade.io/en/stable/freqai](https://www.freqtrade.io/en/stable/freqai/) — HIGH confidence
- QuantConnect platform features: [quantconnect.com](https://www.quantconnect.com/) — HIGH confidence
- QuantConnect backtesting docs: [quantconnect.com/docs/v2/cloud-platform/backtesting](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting) — HIGH confidence
- QuantConnect paper trading docs: [quantconnect.com/docs/v2/cloud-platform/live-trading/brokerages/quantconnect-paper-trading](https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/brokerages/quantconnect-paper-trading) — HIGH confidence
- TradingView Pine Script strategies: [tradingview.com/pine-script-docs/concepts/strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/) — HIGH confidence
- Danelfin XAI features and win rate tracking: [danelfin.com/how-it-works](https://danelfin.com/how-it-works) — HIGH confidence
- Danelfin Trade Ideas: [danelfin.com/trade-ideas](https://danelfin.com/trade-ideas) — HIGH confidence
- Backtesting pitfalls (lookahead bias, overfitting): [blockchain-council.org](https://www.blockchain-council.org/cryptocurrency/backtesting-ai-crypto-trading-strategies-avoiding-overfitting-lookahead-bias-data-leakage/) — MEDIUM confidence
- LLM-based trading bot comparison: [flowhunt.io](https://www.flowhunt.io/blog/llm-trading-bots-comparison/) — MEDIUM confidence
- Free finance API comparison 2026: [steadyapi.com](https://steadyapi.com/blogs/top-8-free-financial-data-apis-for-building-a-powerful-stock-portfolio) — MEDIUM confidence
- yfinance (Yahoo Finance wrapper): [github.com/ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) — HIGH confidence (widely used, actively maintained)
- Options data API limitations: [datarade.ai](https://datarade.ai/top-lists/best-option-chain-apis) and [thetadata.net](https://www.thetadata.net/) — MEDIUM confidence
- 3Commas AI trading bot features analysis: [3commas.io/blog/essential-features-of-ai-trading-bots-in-2025-comp](https://3commas.io/blog/essential-features-of-ai-trading-bots-in-2025-comp) — MEDIUM confidence
- Black box trading user concerns: [ccn.com](https://www.ccn.com/education/crypto/ai-crypto-trading-bots-how-they-make-and-lose-millions/) — MEDIUM confidence

---
*Feature research for: AI Trading Bot*
*Researched: 2026-04-06*
