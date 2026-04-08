<!-- GSD:project-start source:PROJECT.md -->
## Project

**AI Trading Bot**

An AI-powered trading assistant that scans multiple financial markets (stocks, crypto, forex, options), identifies the best opportunities using artificial intelligence, and presents actionable suggestions with profitability estimates. Users can simulate strategies through backtesting and paper trading before committing real money. The MVP focuses on AI-driven suggestions — not auto-execution — delivered through a web dashboard.

**Core Value:** The AI must surface high-quality trading opportunities with clear reasoning and win-rate tracking, so users can make informed decisions faster than they could manually scanning markets.

### Constraints

- **Data**: Free sources only — Yahoo Finance, CoinGecko, free API tiers, web scraping where necessary
- **Tech stack**: Research-driven — let domain research guide the best stack (Python likely for finance/ML ecosystem)
- **Deployment**: Web dashboard accessible via browser
- **Budget**: Zero ongoing costs for data — infrastructure costs should be minimal
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack (Implemented)

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Backend runtime |
| FastAPI | 0.135+ | API server + WebSocket server |
| Uvicorn | 0.44+ | ASGI server |
| SQLAlchemy | 2.0+ | ORM (async sessions) |
| asyncpg / aiosqlite | latest | Async DB drivers |
| Alembic | 1.18+ | DB migrations (7 versions) |
| APScheduler | 3.11+ | Background scheduler (NOT Celery — single-process MVP decision) |
| pydantic-settings | 2.13+ | Type-safe config from env |
| slowapi | 0.1.9+ | Rate limiting |
| secure | 1.0+ | Security headers middleware |
| PyJWT | 2.12+ | JWT tokens |
| passlib + argon2-cffi | latest | Password hashing |

### Data Layer
| Source | Library | Schedule |
|--------|---------|---------|
| yfinance | yfinance 1.2+ | Every 5 min (stocks) |
| CoinGecko | pycoingecko 3.2+ | Every 30 min (top-5 crypto) |
| CCXT (Binance) | ccxt 4.5+ | Every 15 min (crypto OHLCV) |
| Alpha Vantage | httpx | Every 24h (forex daily) |
| Finnhub | websockets | WebSocket live ticks |

### AI / Signal Layer
| Technology | Version | Purpose |
|------------|---------|---------|
| pandas-ta-classic | 0.4.47+ | Technical indicators (NOT pandas-ta — different package) |
| pandas | 3.0+ | OHLCV processing |
| vectorbt | 0.28+ | Backtesting engine |
| LangChain + OpenAI | 0.3+ | LLM signal explanations (gpt-4o-mini, optional) |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19+ | UI framework |
| Vite | 8+ | Build tool |
| TypeScript | 6+ | Language |
| Tailwind CSS | 4+ | Styling |
| shadcn/ui | 4+ | Component library |
| TradingView Lightweight Charts | 5.1+ | Candlestick charts |
| TanStack Query | 5+ | Server state / data fetching |
| Zustand | 5+ | Frontend state management |
| Recharts | 3+ | Performance curves, win-rate graphs |
| React Router | 7+ | SPA routing |
| Playwright | 1.59+ | E2E tests |

### Infrastructure
| Tool | Purpose |
|------|---------|
| Docker Compose | TimescaleDB (PostgreSQL 16) only — backend runs locally |
| TimescaleDB | PostgreSQL 16 extension for time-series (hypertables) |
| SQLite + aiosqlite | Dev fallback (no Docker needed) |
<!-- GSD:stack-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture Overview

```
Free APIs (yfinance, CoinGecko, CCXT, Finnhub, Alpha Vantage)
    |
    v
APScheduler jobs (7 jobs, 5-min to 24h intervals)
    |
    v
ingestion/ providers --> upsert_candles() --> market_data table (TimescaleDB hypertable)
                                                      |
                                                      v
                                              analysis/ scanner.py
                                              (every 5 min via scheduler)
                                                      |
                            +-----------+-------------+-------------+
                            |           |             |             |
                      indicators/   signals/     regime/       explainer/
                      (pure fn)    (pure fn)    (pure fn)    (LLM, optional)
                            |           |             |             |
                            +-----+-----+-------------+-------------+
                                  |
                                  v
                           signals table (upsert ON CONFLICT DO UPDATE)
                                  |
                    +-------------+-------------+
                    |                           |
              FastAPI REST API            WebSocket /ws/live
              (JWT-protected)            (Finnhub live ticks)
                    |                           |
              React SPA                   TanStack Query cache
              (Vite, port 5173)           (injected via useWebSocket.ts)
```

**Key design principle:** All analysis engines (`indicators.py`, `signals.py`, `backtesting/engine.py`, `paper_trading/engine.py`, `alerts/engine.py`) are pure functions — no DB, no FastAPI imports. Fully testable in isolation.
<!-- GSD:architecture-end -->

