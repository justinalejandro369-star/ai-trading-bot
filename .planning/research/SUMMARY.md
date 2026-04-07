# Project Research Summary

**Project:** AI Trading Bot
**Domain:** AI-powered trading assistant
**Researched:** 2026-04-06
**Confidence:** MEDIUM

## Executive Summary

This is a suggestion-first algorithmic trading assistant: a system that ingests market data, runs technical analysis, generates AI-annotated signals, and presents ranked opportunities through a web dashboard — without auto-executing trades. Research across Freqtrade, QuantConnect, TradingView, and Danelfin confirms that the domain is well-understood and mature. The recommended approach is a Python-first backend (FastAPI + Celery + Redis) with a React dashboard, using free-tier data sources (Finnhub for real-time stocks, CoinGecko for crypto, yfinance for batch historical data), and a vectorized backtesting engine (vectorbt). For MVP, the stack is proven and the build order is clear: data ingestion must come first, everything else depends on it.

The highest-value differentiator is explainability combined with educational context. No major competitor (Freqtrade, QuantConnect) seriously targets beginners with explanation-first design — this is a genuine blue ocean. For MVP, signal reasoning should come from rule-based templates grounded in verified indicator values; LLM-generated natural-language explanations are a powerful upgrade for v1.x once the signal pipeline is validated. The AI layer should use LLMs only for reasoning about pre-verified data, never as a source of numerical market facts, to avoid the well-documented hallucination risks in finance AI.

The most dangerous pitfalls are all in the backtesting engine: look-ahead bias, overfitting, ignoring transaction costs, and survivorship bias can make any strategy appear profitable in testing while failing live. These must be designed-in from the start — a `shift(1)` guardrail, next-bar execution fills, and configurable cost modeling are non-negotiable. The second major risk category is data source fragility: yfinance is unsuitable for continuous polling and must be restricted to batch historical fetches. Markets should be serialized in the MVP (stocks first, then crypto) rather than built in parallel, which would quadruple debugging surface area before the core loop is validated.

---

## Key Findings

### Recommended Stack

The Python finance/ML ecosystem makes Python-first the only sensible backend choice. FastAPI (0.115+) provides async REST and native WebSocket support for real-time signal push. Celery (5.4+) with Redis (7.2+) handles scheduled market scans, async backtests, and rate-limited API fetching without blocking the web tier. For MVP, APScheduler in-process is sufficient and avoids Celery's operational overhead until scale demands it. SQLite is acceptable for local/single-user dev; PostgreSQL 16+ (with TimescaleDB extension for time-series OHLCV hypertables) is required for production. The frontend is React 18 + Vite (not Next.js — this is an authenticated SPA, no SEO required), TradingView Lightweight Charts for candlestick rendering, TanStack Query for server state, and Zustand for local dashboard state.

Data sources carry the most uncertainty: yfinance is an unofficial scraper that breaks under sustained load. Finnhub (60 calls/min free) is the right source for real-time stock prices; CoinGecko Demo plan (10,000 calls/month) covers crypto. Alpha Vantage (500 req/day) fills gaps. The LLM layer should use OpenAI gpt-4o-mini for production (cheap, capable financial reasoning) and be designed with an OpenAI-compatible interface abstraction so Ollama can run locally at zero cost.

**Core technologies:**
- Python 3.11 + FastAPI: backend runtime and API — async-first, native WebSocket, Pydantic validation
- Celery + Redis: background task queue for scheduled scans and async backtests
- vectorbt: backtesting engine — vectorized, handles years of minute-level data in seconds
- pandas + pandas-ta: data manipulation and 150+ technical indicators, no C compilation required
- LangChain + OpenAI gpt-4o-mini: LLM orchestration and signal explanation generation
- React 18 + Vite + TypeScript: authenticated SPA dashboard, sub-second HMR
- TradingView Lightweight Charts: free, MIT, renders 100k+ bars; industry standard for web trading UI
- SQLAlchemy 2.0 + Alembic: ORM with async support and schema versioning
- Docker + Docker Compose: single-command environment reproducibility

