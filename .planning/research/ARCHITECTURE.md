# Architecture Research

**Domain:** AI Trading Bot
**Researched:** 2026-04-06
**Confidence:** MEDIUM-HIGH (patterns verified across multiple sources, specific implementation details vary)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WEB DASHBOARD (Frontend)                    │
│              React + Chart.js / Lightweight Charts                  │
│    [Opportunity Feed] [Portfolio] [Backtesting UI] [Analytics]      │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP + WebSocket
┌────────────────────────────▼────────────────────────────────────────┐
│                         API LAYER (FastAPI)                         │
│         REST endpoints + WebSocket broadcaster                      │
└───┬───────────────┬──────────────────┬──────────────────────────────┘
    │               │                  │
    ▼               ▼                  ▼
┌────────┐  ┌───────────────┐  ┌───────────────┐
│ Auth / │  │  Backtesting  │  │  Paper Trading│
│ Config │  │    Engine     │  │   Simulator   │
└────────┘  └───────┬───────┘  └───────┬───────┘
                    │                  │
                    └────────┬─────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                     AI / SIGNAL ENGINE                              │
│  [Feature Builder] → [AI Analyzer] → [Signal Generator]            │
│  Technical indicators + LLM reasoning + opportunity scoring         │
└────────────────────────────┬────────────────────────────────────────┘
                             │ reads from / writes to
┌────────────────────────────▼────────────────────────────────────────┐
│                        DATA LAYER                                   │
│           PostgreSQL + TimescaleDB (time-series hypertables)        │
│  [market_data] [signals] [paper_trades] [backtest_results]          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                    DATA INGESTION LAYER                             │
│        APScheduler (periodic) + async fetchers                      │
│  [Yahoo Finance] [CoinGecko] [Frankfurter/ECB] [Options scraper]    │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Data Ingestion | Polls free APIs on a schedule, normalizes OHLCV data, persists to DB | Python + APScheduler + yfinance + requests |
| Market Data Store | Stores and queries time-series OHLCV data efficiently | PostgreSQL + TimescaleDB hypertables |
| Feature Builder | Computes technical indicators (RSI, MACD, Bollinger, volume) from raw OHLCV | pandas-ta or TA-Lib |
| AI Analyzer | Classifies opportunity quality; optionally generates natural-language reasoning | scikit-learn signals + LLM (OpenAI/local) for explanation |
| Signal Generator | Applies rules or model output to produce BUY/SELL/HOLD signals with score | Python rule engine or ML classifier output |
| Backtesting Engine | Replays historical OHLCV + signals, simulates fills, measures P&L, win rate | Vectorized (pandas) for speed; event-driven for accuracy |
| Paper Trading Simulator | Runs strategy against live market data using fake portfolio state | In-memory or DB portfolio + same execution path as backtester |
| API Layer | Exposes REST + WebSocket endpoints for dashboard; coordinates services | FastAPI |
| Web Dashboard | Visual interface: charts, opportunity feed, paper portfolio, analytics | React + Lightweight Charts (or TradingView widget) |
| Task Queue | Manages background jobs: data fetches, signal runs, backtests | APScheduler (simple) or Celery + Redis (distributed) |

---

## Recommended Project Structure

