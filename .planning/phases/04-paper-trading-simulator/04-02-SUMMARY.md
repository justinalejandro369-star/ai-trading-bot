---
phase: 04-paper-trading-simulator
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, apscheduler, python, paper-trading, integration-tests]

# Dependency graph
requires:
  - phase: 04-paper-trading-simulator
    plan: 01
    provides: PaperAccount, PaperPosition, EquitySnapshot ORM models; fill_order(); compute_equity()
  - phase: 03-backtesting-engine
    provides: BacktestRun ORM model with equity_curve_data()
  - phase: 01-data-foundation
    provides: MarketData ORM model; get_session() FastAPI dependency; async_session_factory
provides:
  - FastAPI router with 5 paper trading endpoints (PAPER-01 through PAPER-04 complete at API level)
  - APScheduler equity_snapshot_job (max_instances=1, 5-minute interval, DB-only, no external API)
  - Updated scheduler.py with 5th registered job (paper_equity_snapshot)
  - Updated main.py with paper_trading_router at /api prefix, version 0.4.0
  - 7 GREEN integration tests covering all endpoint contracts
affects: [frontend-dashboard, equity-curve-charts, backtest-comparison-charts]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Route handler delegates all business logic to engine.py — routes only handle DB I/O and HTTP errors"
    - "Batch price query via symbol IN (...) + ORDER BY timestamp DESC to avoid N+1 DB round-trips"
    - "Equity snapshot inserted inline after every order fill (not scheduler-only) for immediate equity curve availability"
    - "max_instances=1 on APScheduler job prevents duplicate snapshot rows if job runs beyond interval"
    - "ASGITransport + in-memory SQLite integration test pattern reused from test_backtest_api.py"

key-files:
  created:
    - backend/app/api/routes/paper_trading.py
    - backend/app/paper_trading/snapshot.py
  modified:
    - backend/app/ingestion/scheduler.py
    - backend/app/main.py
    - backend/tests/test_paper_trading_api.py

key-decisions:
  - "Equity snapshot inserted inline after every fill (not just from scheduler job) — ensures /equity endpoint returns data immediately after first order without waiting 5 minutes"
  - "Batch MarketData price query uses WHERE symbol IN (...) ORDER BY timestamp DESC with Python-side dedup — avoids one subquery per symbol"
  - "SELL with remaining qty <= 0 deletes PaperPosition row — no zero-quantity ghost rows in paper_positions table"
  - "snapshot.py job wraps all account processing in a single async_session_factory() context and commits once — minimises round-trips per job run"

patterns-established:
  - "Paper trading router follows backtest.py import pattern (get_session from market_data, Depends(get_session))"
  - "Integration tests use fresh engine per fixture, monkeypatch override of get_session, ASGITransport"

requirements-completed: [PAPER-01, PAPER-02, PAPER-03, PAPER-04]

# Metrics
duration: 8min
completed: 2026-04-08
---

# Phase 4 Plan 2: Paper Trading REST API, Snapshot Job, and Integration Tests Summary

**Five paper trading REST endpoints wired to the Plan-01 engine, APScheduler equity_snapshot_job registered with max_instances=1, and all 7 RED integration test stubs turned GREEN (20/20 tests passing).**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-08T13:39:59Z
- **Completed:** 2026-04-08T13:48:00Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 updated)

## Accomplishments

- `paper_trading.py` router: 5 endpoints covering PAPER-01 through PAPER-04
  - POST /api/paper/accounts — create account with configurable starting balance, slippage, commission
  - GET /api/paper/accounts/{id} — account summary with live equity (batch price query, no N+1)
  - POST /api/paper/accounts/{id}/orders — BUY/SELL with slippage, weighted-avg cost basis, inline snapshot
  - GET /api/paper/accounts/{id}/equity — time-series equity curve from EquitySnapshot rows
  - GET /api/paper/accounts/{id}/compare — paper vs. backtest equity curves (null-safe when unlinked)
- `snapshot.py`: `equity_snapshot_job()` — DB-only APScheduler job, no external API calls, handles no-position accounts
- `scheduler.py`: 5th job (`paper_equity_snapshot`) registered with `max_instances=1` and `misfire_grace_time=60`
- `main.py`: paper_trading_router included at /api prefix, version bumped to 0.4.0
- All 7 integration tests implemented and GREEN; full 20/20 test suite passes

## Task Commits

Each task was committed atomically:

1. **Task 1: REST router — five paper trading endpoints** - `0d65a46` (feat)
2. **Task 2: Snapshot job + scheduler registration + main.py wiring + integration tests GREEN** - `14fc248` (feat)

## Files Created/Modified

- `backend/app/api/routes/paper_trading.py` — 5-endpoint FastAPI router (new)
- `backend/app/paper_trading/snapshot.py` — APScheduler equity_snapshot_job (new)
- `backend/app/ingestion/scheduler.py` — added 5th job registration and import (updated)
- `backend/app/main.py` — included paper_trading_router, version 0.4.0 (updated)
- `backend/tests/test_paper_trading_api.py` — 7 integration tests implemented (updated)

## Decisions Made

- Equity snapshots are recorded inline after every order fill (in addition to the 5-minute scheduler job). This ensures the `/equity` endpoint returns data immediately after the first order, without waiting up to 5 minutes for the next scheduled run.
- Batch MarketData query uses `WHERE symbol IN (...)` + Python-side dedup (keep first occurrence per symbol from timestamp-DESC ordering) rather than one subquery per symbol — avoids N+1 and keeps the query simple.
- SELL fills that reduce position quantity to zero delete the PaperPosition row entirely, preventing ghost rows with `quantity=0` from affecting equity calculations.
- `snapshot.py` commits once at the end of a full pass over all accounts — single transaction minimises DB round-trips per job run.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — all endpoints return live data from SQLite. No hardcoded placeholders.

## User Setup Required

None - no external service configuration required.

## Self-Check

Files exist and commits verified below.

## Self-Check: PASSED

Files confirmed:
- FOUND: backend/app/api/routes/paper_trading.py
- FOUND: backend/app/paper_trading/snapshot.py

Commits confirmed:
- 0d65a46 — feat(04-02): paper trading REST router with 5 endpoints
- 14fc248 — feat(04-02): snapshot job, scheduler registration, main.py wiring, tests GREEN

---
*Phase: 04-paper-trading-simulator*
*Completed: 2026-04-08*