**Avoid:** Zipline (dead ecosystem), yfinance for real-time polling, Streamlit for the dashboard, Node.js backend, Redux, Chart.js/D3 for OHLCV.

### Expected Features

Research confirms users arriving from TradingView, Danelfin, and Freqtrade expect a clear baseline. The black-box complaint is the #1 signal quality issue across Reddit, Forex Factory, and product reviews — signal reasoning is table stakes, not a differentiator. The critical build path is linear: data ingestion → indicators → signal detection → dashboard; paper trading and backtesting branch from this core.

**Must have (table stakes):**
- Backtesting engine — users will not trust signals that haven't been validated against history
- Paper trading / dry-run simulator — users refuse to risk real money without it
- Opportunity feed / signal dashboard — ranked list with asset, direction, entry/exit, confidence, timestamp
- Charts with signal overlays — candlestick chart with entry/exit markers and indicator overlays
- Win rate and performance tracking — honest live-tracked accuracy, not inflated backtested stats
- Basic risk context per signal — entry, stop-loss, take-profit, and risk/reward ratio
- Signal reasoning / explainability — which indicators triggered, in plain language

**Should have (competitive differentiators):**
- Natural-language signal explanations (LLM-generated, grounded in verified data) — beginners find raw indicator values opaque
- AI opportunity scoring with ranked list — reduces decision fatigue; Danelfin's 1-10 score model is validated
- Educational context mode — inline glossary, concept explanations, "why did this win/lose" post-mortems
- Multi-timeframe signal correlation — signals confirmed on 1H + 4H + Daily are materially more reliable
- Portfolio simulation with visual P&L — running equity curve vs. buy-and-hold benchmark
- Strategy transparency page — human-readable description of signal logic and thresholds

**Defer (v2+):**
- Auto-execution via brokerage API (Alpaca, IBKR) — regulatory gray area, financial risk, out of MVP scope
- Options market support — requires paid data for Greeks/IV; free yfinance options data is end-of-day only
- ML model training from scratch — validate signal quality first before building custom models
- Mobile push notifications
- Social leaderboard / copy portfolio (paper only)
- High-frequency / sub-minute signal detection

**Forex:** Defer to v1.x; Alpha Vantage free tier is too rate-limited for intraday forex; scope to daily/swing if included.

### Architecture Approach

The system is a layered pipeline with strict dependency order: data ingestion writes normalized OHLCV to a time-series database, the analysis engine reads from the DB to compute indicators and generate signals, the backtesting and paper trading engines share the analysis layer's logic through a common interface, and the FastAPI layer exposes REST + WebSocket to the React dashboard. The key architectural principle is a normalizer between all data sources and the strategy layer: signal generator code must never parse raw API responses, only canonical OHLCV schema. This makes sources swappable without touching strategy code.

For MVP at single-user scale: one Python process with APScheduler, SQLite or PostgreSQL, no Celery, no Redis. Add distributed infrastructure only when measured scale demands it.

**Major components:**
1. Data Ingestion — polls free APIs on schedule, normalizes all sources to common OHLCV schema, persists to DB
2. Feature Builder — computes RSI, MACD, Bollinger Bands, EMA, Volume from raw OHLCV (pandas-ta)
3. Signal Generator — applies rule-based logic (or ML classifier) to produce BUY/SELL/HOLD with score and reasoning text
4. Backtesting Engine — vectorized replay of historical data; never calls external APIs; enforces shift(1) and next-bar execution
5. Paper Trading Simulator — uses live data with simulated fills; separate code path from backtesting (no shared live=True flag)
6. FastAPI API Layer — REST endpoints + WebSocket broadcaster for signal events only (not every price tick)
7. React Dashboard — opportunity feed, candlestick charts with overlays, paper portfolio, analytics, educational tooltips

### Critical Pitfalls

