# Stack Research

**Domain:** AI Trading Bot (multi-market, web dashboard, free data sources)
**Researched:** 2026-04-06
**Confidence:** MEDIUM (core Python/FastAPI/React stack is HIGH; data source stability is LOW due to third-party fragility)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Backend runtime | Finance/ML ecosystem is Python-first; every serious trading library is Python-native. 3.11 gives measurable speed gains over 3.10 and is the current LTS-stable choice. |
| FastAPI | 0.115+ | API server + WebSocket server | Async-first, built-in WebSocket support for real-time price streaming, automatic OpenAPI docs, Pydantic validation. Used by Freqtrade's REST API layer — battle-tested for this domain. |
| Uvicorn | 0.30+ | ASGI server | Required by FastAPI; single-worker for dev, multi-worker via `uvicorn --workers N` for production. |
| React | 18+ | Frontend UI | Proven ecosystem for dashboards; TradingView Lightweight Charts has a first-class React integration. Vite beats Next.js for this use-case (see below). |
| Vite | 5+ | Frontend build tool | Sub-second HMR, zero-config TypeScript, smallest bundles. Trading dashboards are authenticated SPAs — no SEO required, no need for Next.js SSR overhead. |
| TypeScript | 5+ | Frontend language | Type safety for complex chart/portfolio state. Adds ~0 runtime cost with Vite. |
| Redis | 7.2+ | Task queue broker + pub/sub | Message broker for Celery background tasks; pub/sub channel for broadcasting live price ticks to WebSocket clients. Redis 7+ Sentinel handles failover. |
| Celery | 5.4+ | Background task queue | Schedules recurring market scans (every 5 min, hourly, etc.), runs backtests asynchronously, handles rate-limited API fetching without blocking the web tier. |
| SQLite (dev) / PostgreSQL 16+ (prod) | — | Persistent storage | Trade history, AI suggestions, win-rate stats, paper portfolio positions. SQLAlchemy 2.0 ORM lets you run SQLite locally and promote to Postgres without query rewrites. SQLite is what Freqtrade uses by default — proven for this domain. |
| SQLAlchemy | 2.0+ | ORM | Declarative models, async session support with FastAPI, single codebase for SQLite/Postgres swap. |

---

### Data Layer — Free Sources

| Source | Markets | Constraints | Python Library |
|--------|---------|-------------|----------------|
| **yfinance** | Stocks (OHLCV, fundamentals, options chains) | Unofficial scraper; fragile, rate-limited. Reliable for daily/weekly historical data. NOT suitable for real-time polling every few seconds. | `yfinance` (0.2+) |
| **Alpha Vantage** | Stocks, Forex, Crypto, technical indicators | Free tier: 25 requests/day (severely limited). Upgrade to 500 req/day free plan with email signup. Best backup for yfinance gaps. | `alpha_vantage` or raw `httpx` |
| **Finnhub** | US stocks real-time (60 calls/min free), crypto | Most generous free real-time tier. WebSocket feed available for free. Use for live price ticks. | `finnhub-python` or `websockets` |
| **CoinGecko** | Crypto (18,000+ coins) | Free Demo plan: 10,000 calls/month, 1 year history. Best free crypto source by coverage. | `pycoingecko` |
| **CCXT** | Crypto (100+ exchanges) | MIT license, free forever. Use for exchange OHLCV data, order books. Covers Binance, Coinbase, Kraken. | `ccxt` (4+) |
| **Alpha Vantage (FX)** | Forex (major pairs) | 500 req/day free tier covers daily FX rates. Intraday FX is rate-limited hard. | `alpha_vantage` |

**Market Prioritization for MVP (research-driven):**
- **Stocks first** — best free data coverage (yfinance + Finnhub), most familiar to new traders
- **Crypto second** — excellent free data (CoinGecko + CCXT), active API ecosystem
- **Forex third** — Alpha Vantage covers it, but free tier limits realtime use
- **Options last** — Free options chain data exists (yfinance), but greeks/IV calculations require extra work; highest complexity for a beginner trader

---

### AI / Signal Generation Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **OpenAI API** (gpt-4o-mini) | latest | LLM reasoning for signal explanations, trade rationale | gpt-4o-mini at ~$0.15/1M input tokens is cheap enough for a dev-stage bot. Generates human-readable "why" explanations — the core educational value prop. |
| **LangChain** | 0.3+ | LLM orchestration, RAG pipelines, agent chains | Standard Python library for chaining LLM calls with tool use; used in TradingAgents framework. Handles prompt templates, context injection, memory. |
| **pandas-ta** | 0.3.14b | Technical indicators (150+) | Pure Python, integrates natively with pandas DataFrames. No C compilation required (unlike TA-Lib). Covers RSI, MACD, Bollinger Bands, ATR, Stochastic — everything needed for signal generation. |
| **pandas** | 2.2+ | Data manipulation, OHLCV processing | Industry standard; every data source returns DataFrames. |
| **numpy** | 1.26+ | Numerical computation | Foundation for pandas and vectorbt. |
| **scikit-learn** | 1.5+ | Feature engineering helpers, optional ML signals | For future pattern detection; not needed for LLM-first MVP but import-ready. |

