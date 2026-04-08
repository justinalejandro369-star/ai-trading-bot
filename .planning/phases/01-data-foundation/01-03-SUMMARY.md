---
phase: 01-data-foundation
plan: 03
subsystem: ingestion-scheduler-api
tags: [python, apscheduler, fastapi, sqlalchemy, sqlite, yfinance, ccxt, coingecko, tdd]

# Dependency graph
requires:
  - OHLCVCandle frozen dataclass (from 01-01)
  - OHLCVProvider ABC (from 01-01)
  - YfinanceProvider, CoinGeckoProvider, CCXTProvider (from 01-02)
  - async_session_factory, get_session() (from 01-01)
  - MarketData ORM model (from 01-01)
provides:
  - upsert_candles() async function with ON CONFLICT (symbol, interval, timestamp) DO NOTHING
  - APScheduler with 3 jobs: stock_incremental (5min), crypto_coingecko (30min), crypto_ccxt (15min)
  - FastAPI lifespan context manager starting/stopping AsyncIOScheduler
  - GET /api/market-data/{symbol}?interval={}&limit={} REST endpoint
  - VALID_INTERVALS whitelist enforcement and limit le=1000
  - FastAPI app wired with scheduler lifespan and market-data router
affects: [02-signal-engine, 03-backtesting, 04-paper-trading, 05-dashboard]

# Tech tracking
tech-stack:
  added:
    - greenlet==3.3.2 (required by SQLAlchemy async engine — was missing from pyproject.toml)
  patterns:
    - TDD: RED (failing tests) committed first, then GREEN (implementation) committed separately
    - APScheduler AsyncIOScheduler integrated via FastAPI lifespan context manager
    - upsert_candles() uses raw SQL text() with named params for idempotent ON CONFLICT DO NOTHING
    - FastAPI Depends() requires async generator — separate get_session() defined in route module
    - In-memory SQLite DDL initialization in test module for endpoint tests without real DB
    - STOCK_INTERVALS use lowercase yfinance keys (1h/1d) to match YFINANCE_MAX_HISTORY exactly

key-files:
  created:
    - backend/app/ingestion/upsert.py
    - backend/app/ingestion/scheduler.py
    - backend/app/api/__init__.py
    - backend/app/api/routes/__init__.py
    - backend/app/api/routes/market_data.py
    - backend/app/main.py
    - tests/test_timeframes.py
    - tests/test_scheduler.py
  modified:
    - backend/pyproject.toml (greenlet added)
    - backend/uv.lock (updated)

key-decisions:
  - "STOCK_INTERVALS uses lowercase yfinance keys ['1m','5m','15m','1h','1d'] — YFINANCE_MAX_HISTORY keys are lowercase; uppercase variants ('1H','1D') are not valid yfinance interval strings"
  - "CCXT_INTERVALS uses app-convention uppercase ['1m','5m','15m','1H','4H','1D'] — CCXT_INTERVAL_MAP translates these to Binance lowercase; the test test_all_ccxt_intervals_are_valid_ccxt_keys enforces this"
  - "get_session() defined as async generator in market_data.py for FastAPI Depends() — the @asynccontextmanager version in database.py is for non-FastAPI callers (scheduler jobs)"
  - "greenlet added to pyproject.toml — SQLAlchemy 2.0 async requires greenlet at runtime even though it was implicitly installed before"
  - "APScheduler (not Celery+Redis) locked in by Phase 1 STATE.md decision — single-process MVP, no external queue required"

requirements-completed: [DATA-03]

# Metrics
duration: 4min
completed: 2026-04-08
---

# Phase 1 Plan 3: Scheduler, Upsert, and Market Data API Summary

**APScheduler integrated into FastAPI lifespan with 3 jobs (stock 5min, CoinGecko 30min, CCXT 15min); upsert_candles() with ON CONFLICT DO NOTHING closes the ingestion loop; GET /api/market-data/{symbol} completes Phase 1 data pipeline**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-08T05:22:23Z
- **Completed:** 2026-04-08T05:26:00Z
- **Tasks:** 2
- **Files modified:** 8 created, 2 modified

## Accomplishments

- upsert_candles() implemented with parameterized ON CONFLICT (symbol, interval, timestamp) DO NOTHING — tested idempotent via 3 separate in-memory SQLite test cases
- APScheduler AsyncIOScheduler starts in FastAPI lifespan before yield, shuts down after yield; 3 jobs registered with misfire_grace_time to prevent pile-up
- All 6 timeframes covered: stocks via yfinance (1m/5m/15m/1h/1d), crypto intraday via CCXT (1m/5m/15m/1H/4H/1D), crypto daily via CoinGecko (4H)
- GET /api/market-data/{symbol} enforces VALID_INTERVALS whitelist, limit le=1000, returns JSON array ordered by timestamp DESC
- Full test suite: 36/36 tests pass across 6 test files; all new tests written TDD (RED first, then GREEN)

## Task Commits

1. **Task 1 RED: Failing tests for upsert, scheduler, timeframes** - `b6b1523` (test)
2. **Task 1+2 GREEN: upsert, scheduler, API implementation** - `c5cbcbb` (feat)

## Files Created/Modified