1. **Look-ahead bias in backtesting** — always `shift(1)` signal columns before generating trade decisions; execute at next-bar open, never signal-bar close; build a timestamp audit test confirming no signal at time T uses data with timestamp >= T
2. **Overfitting / curve fitting** — reserve a strict out-of-sample holdout before any development begins; use walk-forward validation; start with simple, explainable rule-based strategies before adding ML overlays
3. **yfinance for real-time polling** — restrict yfinance to batch historical fetches only; use Finnhub WebSocket for live stock prices; design a provider abstraction layer so sources are swappable
4. **AI signal hallucination** — LLMs must never be the source of numerical market data; inject only verified, pre-fetched indicator values into prompts; ground all AI explanations in specific confirmed indicator values
5. **Over-engineering before validating the core loop** — start with one market (crypto recommended for 24/7 availability), one timeframe (daily), one signal type; validate the full loop end-to-end before adding markets, timeframes, or signal types

---

## Implications for Roadmap

Based on research, the architecture has strict dependency ordering that should directly map to roadmap phases. Building out of order produces unmockable interfaces. Complexity should be added serially, not in parallel.

### Phase 1: Data Foundation
**Rationale:** Everything in the system reads from the data layer. No other component can be built or tested without stored, normalized OHLCV data. This is the single most critical phase to get right.
**Delivers:** Working data pipeline for stocks (yfinance batch) + crypto (CoinGecko), normalized OHLCV in SQLite/PostgreSQL with TimescaleDB, APScheduler-driven polling, provider abstraction layer, rate limiting and caching, data freshness indicators.
**Addresses:** Multi-market data ingestion requirement; free-sources-only constraint.
**Avoids:** yfinance fragility (rate limits, polling misuse); API key exposure; missing caching layer.

### Phase 2: Analysis Engine
**Rationale:** Signal generation is the core value proposition. It must be built on top of clean stored data, not raw API calls. Rule-based signals must come before LLM explanation — validate the signal logic first.
**Delivers:** Technical indicator calculation (RSI, MACD, Bollinger Bands, EMA, Volume via pandas-ta), rule-based signal detection across day-trade and swing-trade timeframes, signal scoring and confidence estimation, basic rule-based reasoning text (template-driven, not LLM).
**Addresses:** AI-powered market scanning, suggestion engine with entry/exit/reasoning.
**Avoids:** Coupling signal logic to data source format; LLM hallucination (rule-based templates come first); over-engineering before validating the core loop.

### Phase 3: Backtesting Engine
**Rationale:** Users will not trust signals that have not been validated against history. Backtesting must come before paper trading so there is a baseline to compare against. Look-ahead bias safeguards must be foundational, not bolted on.
**Delivers:** Vectorized backtest runner (vectorbt), configurable transaction cost model (commission + slippage), shift(1) enforcement, next-bar execution fills, walk-forward validation, Sharpe/win-rate/max-drawdown metrics, survivorship bias disclaimer on results pages.
**Addresses:** Backtesting engine requirement; win rate tracking.
**Avoids:** Look-ahead bias; overfitting; ignoring transaction costs; survivorship bias; calling live APIs during backtest.

### Phase 4: Paper Trading Simulator
**Rationale:** Bridges the gap between validated backtests and live decision-making. Shares signal logic from Phase 2 via a common interface but has a completely separate code path from the backtesting engine.
**Delivers:** Simulated order fills against live market data, fake portfolio state with $10k starting balance, configurable slippage/spread model, P&L tracking, win rate on paper trades, prominent "simulation — may overestimate live performance" labeling.
**Addresses:** Paper trading simulator requirement; portfolio tracking.
**Avoids:** Mixing backtesting and paper trading code paths (no shared live=True flag); perfect-fill optimism bias (add configurable realism penalty).

### Phase 5: API and Dashboard
**Rationale:** The API and frontend can begin in parallel with Phase 4 once Phase 2 signal contracts are defined. The dashboard delivers the user-facing value: charts, opportunity feed, analytics, and educational context. This is where the product becomes tangible.
**Delivers:** FastAPI REST + WebSocket (signal events only — not every price tick), React + Vite dashboard, TradingView Lightweight Charts with signal overlays, ranked opportunity feed, paper portfolio view, win rate analytics, educational tooltips and inline indicator glossary.
**Addresses:** Web dashboard, charts with signal overlays, educational context, win rate tracking.
**Avoids:** Real-time WebSocket for all data (overkill; use WebSocket for signal events, REST for chart data); information overload on first use (progressive disclosure UX); presenting confidence scores without statistical grounding.