**LLM cost note:** For zero ongoing cost, use **Ollama** running a local `llama3.2` or `mistral` model. Response quality is noticeably lower than gpt-4o-mini for financial reasoning, but it costs nothing. Recommended approach: design the system to be model-swappable (OpenAI-compatible API interface) so you can run Ollama locally and switch to OpenAI in production.

---

### Backtesting Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **vectorbt** | 0.26+ | Backtesting engine | Fastest Python backtester — NumPy/Numba vectorized, handles years of minute-level data in seconds. Active development (1.2.0 added tick-level resolution, Oct 2025). Better choice than Backtrader for the data volumes this bot will generate. |
| **Backtesting.py** | 0.3+ | Simple strategy prototyping | Beginner-friendly fallback if vectorbt's API proves complex. Useful for validating single-asset strategies quickly. |

**Why not Backtrader:** Still works for swing trading strategies, but event-driven Python execution is slow at scale. vectorbt handles 5 years of daily data across 500 symbols in under a minute. Backtrader takes minutes.

**Why not Zipline:** Designed for Python 3.5-3.6; requires forks (zipline-reloaded) to run on modern Python. Slow. Quantopian is dead. Avoid.

---

### Frontend Libraries

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **TradingView Lightweight Charts** | 4+ | OHLCV candlestick + line charts | Free, open-source, MIT license. Renders 100k+ bars smoothly in browser. Official React integration. Industry standard for web trading UIs. |
| **TanStack Query** | 5+ | Server state management, REST data fetching | Handles caching, background refetching, loading/error states for REST endpoints. |
| **Zustand** | 4+ | Frontend state management | Lightweight alternative to Redux; sufficient for portfolio state, alert state. |
| **Tailwind CSS** | 3+ | Styling | Utility-first; fast to build dense data-heavy dashboards. Standard choice for 2025 React apps. |
| **shadcn/ui** | latest | UI component library | Built on Radix UI + Tailwind. Pre-built tables, cards, dropdowns — critical for dashboard screens. Copies components into your codebase (no runtime dependency). |
| **Recharts** | 2+ | Secondary charts (performance curves, win-rate graphs) | React-native charting for non-OHLCV data (portfolio value over time, win/loss breakdown). Lighter than Chart.js for simple charts. |

---

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **Docker + Docker Compose** | Container orchestration | Single `docker-compose up` starts API, Redis, Celery worker, Postgres. Critical for reproducibility. |
| **Poetry** or **uv** | Python dependency management | uv is the 2025 standard — 10-100x faster than pip. Poetry is still widely used. Either works; uv is recommended for greenfield. |
| **pytest** | Backend testing | Standard Python test runner. Use `pytest-asyncio` for FastAPI endpoint tests. |
| **Alembic** | Database migrations | SQLAlchemy companion for schema versioning. Lets you evolve the DB schema as features are added. |
| **Flower** | Celery task monitoring | Web UI at `localhost:5555` showing queued/active/failed tasks. Essential for debugging market scan jobs. |
| **pre-commit** | Code quality hooks | ruff (linting + formatting) + mypy (type checking) as pre-commit hooks. |
| **ruff** | Python linting + formatting | Replaces flake8 + black + isort; 10-100x faster than legacy tools. 2025 standard. |

---

## Installation