```
trading-bot/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entry point
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── signals.py       # GET /signals, WebSocket /ws/signals
│   │   │   │   ├── backtest.py      # POST /backtest/run, GET /backtest/{id}
│   │   │   │   ├── paper_trading.py # portfolio state, trade execution
│   │   │   │   └── market_data.py   # historical OHLCV queries
│   │   ├── core/
│   │   │   ├── config.py            # env vars, settings
│   │   │   └── database.py          # SQLAlchemy + TimescaleDB setup
│   │   ├── ingestion/
│   │   │   ├── scheduler.py         # APScheduler job definitions
│   │   │   ├── sources/
│   │   │   │   ├── yahoo.py         # stocks via yfinance
│   │   │   │   ├── coingecko.py     # crypto via CoinGecko API
│   │   │   │   ├── forex.py         # forex via Frankfurter/ECB
│   │   │   │   └── options.py       # options scraping (Yahoo Finance options chain)
│   │   │   └── normalizer.py        # maps all sources to common OHLCV schema
│   │   ├── analysis/
│   │   │   ├── features.py          # technical indicator computation (pandas-ta)
│   │   │   ├── ai_engine.py         # signal scoring: ML model or rule-based
│   │   │   ├── signal_generator.py  # converts scores to BUY/SELL/HOLD + reasoning
│   │   │   └── llm_explainer.py     # optional: LLM call for natural-language rationale
│   │   ├── backtesting/
│   │   │   ├── engine.py            # vectorized backtest runner
│   │   │   ├── events.py            # event types: MARKET, SIGNAL, ORDER, FILL
│   │   │   ├── portfolio.py         # position tracking, P&L, drawdown
│   │   │   └── metrics.py           # Sharpe, win rate, max drawdown
│   │   ├── paper_trading/
│   │   │   ├── simulator.py         # fake order execution against live prices
│   │   │   └── portfolio.py         # paper portfolio state
│   │   └── models/
│   │       ├── market_data.py       # ORM: OHLCV hypertable
│   │       ├── signal.py            # ORM: generated signals + scores
│   │       ├── backtest.py          # ORM: backtest run + results
│   │       └── paper_trade.py       # ORM: paper trade history
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Charts/              # price charts with signal overlays
│   │   │   ├── SignalFeed/          # real-time opportunity list
│   │   │   ├── PaperPortfolio/      # fake portfolio tracker
│   │   │   ├── BacktestRunner/      # form + results display
│   │   │   └── Analytics/           # win rate, P&L history
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts      # live signal subscription
│   │   └── api/
│   │       └── client.ts            # REST API calls
├── docker-compose.yml               # postgres+timescaledb, redis (if celery)
├── alembic/                         # DB migrations
└── tests/
    ├── test_ingestion.py
    ├── test_signals.py
    └── test_backtest.py
```

---

## Data Flow

### Market Data Flow

```
Schedule trigger (APScheduler)
  │
  ▼
Source-specific fetcher
  (yfinance / CoinGecko API / Frankfurter / Yahoo options chain)
  │
  ▼
Normalizer
  (maps to: {symbol, timestamp, open, high, low, close, volume, market})
  │
  ▼
TimescaleDB market_data hypertable
  (INSERT with ON CONFLICT DO NOTHING for idempotency)
  │
  ▼
Feature Builder
  (reads recent N candles, computes RSI, MACD, BB, ATR, volume ratios)
  │
  ▼
AI Analyzer / Signal Generator
  (scores each symbol: opportunity strength, direction, timeframe)
  │
  ▼
signals table
  (INSERT: symbol, score, direction, entry_price, target, stop, reasoning)
  │
  ▼
FastAPI WebSocket broadcaster
  ▼
Dashboard signal feed (real-time push to browser)
```

### Signal Generation Flow

```
New market data written to DB
  │
  ▼
Trigger: APScheduler fires signal scan (e.g., every 5 min during market hours)
  │
  ▼
For each watched symbol:
  ├─ Pull last N candles from TimescaleDB
  ├─ Compute features (pandas-ta)
  ├─ Score with AI engine (rule-based OR ML classifier)
  ├─ If score > threshold → generate signal record
  │    {symbol, market, direction, entry, target, stop_loss,
  │     confidence_score, reasoning_text, timeframe}
  └─ Persist to signals table
  │
  ▼
Push new signals via WebSocket to connected dashboard clients
```

### Backtesting Flow

```
User selects: symbol + date range + strategy parameters (via dashboard form)
  │
  ▼
POST /backtest/run → FastAPI creates background task
  │
  ▼
Backtesting Engine loads historical OHLCV from TimescaleDB
  (no external API calls during backtest — use stored data only)
  │
  ▼
Vectorized pass:
  ├─ Compute features on entire price history
  ├─ Apply signal logic to generate historical signals
  ├─ Simulate fills (assume next-bar open, apply slippage estimate)
  └─ Track portfolio equity curve
  │
  ▼
Metrics computation:
  (Sharpe ratio, win rate, max drawdown, total return, trade list)
  │
  ▼
Store in backtest_results table
  │
  ▼
Dashboard fetches and renders equity curve + trade list
```

### Paper Trading Flow