### Phase 6: LLM Signal Explanations
**Rationale:** LLM explanations are a powerful differentiator but depend on validated signal logic from Phase 2. Add LLM narrative summaries only after the rule-based signal pipeline is confirmed accurate — this prevents the LLM from explaining signals that don't work.
**Delivers:** LangChain-orchestrated LLM calls (OpenAI gpt-4o-mini or Ollama for local dev), grounded natural-language signal summaries injected with pre-verified indicator values, cached per signal (LLM is not called on re-fetch), grounding check that verifies any numbers cited by LLM against live data, audit log of AI inputs vs. outputs.
**Addresses:** Natural-language signal explanations differentiator; educational mission.
**Avoids:** LLM hallucination (data grounding is mandatory); LLM inference latency in signal loop (call LLM only for top-N candidates that pass rule-based filter; cache results).

### Phase 7: Market Expansion
**Rationale:** Once the full loop is validated on stocks + crypto, the ingestion abstraction from Phase 1 makes adding new markets low-risk. Forex and additional crypto sources can be added without touching strategy or API code.
**Delivers:** Forex support via Alpha Vantage (daily/swing timeframes only — free tier too rate-limited for intraday), expanded crypto coverage via CCXT (100+ exchanges), Finnhub WebSocket for real-time stock prices, multi-timeframe signal correlation panel.
**Addresses:** Multi-market coverage goal.
**Avoids:** Forex intraday on free APIs (rate limits make it unreliable); options in MVP (defer to v2+ due to Greeks/IV complexity and paid data requirement).

### Phase Ordering Rationale

- Data must precede analysis: the signal engine has nothing to process without stored, normalized OHLCV.
- Analysis must precede backtesting and paper trading: both depend on the same signal logic.
- Backtesting must precede paper trading: establishes baseline signal quality before real-time simulation begins.
- API and dashboard can start in parallel with Phase 4 once Phase 2 signal schemas are locked.
- LLM explanations come after signal validation: explaining a bad signal with fluent prose is worse than no explanation.
- Market expansion comes last: the ingestion abstraction from Phase 1 makes it low-effort once the core is stable.
- Start with one market, one timeframe, one signal type — the core loop must be end-to-end before expanding.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Backtesting Engine):** Walk-forward validation implementation in vectorbt has sparse documentation; needs dedicated research before building. Cost modeling for different asset classes (stocks vs. crypto fee structures) needs specific values.
- **Phase 6 (LLM Explanations):** Prompt engineering for financial reasoning and grounding architecture needs prototyping. LangChain agent design for data injection patterns is not standardized.
- **Phase 7 (Market Expansion — Forex):** Alpha Vantage free tier rate limits for daily FX are adequate, but the specific API endpoints and session-awareness requirements need validation before building.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Data Foundation):** yfinance batch usage, CoinGecko API, and APScheduler are well-documented. Provider abstraction pattern is standard.
- **Phase 2 (Analysis Engine):** pandas-ta indicator computation is straightforward and well-documented. Rule-based signal generation from indicator thresholds is standard.
- **Phase 4 (Paper Trading):** Simulated order fill pattern is well-understood. Main design constraint is keeping it separate from backtesting code path.
- **Phase 5 (API and Dashboard):** FastAPI + WebSocket + React + TradingView Lightweight Charts all have excellent documentation and reference implementations.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core Python/FastAPI/React stack is HIGH confidence — battle-tested in open-source trading projects. Data source stability is LOW — yfinance fragility and CoinGecko rate limits are well-documented pain points with no perfect free alternative. |
| Features | MEDIUM-HIGH | Table stakes verified against live platforms (Freqtrade, QuantConnect, TradingView, Danelfin). MVP scope is well-defined. Some complexity estimates are experience-based rather than empirically measured. |
| Architecture | MEDIUM-HIGH | Layered pipeline with normalizer, TimescaleDB, and separate backtesting/paper trading code paths is validated by multiple open-source reference implementations. Specific implementation details for walk-forward validation in vectorbt need verification. |
| Pitfalls | HIGH | Multiple independent sources with community consensus and official documentation. Look-ahead bias, overfitting, yfinance fragility, and LLM hallucination are universally cited. The production-readiness checklist is well-grounded. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **yfinance replacement for real-time stocks:** Finnhub is recommended but free-tier WebSocket behavior under load needs validation during Phase 1 build. Plan for a fallback (Alpha Vantage polling) if Finnhub rate limits are hit in practice.
- **vectorbt walk-forward API:** The walk-forward validation feature in vectorbt 0.26+ needs a dedicated spike during Phase 3 planning. Documentation is sparse; may require custom implementation.
- **LLM grounding architecture:** The specific pattern for injecting verified indicator data into LLM prompts without hallucination leakage is not standardized. Needs a prompt engineering spike before Phase 6 build.
- **CoinGecko 10,000 calls/month cap:** For a multi-coin scanning use case (100+ coins, every 5 minutes), 10,000 monthly calls will be exhausted in approximately 1.4 days. Aggressive local caching and longer polling intervals are mandatory. This may require downgrading scan frequency on the crypto side.
- **TimescaleDB vs. plain PostgreSQL:** Architecture research recommends TimescaleDB; stack research lists plain PostgreSQL. For MVP at single-user scale, plain PostgreSQL with a (symbol, timestamp) composite index is sufficient. Clarify the decision before Phase 1 build.