```bash
# Python backend — using uv
uv init trading-bot-backend
cd trading-bot-backend
uv add fastapi uvicorn[standard] celery[redis] redis sqlalchemy alembic \
       yfinance finnhub-python pycoingecko ccxt alpha_vantage \
       pandas numpy pandas-ta vectorbt langchain openai \
       httpx websockets python-dotenv pydantic-settings

uv add --dev pytest pytest-asyncio ruff mypy pre-commit

# Frontend — using Vite + React + TypeScript
npm create vite@latest trading-bot-frontend -- --template react-ts
cd trading-bot-frontend
npm install lightweight-charts @tanstack/react-query zustand \
            tailwindcss @tailwindcss/vite recharts
npx shadcn@latest init

# Infrastructure — Docker Compose
# docker-compose.yml includes: postgres, redis, api, celery-worker, flower
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| React + Vite | Next.js 15 | Only if you need SSR, public-facing SEO pages, or marketing site alongside the dashboard |
| React + Vite | Streamlit | Only for internal prototype/demo — terrible DX for real-time WebSocket UIs, not suitable for production dashboard |
| vectorbt | Backtrader | If strategies are simple event-driven (single asset, small data) and you prefer its cleaner API; acceptable for swing-only strategies |
| FastAPI | Django + DRF | If team has existing Django expertise; FastAPI's async + WebSocket support is materially better for real-time trading data |
| FastAPI | Flask | Flask has no native async or WebSocket support; avoid for a real-time system |
| Celery + Redis | APScheduler | APScheduler is fine for simple cron-style scheduling but lacks Celery's retry logic, task inspection, and horizontal scaling |
| pandas-ta | TA-Lib | If you need maximum performance on very large datasets and are willing to manage C compilation across environments |
| OpenAI API | Anthropic Claude API | Comparable quality; gpt-4o-mini is cheaper than comparable Claude Haiku for this use-case; swap is trivial since LangChain abstracts the provider |
| OpenAI API | Ollama (local) | Zero cost — valid for dev/demo; lower quality financial reasoning; swap is trivial if API is designed with OpenAI-compatible interface |
| PostgreSQL | SQLite (permanent) | SQLite is fine for single-user local dev; PostgreSQL required for multi-user or production deployment |
| CoinGecko + CCXT | Binance direct API | CCXT wraps Binance (and 99 other exchanges) — no reason to use Binance's Python SDK directly |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Zipline** | Designed for Python 3.5-3.6; community-maintained forks are fragile; slow on modern data volumes; Quantopian (its origin) is dead | vectorbt or Backtesting.py |
| **yfinance for real-time polling** | Unofficial scraper; 429 errors are common under load; HTML changes break it without warning | Finnhub WebSocket (free, official, 60 calls/min) |
| **Streamlit for the dashboard** | Cannot handle WebSocket push properly; poor state management for complex UIs; styling is constrained; becomes a liability once you need real charts | React + Vite + TradingView Lightweight Charts |
| **Node.js backend** | Finance/ML ecosystem is Python-first; you'd lose access to pandas, vectorbt, pandas-ta, LangChain, scikit-learn natively | FastAPI (Python) |
| **RabbitMQ** | More complex to deploy and operate than Redis for this scale; Redis 7 handles Celery message brokering fine at small-to-medium scale | Redis |
| **Redux** | Overkill for dashboard state; complex boilerplate; Zustand covers the same need in 10x less code | Zustand |
| **Chart.js or D3.js for OHLCV** | Chart.js struggles with dense candlestick data; D3 requires custom implementation; TradingView Lightweight Charts is purpose-built for this | TradingView Lightweight Charts |
| **Free forex APIs for intraday** | No free source provides reliable sub-hourly forex data; even Alpha Vantage's free tier is severely constrained | Scope forex to daily/swing timeframes only in MVP, or defer it |
| **Options data for MVP** | Greeks, IV surface, options chains require significant data engineering work; free sources (yfinance options) are limited and unreliable for real-time | Defer options to v2; focus MVP on stocks + crypto |

---

## Sources

- Freqtrade REST API documentation: https://www.freqtrade.io/en/stable/rest-api/
- VectorBT documentation: https://vectorbt.dev/
- TradingView Lightweight Charts React tutorial: https://tradingview.github.io/lightweight-charts/tutorials/react/simple
- CoinGecko API (free tier): https://www.coingecko.com/en/api
- CCXT documentation: https://docs.ccxt.com/
- Alpha Vantage API: https://www.alphavantage.co/documentation/
- FastAPI + WebSocket real-time dashboard: https://testdriven.io/blog/fastapi-postgres-websockets/
- Celery + Redis + FastAPI production guide: https://medium.com/@dewasheesh.rana/celery-redis-fastapi-the-ultimate-2025-production-guide-broker-vs-backend-explained-5b84ef508fa7
- TradingAgents multi-agent LLM framework: https://tradingagents-ai.github.io/
- LangChain trading stock analysis: https://blog.quantinsti.com/langchain-trading-stock-analysis-llm-financial-python/
- Vite vs Next.js 2026 comparison: https://designrevision.com/blog/vite-vs-nextjs
- yfinance rate limit issues: https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01
- Backtrader vs NautilusTrader vs VectorBT vs Zipline: https://autotradelab.com/blog/backtrader-vs-nautilusttrader-vs-vectorbt-vs-zipline-reloaded
- QuestDB scaling a trading bot: https://questdb.com/blog/scaling-trading-bot-with-time-series-database/

---

*Stack research for: AI Trading Bot*
*Researched: 2026-04-06*
