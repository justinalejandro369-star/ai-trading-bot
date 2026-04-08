---
phase: 01-data-foundation
plan: 01
subsystem: database
tags: [python, sqlalchemy, alembic, timescaledb, fastapi, pydantic, yfinance, coingecko, sqlite, docker]

# Dependency graph
requires: []
provides:
  - OHLCVCandle frozen dataclass (9 typed fields: symbol, market, interval, timestamp, open, high, low, close, volume)
  - OHLCVProvider ABC with fetch_historical + fetch_latest abstract async methods
  - normalize_yfinance() converting yfinance DataFrames to OHLCVCandle list
  - normalize_coingecko() converting CoinGecko OHLC lists to OHLCVCandle list (volume=0.0 known limitation)
  - MarketData SQLAlchemy ORM model with composite PK (symbol, interval, timestamp)
  - Alembic migration 001: CREATE TABLE market_data + create_hypertable() with 7-day chunk interval
  - alembic/env.py with include_object() filter preventing TimescaleDB index drops on autogenerate
  - docker-compose.yml launching timescale/timescaledb:latest-pg16
  - pydantic-settings Settings class for DATABASE_URL, FINNHUB_API_KEY, COINGECKO_API_KEY
  - async_session_factory and get_session() async context manager
  - .env.example with placeholder values; no real keys committed
affects: [02-data-foundation, 03-signal-engine, 04-backtesting, 05-paper-trading, 06-dashboard, 07-intelligence]

# Tech tracking
tech-stack:
  added:
    - fastapi==0.115+
    - uvicorn[standard]
    - sqlalchemy==2.0.49
    - alembic==1.18.4
    - asyncpg==0.31.0
    - psycopg2-binary==2.9.11
    - aiosqlite
    - pydantic-settings
    - pydantic
    - yfinance==1.2.1
    - pycoingecko==3.2.0
    - ccxt
    - httpx==0.28.1
    - websockets
    - python-dotenv
    - apscheduler
    - pandas
    - pytest==9.0.3
    - pytest-asyncio==1.3.0
    - pytest-timeout
    - ruff
    - mypy
  patterns:
    - Provider ABC pattern: new data sources implement OHLCVProvider without touching other modules
    - Normalizer pattern: all provider-specific formats pass through normalizer.py before DB
    - Frozen dataclass for immutable candle records
    - pydantic-settings for type-safe env var configuration
    - SQLite/PostgreSQL swap via DATABASE_URL env var
    - ON CONFLICT DO NOTHING for idempotent OHLCV upserts
    - Alembic include_object() filter for TimescaleDB index safety

key-files:
  created:
    - backend/app/ingestion/base_provider.py
    - backend/app/ingestion/normalizer.py
    - backend/app/models/market_data.py
    - backend/app/core/config.py
    - backend/app/core/database.py
    - backend/alembic/env.py
    - backend/alembic/versions/001_create_ohlcv_hypertable.py
    - backend/pyproject.toml
    - docker-compose.yml
    - .env.example
    - .gitignore
    - tests/conftest.py
    - tests/test_provider_interface.py
    - tests/test_db_schema.py
  modified: []

key-decisions:
  - "normalize_coingecko() sets volume=0.0 with inline comment — CoinGecko OHLC endpoint has no volume field; future enhancement joins with market_chart endpoint"
  - "Alembic migration uses raw SQL op.execute() not op.create_table() because create_hypertable() must be called as a TimescaleDB extension function"
  - "Hypertable call wrapped in try/except ProgrammingError to support SQLite dev environment without Docker"
  - "alembic/env.py converts asyncpg URLs to psycopg2 for migration execution — asyncpg is runtime-only, Alembic needs synchronous access"
  - ".gitignore added to prevent __pycache__, .env, *.db files from being committed"

patterns-established:
  - "Pattern: Provider ABC — any new data source implements OHLCVProvider without modifying any other file"
  - "Pattern: Normalizer first — all provider output passes through normalizer.py before reaching storage or analysis code"
  - "Pattern: SQLite default — DATABASE_URL defaults to sqlite+aiosqlite:///./dev.db; tests run without Docker"
  - "Pattern: TDD — write failing tests first, then implement; all 9 tests GREEN before commit"

requirements-completed: [DATA-04, DATA-05]

# Metrics
duration: 4min
completed: 2026-04-08
---

# Phase 1 Plan 1: Data Foundation — OHLCV Contracts and Schema Summary

**OHLCVCandle frozen dataclass + OHLCVProvider ABC establish the canonical data contract; MarketData ORM model with TimescaleDB hypertable migration and SQLite dev fallback wire the storage layer**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-08T05:06:56Z
- **Completed:** 2026-04-08T05:11:29Z
- **Tasks:** 2
- **Files modified:** 14 created, 0 modified

## Accomplishments