## Running the App

### Prerequisites
- Python 3.11+, uv, Node.js 20+, Docker (for TimescaleDB)

### Start TimescaleDB
```bash
docker compose up -d
```

### Backend
```bash
# Install dependencies
cd backend
uv sync

# Run migrations (first time or after schema changes)
uv run alembic upgrade head

# Start API server (port 8000)
uv run uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 — proxies /api and /ws to localhost:8000
```

### Run Tests
```bash
# From repo root
PYTHONPATH=backend uv --project backend run pytest tests/ -q

# Single file
PYTHONPATH=backend uv --project backend run pytest tests/test_indicators.py -v
```

### Hash a New Admin Password
```bash
PYTHONPATH=backend uv --project backend run python -c \
  "from app.core.security import hash_password; print(hash_password('yourpassword'))"
# Paste the output into ADMIN_PASSWORD_HASH in .env
```

## Environment Variables

Copy `.env.example` to `.env` in the `backend/` directory.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | SQLite dev.db | asyncpg or aiosqlite URL |
| `FINNHUB_API_KEY` | Yes | — | Finnhub WebSocket live ticks |
| `COINGECKO_API_KEY` | Yes | — | CoinGecko Demo plan key |
| `ALPHA_VANTAGE_API_KEY` | No | "" | Forex daily data (skipped if empty) |
| `JWT_SECRET` | Yes | dev-secret (change!) | Signs JWT access tokens |
| `ADMIN_USERNAME` | No | admin | Single-user login username |
| `ADMIN_PASSWORD_HASH` | Yes | — | Argon2 hash from `hash_password()` |
| `FRONTEND_URL` | No | http://localhost:5173 | CORS allowed origin |
| `COOKIE_SAMESITE` | No | lax | Cookie SameSite attribute |
| `TELEGRAM_BOT_TOKEN` | No | "" | Alert notifications (disabled if empty) |
| `TELEGRAM_CHAT_ID` | No | "" | Telegram chat target |
| `DISCORD_WEBHOOK_URL` | No | "" | Discord alert webhook |
| `OPENAI_API_KEY` | No | "" | LLM explanations (disabled if empty) |
| `LLM_ENABLED` | No | false | Master switch for LLM explanations |

## API Endpoints

### Auth (unprotected)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Login with username+password, sets JWT httpOnly cookie |
| POST | `/auth/logout` | Clears JWT cookie |
| GET | `/auth/me` | Returns current user info (requires valid cookie) |

### Market Data (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/candles/{symbol}` | OHLCV candles (params: interval, limit) |
| GET | `/api/symbols` | List of all tracked symbols |

### Indicators (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/indicators/{symbol}` | Computed IndicatorSet for a symbol |

### Signals (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/signals` | All latest signals (BUY/SELL/HOLD) |
| GET | `/api/signals/{symbol}` | Signal for one symbol |

### Backtesting (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/backtest` | Run vectorbt backtest for a symbol |
| GET | `/api/backtest/runs` | List historical backtest runs |

### Paper Trading (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/paper/portfolio` | Current portfolio (cash, positions, equity) |
| POST | `/api/paper/order` | Place a paper BUY or SELL order |
| GET | `/api/paper/trades` | Trade history |
| GET | `/api/paper/equity` | Equity curve (time series) |

### Alerts (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/alerts` | List all alert rules |
| POST | `/api/alerts` | Create an alert rule |
| DELETE | `/api/alerts/{id}` | Delete an alert rule |

### Education (unprotected)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/education/lessons` | List all lessons |
| GET | `/api/education/lessons/{id}` | Get lesson content |

### WebSocket
| Path | Description |
|------|-------------|
| `ws://localhost:8000/ws/live` | Live Finnhub price ticks, broadcast to all connected clients |

## Database Schema

7 tables across 7 Alembic migrations.

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `market_data` | symbol, market, interval, timestamp, open, high, low, close, volume | TimescaleDB hypertable; PK = (symbol, interval, timestamp); upsert DO NOTHING |
| `signals` | symbol, interval, scanned_at, direction, confidence, regime, close, entry_price, stop_loss, target_price, rsi_14, macd_val, adx_14, atr_14, reasons, explanation, multiframe_agreement | Upsert ON CONFLICT (symbol, interval) DO UPDATE — always refreshed |
| `backtest_runs` | id, symbol, interval, run_at, sharpe_ratio, max_drawdown, win_rate, profit_factor, total_return, total_trades, equity_curve | equity_curve is JSON array of [ts, value] pairs |
| `paper_portfolio` | id, cash, created_at | Single row; starting cash $10,000 |
| `paper_positions` | id, symbol, quantity, avg_entry_price, opened_at | Open positions |
| `paper_trades` | id, symbol, side, quantity, fill_price, commission_paid, realized_pnl, created_at | Completed fills |
| `paper_equity_snapshots` | id, timestamp, equity | Equity value at each 5-min snapshot |
| `alert_rules` | id, symbol, threshold_type, threshold_value, enabled, created_at | threshold_type: price_spike, volume_surge, trend_reversal |
| `users` | id, username, password_hash, created_at | Single admin user |