```
Paper Trading Simulator runs continuously (same scheduler as signal scan)
  │
  ▼
For each active paper position:
  ├─ Fetch current price from DB (latest candle)
  ├─ Check stop-loss or take-profit conditions
  └─ If triggered → record paper SELL, update portfolio state
  │
For each new signal (above confidence threshold):
  ├─ Check paper portfolio has capacity (max positions, risk per trade)
  └─ If yes → record paper BUY at current market price
  │
  ▼
paper_trades + paper_portfolio tables updated
  │
  ▼
Dashboard paper portfolio view reflects state
  (positions, unrealized P&L, trade history, running win rate)
```

---

## Build Order (Phase Dependencies)

The components have strict dependency ordering. Building out-of-order produces unmockable interfaces or untestable code.

```
Phase 1 — Data Foundation
  TimescaleDB schema + migrations
  Data ingestion (stocks first — best free data)
  → Dependency: Everything else reads from this layer

Phase 2 — Analysis Engine
  Feature builder (technical indicators)
  Signal generator (rule-based first, AI overlay later)
  → Dependency: Requires Phase 1 to have data to analyze

Phase 3 — Backtesting Engine
  Vectorized backtest runner
  Metrics computation
  → Dependency: Requires Phase 1 historical data + Phase 2 signal logic

Phase 4 — Paper Trading Simulator
  Paper portfolio state + fake order execution
  → Dependency: Requires Phase 2 live signals + Phase 1 live data

Phase 5 — API + Dashboard
  FastAPI REST + WebSocket
  React dashboard with charts
  → Dependency: All backend components complete (can start in parallel after Phase 2)

Phase 6 — Market Expansion
  Add crypto, forex, options ingestion adapters
  → Dependency: Phase 1 ingestion infrastructure already in place
```

---

## Scaling Considerations

| Concern | At MVP (1 user) | At 100 users | At 1000+ users |
|---------|-----------------|--------------|----------------|
| Data storage | SQLite acceptable | TimescaleDB required | TimescaleDB with partitioning |
| Task scheduling | APScheduler in-process | APScheduler still fine | Celery + Redis workers |
| Signal broadcasting | In-memory WebSocket | Redis pub/sub for multi-worker | Redis Streams |
| Backtesting | Synchronous background task | Queue with status polling | Dedicated worker pool |
| API | Single FastAPI process | Uvicorn workers | Load balancer + multiple instances |

For MVP: run everything in a single Python process with APScheduler. No Celery, no Redis, no distributed systems. Add them only when scale demands it.

---

## Anti-Patterns

### Anti-Pattern 1: Calling Live APIs During Backtesting
**What:** Fetching prices from Yahoo Finance / CoinGecko inside the backtest loop.
**Why bad:** Rate limits hit immediately, introduces latency, results non-reproducible, future data leak possible.
**Instead:** Backtest engine reads exclusively from local TimescaleDB. Ingest historical data first as a separate step.

### Anti-Pattern 2: Coupling Signal Logic to Data Source Format
**What:** Signal generator code that directly parses Yahoo Finance JSON or CoinGecko response structures.
**Why bad:** Changing a data source requires rewriting the analysis layer. Hard to test.
**Instead:** Normalizer layer converts all sources to a canonical OHLCV schema before writing to DB. Signal generator only ever sees normalized data.

### Anti-Pattern 3: Mixing Backtesting and Paper Trading Code Paths
**What:** Using one code path for both backtest and paper trading, parameterized by a `live=True` flag.
**Why bad:** Live paper trading needs real-time scheduling, persistence, and state management that backtesting doesn't. The flag proliferates and creates hard-to-trace bugs.
**Instead:** Separate modules that share the Portfolio and Signal logic via a common interface, but have distinct entry points and I/O.

### Anti-Pattern 4: No Lookahead Bias Guard in Backtesting
**What:** Computing features using data from the future (e.g., a 5-day moving average that uses day 6 to compute the value for day 5).
**Why bad:** Backtested results look exceptional, live results fail. This is the #1 cause of strategy overfit.
**Instead:** In vectorized backtesting, always `shift(1)` signal columns before generating trade decisions. Features must only use data available at signal time.

### Anti-Pattern 5: Starting with Celery + Redis + Kafka for MVP
**What:** Full distributed task queue infrastructure from day one.
**Why bad:** Enormous operational overhead, complex debugging, wasted time. A single APScheduler instance handles hundreds of symbols for a single-user MVP.
**Instead:** APScheduler in-process for MVP. Migrate to Celery only when a real bottleneck is measured.