- OHLCVCandle frozen dataclass and OHLCVProvider ABC define the immutable data contract all phases 2-7 depend on
- normalize_yfinance() and normalize_coingecko() implemented and tested — CoinGecko volume=0.0 limitation documented inline
- MarketData ORM model with composite PK (symbol, interval, timestamp) matches TimescaleDB DDL exactly
- Alembic migration 001 creates market_data + calls create_hypertable() with 7-day chunk interval; SQLite dev fallback works without Docker
- Full TDD cycle: 5 RED tests -> implementation -> 5 GREEN, then 4 RED tests -> implementation -> 4 GREEN; all 9 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold, provider interface, and normalizer** - `85c38c1` (feat)
2. **Task 2: TimescaleDB schema, SQLAlchemy model, Alembic migration, and Docker Compose** - `f5b0795` (feat)
3. **Chore: .gitignore and scaffold files** - `1ebf6e9` (chore)

_Note: TDD tasks include test (RED) then feat (GREEN) in same commit for clarity_

## Files Created/Modified

- `backend/app/ingestion/base_provider.py` - OHLCVCandle frozen dataclass + OHLCVProvider ABC
- `backend/app/ingestion/normalizer.py` - normalize_yfinance() and normalize_coingecko() functions
- `backend/app/models/market_data.py` - SQLAlchemy MarketData ORM model with composite PK
- `backend/app/core/config.py` - pydantic-settings Settings class for env vars
- `backend/app/core/database.py` - async engine, async_session_factory, get_session() context manager
- `backend/alembic/env.py` - Alembic env with include_object() filter + URL conversion for sync migrations
- `backend/alembic/versions/001_create_ohlcv_hypertable.py` - DDL migration + create_hypertable() + SQLite fallback
- `backend/pyproject.toml` - Project manifest with all dependencies via uv
- `backend/uv.lock` - Locked dependency resolution for reproducible builds
- `docker-compose.yml` - timescale/timescaledb:latest-pg16 on port 5432
- `.env.example` - Placeholder values for DATABASE_URL, FINNHUB_API_KEY, COINGECKO_API_KEY
- `.gitignore` - Python artifacts, .env, *.db excluded from version control
- `tests/conftest.py` - sample_yfinance_df and sample_coingecko_raw fixtures
- `tests/test_provider_interface.py` - 5 tests for OHLCVCandle, OHLCVProvider, normalizers
- `tests/test_db_schema.py` - 4 tests for MarketData columns, PK, SQLite default, upsert idempotency

## Decisions Made

- normalize_coingecko() sets volume=0.0 with inline comment explaining the limitation — OHLCVCandle.volume is non-optional float, CoinGecko OHLC endpoint has no volume field; joining with market_chart endpoint is deferred
- Alembic migration uses raw SQL op.execute() instead of op.create_table() because create_hypertable() is a TimescaleDB function that must be called post-table-creation
- Hypertable call wrapped in try/except sqlalchemy.exc.ProgrammingError to support SQLite dev environment without Docker — plain table is used as fallback
- alembic/env.py URL conversion: asyncpg -> psycopg2 for migration execution since asyncpg is runtime-only and Alembic requires synchronous access to the database

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added .gitignore**
- **Found during:** Task 2 (post-commit cleanup)
- **Issue:** No .gitignore existed; __pycache__, .env, *.db files would be committed inadvertently
- **Fix:** Created comprehensive .gitignore for Python artifacts, .env files, and generated files
- **Files modified:** .gitignore
- **Verification:** git status shows __pycache__ directories as ignored
- **Committed in:** 1ebf6e9 (chore commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** .gitignore essential for security (prevents API key .env files from being committed). No scope creep.

## Issues Encountered

None — plan executed cleanly. The alembic/env.py required URL conversion logic (asyncpg -> psycopg2) which was anticipated by the plan but not explicitly written out; implemented correctly on first attempt.

## Known Stubs

- `normalize_coingecko()` sets `volume=0.0` for all candles. This is an intentional stub documented inline with `# Known limitation: CoinGecko OHLC endpoint returns no volume field. Future enhancement: join with market_chart endpoint.` Plan 02 (providers) may resolve this if CoinGecko market_chart data is joined; otherwise it remains until crypto volume data is needed for signal generation.

## User Setup Required

None — all tests use SQLite in-memory. Docker Compose is provided for when TimescaleDB is needed, but is not required to run the test suite.

## Next Phase Readiness

- OHLCVCandle and OHLCVProvider contracts are ready for Plan 02 (concrete provider implementations: yfinance, CoinGecko)
- MarketData model and Alembic migration are ready; run `docker-compose up db` then `uv run alembic upgrade head` to provision TimescaleDB
- Settings class loads API keys from .env; copy .env.example to .env and fill in keys before running providers

---
*Phase: 01-data-foundation*
*Completed: 2026-04-08*