---

## Sources

### Primary (HIGH confidence)
- Freqtrade official documentation (freqtrade.io) — REST API, FreqAI module, paper trading dry-run mode
- QuantConnect platform documentation (quantconnect.com) — backtesting, paper trading, multi-asset support
- TradingView Pine Script documentation — strategy tester capabilities and limitations
- Danelfin (danelfin.com/how-it-works) — XAI signal scoring, win rate tracking approach
- vectorbt documentation (vectorbt.dev) — backtesting engine performance characteristics
- Interactive Brokers Campus — vectorized vs. event-driven backtesting comparison
- Event-Driven Backtesting with Python (QuantStart) — backtesting architecture patterns
- FastAPI + Postgres + WebSockets (TestDriven.io) — reference implementation
- intelligent-trading-bot (GitHub: asavinov) — open-source reference implementation
- Stock Trading Bot with Django + TimescaleDB (GitHub: codingforentrepreneurs) — reference implementation
- CFTC Advisory on AI Trading Bots — regulatory and risk context

### Secondary (MEDIUM confidence)
- Celery + Redis + FastAPI production guide (Medium, 2025) — deployment patterns
- TradingAgents multi-agent LLM framework (tradingagents-ai.github.io) — LLM orchestration patterns
- LangChain trading stock analysis (QuantInsti blog) — prompt engineering for financial data
- yfinance rate limit issues (Medium, Trading Dude) — confirmed fragility under load
- Backtrader vs vectorbt vs Zipline comparison (AutoTradeLab) — backtesting tool selection
- QuestDB blog: scaling trading bot with time-series database — TimescaleDB performance patterns
- Blockchain Council: backtesting pitfalls — lookahead bias and overfitting patterns
- Why Most Crypto Trading Bots Fail (DEV Community) — community failure modes
- Alpaca Markets: paper vs. live trading data study — paper trading optimism bias
- Blueberry Fund: AI hallucinations in finance — LLM risk documentation
- arXiv: TradeTrap LLM trading agent reliability — academic validation of LLM risks
- 3Commas: essential AI trading bot features 2025 — feature landscape validation

### Tertiary (LOW confidence)
- Stanford study cited in PITFALLS.md (58% of retail algo models collapse in 3 months) — not independently verified; directionally consistent with community data
- Option Alpha community data on paper vs. live fill rates — community-sourced, not peer-reviewed

---
*Research completed: 2026-04-06*
*Ready for roadmap: yes*