### Anti-Pattern 6: Real-Time WebSocket for All Data
**What:** Streaming every price tick to the dashboard via WebSocket.
**Why bad:** For a suggestion-focused (not HFT) tool, this burns CPU and bandwidth on data the UI doesn't need. Free API sources can't sustain it anyway.
**Instead:** WebSocket for new signal events only. Dashboard polls REST endpoints for chart data at user-controlled refresh intervals.

### Anti-Pattern 7: Over-fitting AI to Historical Data
**What:** Optimizing ML model hyperparameters on the full historical dataset, then reporting that backtest performance as validation.
**Why bad:** A study of 888 algorithmic strategies found backtested Sharpe ratios have R² < 0.025 correlation to live performance. ~44% of published strategies fail forward.
**Instead:** Always hold out an out-of-sample test period. Prefer rule-based signals with explainable logic for MVP; add ML as an overlay later when validation data exists.

---

## Component Interface Contracts

These boundaries define what each layer exposes. Enforcing them prevents tight coupling.

```
DataIngestion → Database
  writes: {symbol, market, timestamp, open, high, low, close, volume}
  all sources must normalize to this schema before insertion

Database → AnalysisEngine
  reads: list[OHLCV] for symbol+timeframe window
  writes: list[Signal] {symbol, direction, score, entry, target, stop, reasoning}

AnalysisEngine → BacktestingEngine
  shared: feature computation logic (FeatureBuilder class)
  backtest passes its own historical OHLCV slice, gets signals back
  NEVER calls external APIs

AnalysisEngine → PaperTradingSimulator
  shared: same Signal schema as live signals
  simulator reads from signals table, maintains portfolio state separately

BacktestingEngine → API
  BacktestResult: {id, symbol, date_range, trades[], metrics{}, equity_curve[]}

API → Dashboard
  REST: OHLCV history, signals list, backtest results, paper portfolio
  WebSocket: new signal events only (push model)
```

---

## Sources

- [Stock Trading Bot Architecture: Core Components Explained (Medium)](https://medium.com/@halljames9963/stock-trading-bot-architecture-core-components-explained-d46f5d77c019) — MEDIUM confidence (Medium blog, not official docs)
- [Event-Driven Backtesting with Python Part I (QuantStart)](https://www.quantstart.com/articles/Event-Driven-Backtesting-with-Python-Part-I/) — HIGH confidence (widely cited reference in quant dev community)
- [Intelligent Trading Bot (GitHub: asavinov)](https://github.com/asavinov/intelligent-trading-bot) — HIGH confidence (open-source reference implementation)
- [Building an AI-Powered Stock Trading Bot in Python with Backtesting (DEV Community)](https://dev.to/sajjasudhakararao/building-an-ai-powered-stock-trading-bot-in-python-with-backtesting-19f6) — MEDIUM confidence
- [Stock Trading Bot with Django + TimescaleDB (GitHub: codingforentrepreneurs)](https://github.com/codingforentrepreneurs/Stock-Trading-Bot) — HIGH confidence (reference implementation)
- [TimescaleDB for Algorithmic Trading (Siddharth's Blog)](https://siddharthqs.com/introduction-to-timescaledb-for-algorithmic-trading) — MEDIUM confidence
- [Scaling a Trading Bot with a Time-Series Database (QuestDB)](https://questdb.com/blog/scaling-trading-bot-with-time-series-database/) — MEDIUM confidence
- [Vectorized vs Event-Driven Backtesting (Interactive Brokers Campus)](https://www.interactivebrokers.com/campus/ibkr-quant-news/a-practical-breakdown-of-vector-based-vs-event-based-backtesting/) — HIGH confidence (official broker educational content)
- [Common Pitfalls: Crypto Trading Bot Mistakes (Coin Bureau)](https://coinbureau.com/guides/crypto-trading-bot-mistakes-to-avoid) — MEDIUM confidence
- [FastAPI + Postgres + WebSockets Dashboard (TestDriven.io)](https://testdriven.io/blog/fastapi-postgres-websockets/) — HIGH confidence (practical reference)

---

*Architecture research for: AI Trading Bot*
*Researched: 2026-04-06*