## APScheduler Jobs

7 jobs registered at startup via `ingestion/scheduler.py` lifespan hook:

| Job ID | Function | Interval | Purpose |
|--------|----------|---------|---------|
| `stock_incremental` | `stock_incremental_job()` | Every 5 min | yfinance OHLCV for STOCK_WATCHLIST |
| `crypto_coingecko` | `crypto_coingecko_job()` | Every 30 min | CoinGecko 4H candles for top-5 coins |
| `crypto_ccxt` | `crypto_ccxt_job()` | Every 15 min | CCXT Binance OHLCV for CCXT_CRYPTO_SYMBOLS |
| `analysis_scan` | `analysis_scan_job()` | Every 5 min | Rule-based signal scan across all assets |
| `paper_equity_snapshot` | `equity_snapshot_job()` | Every 5 min | Mark paper portfolio to market |
| `alert_check` | `alert_check_job()` | Every 5 min | Evaluate alert rules, dispatch notifications |
| `forex_daily` | `forex_daily_job()` | Every 24h | Alpha Vantage daily FX candles |

## Security

- **Auth**: Single-user login via `/auth/login`. Password verified with Argon2 (`passlib`). On success, a 30-min JWT is set as an httpOnly cookie (`access_token`).
- **JWT**: Signed with HS256 using `JWT_SECRET`. Decoded by `get_current_user` dependency injected on all protected routers.
- **CORS**: Restricted to `FRONTEND_URL` (default `http://localhost:5173`). `allow_credentials=True` required for cookie transport.
- **Security headers**: `secure` library adds HSTS, X-Frame-Options, X-Content-Type-Options, etc. via async middleware.
- **Rate limiting**: `slowapi` (wraps limits-library). Configured on sensitive endpoints.
- **Allowed methods**: GET, POST, DELETE, OPTIONS only.

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

### Pure Function Pattern
All analysis and simulation engines are pure functions with no I/O:
- `compute_indicators(df, symbol, interval) -> IndicatorSet | None`
- `score_signal(ind) -> SignalResult`
- `detect_regime(ind, atr_sma_20) -> RegimeType`
- `run_backtest(df, ...) -> BacktestResult`
- `fill_order(...) -> FillResult`
- `check_alerts(candles, rules, rsi_series) -> list[AlertTrigger]`

This makes them testable with zero infrastructure — no DB, no FastAPI, no scheduler needed.

### Provider ABC Pattern
All data providers implement `OHLCVProvider` ABC from `ingestion/base_provider.py`:
- `fetch_historical(symbol, interval, start, end) -> list[OHLCVCandle]`
- `fetch_latest(symbol, interval) -> list[OHLCVCandle]`
- Candles are normalized into `OHLCVCandle` dataclass (frozen, immutable)
- The scheduler and ingestion pipeline call only the ABC — never provider-specific code

### TDD RED→GREEN
Tests were written before implementation. The test suite in `backend/tests/` covers all pure functions with property-based edge cases.

### Upsert Semantics
- `market_data` table: `ON CONFLICT DO NOTHING` — candles are immutable historical facts
- `signals` table: `ON CONFLICT (symbol, interval) DO UPDATE` — signals are always refreshed on each scan

### pandas-ta-classic Column Names
Package is `pandas-ta-classic`, imported as `import pandas_ta_classic as ta`. Exact column names:
- `MACD_12_26_9`, `MACDs_12_26_9`, `MACDh_12_26_9`
- `BBU_20_2.0`, `BBL_20_2.0`, `BBP_20_2.0`
- `ADX_14`, `ATRr_14`, `EMA_50`, `EMA_200`

### Circular Import Avoidance
`STOCK_WATCHLIST` and `CCXT_CRYPTO_SYMBOLS` live in `app/core/watchlists.py` (not in `scheduler.py`) to avoid circular imports with `scanner.py`.

### run_in_threadpool
Synchronous library calls (yfinance, some CCXT ops) that run inside async FastAPI handlers must use `starlette.concurrency.run_in_threadpool`.

### MIN_CANDLES = 200
EMA-200 requires exactly 200 candles. `compute_indicators()` returns `None` if `len(df) < 200`. The scanner silently skips those assets.
<!-- GSD:conventions-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