- `backend/app/ingestion/upsert.py` - upsert_candles() with ON CONFLICT DO NOTHING; idempotent, parameterized
- `backend/app/ingestion/scheduler.py` - STOCK_WATCHLIST/INTERVALS, CCXT_CRYPTO_SYMBOLS/INTERVALS constants; 3 job functions; scheduler=AsyncIOScheduler(); lifespan context manager
- `backend/app/api/__init__.py` - API package init
- `backend/app/api/routes/__init__.py` - Routes package init
- `backend/app/api/routes/market_data.py` - GET /market-data/{symbol}; VALID_INTERVALS whitelist; limit ge=1,le=1000; orders by timestamp DESC; get_session() async generator for FastAPI Depends()
- `backend/app/main.py` - FastAPI app with title="Trading Bot API"; lifespan=lifespan; includes market_data_router at prefix="/api"
- `tests/test_timeframes.py` - 8 tests: yfinance/CCXT interval validation, upsert idempotency, 3 endpoint tests
- `tests/test_scheduler.py` - 4 tests: 3-job count, 5min/30min intervals, stock_incremental_job mocked

## Decisions Made

- STOCK_INTERVALS uses lowercase yfinance keys (`1h`, `1d`) — YFINANCE_MAX_HISTORY only has lowercase; test `test_all_stock_intervals_are_valid_yfinance_keys` guards this invariant
- CCXT_INTERVALS uses uppercase app-convention (`1H`, `4H`, `1D`) — CCXT_INTERVAL_MAP translates these; test `test_all_ccxt_intervals_are_valid_ccxt_keys` guards this
- `get_session()` as async generator in market_data.py — FastAPI `Depends()` requires an async generator (not `@asynccontextmanager`); the database.py version remains for scheduler jobs
- `greenlet` added to pyproject.toml — SQLAlchemy 2.0 async runtime requires it; was absent from explicit dependencies

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] STOCK_INTERVALS lowercased to match YFINANCE_MAX_HISTORY keys**
- **Found during:** Task 1 (implementing scheduler)
- **Issue:** Plan specified STOCK_INTERVALS = ["1m", "5m", "15m", "1H", "1D"] but YFINANCE_MAX_HISTORY keys are lowercase ("1h", "4h", "1d"); uppercase variants would raise ValueError at runtime
- **Fix:** Used ["1m", "5m", "15m", "1h", "1d"] — the test `test_all_stock_intervals_are_valid_yfinance_keys` confirms all intervals are valid YFINANCE_MAX_HISTORY keys
- **Files modified:** backend/app/ingestion/scheduler.py
- **Impact:** 4h omitted from STOCK_INTERVALS (yfinance 4h support is unreliable on free tier); CCXT covers 4H for crypto

**2. [Rule 3 - Blocking] Added greenlet to pyproject.toml**
- **Found during:** Task 1 (running upsert tests)
- **Issue:** Tests failed with "the greenlet library is required to use this function" — SQLAlchemy async engine requires greenlet at runtime
- **Fix:** `uv add greenlet` — greenlet==3.3.2 added to pyproject.toml and uv.lock
- **Files modified:** backend/pyproject.toml, backend/uv.lock

**3. [Rule 3 - Blocking] FastAPI Depends() requires async generator, not @asynccontextmanager**
- **Found during:** Task 2 (endpoint tests)
- **Issue:** Plan specified `Depends(get_session)` using the database.py `@asynccontextmanager`; FastAPI cannot use a context manager directly as a dependency
- **Fix:** Defined a separate `async def get_session()` async generator in market_data.py that yields from `async_session_factory()`
- **Files modified:** backend/app/api/routes/market_data.py

**4. [Rule 3 - Blocking] In-memory SQLite for endpoint tests needs DDL initialization**
- **Found during:** Task 2 (endpoint tests)
- **Issue:** Test for empty-symbol endpoint failed with "no such table: market_data" — module-level engine for endpoint tests has no schema
- **Fix:** Added `_init_endpoint_db()` function called at module import time to CREATE TABLE market_data in the test engine
- **Files modified:** tests/test_timeframes.py

---

**Total deviations:** 4 auto-fixed (2 bugs, 2 blocking issues)
**Impact on plan:** All deviations are correctness fixes, no scope changes. Behavior spec is fully met.

## Known Stubs

None — all data flows are wired end to end. The endpoint returns real DB data, upsert stores real candles, scheduler fetches from real providers.

## Phase 1 Complete

This is the final plan in Phase 1. All three plans are complete:
- 01-01: OHLCVCandle contract, MarketData schema, Alembic migration, Docker Compose
- 01-02: YfinanceProvider, CoinGeckoProvider, CCXTProvider, FinnhubProvider
- 01-03: upsert_candles(), APScheduler jobs, GET /api/market-data/{symbol} REST endpoint

Phase 2 (Analysis Engine) can now begin. The full data pipeline is operational: scheduler fetches OHLCV from external APIs, upsert stores idempotently, REST endpoint exposes the data for downstream analysis.

## Self-Check: PASSED

- All 8 files created: FOUND
- Commits b6b1523 (test/RED) and c5cbcbb (feat/GREEN): FOUND
- Full test suite 36/36 passing: CONFIRMED
- App imports cleanly: CONFIRMED

---
*Phase: 01-data-foundation*
*Completed: 2026-04-08*
