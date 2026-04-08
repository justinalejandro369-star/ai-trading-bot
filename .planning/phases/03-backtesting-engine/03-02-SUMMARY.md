---
phase: 03-backtesting-engine
plan: "02"
subsystem: backtesting-api
tags: [fastapi, backtest, vectorbt, threadpool, tdd, integration-tests]
dependency_graph:
  requires: [03-01]
  provides: [POST /api/backtest endpoint, BacktestRun persistence]
  affects: [04-paper-trading, 05-dashboard]
tech_stack:
  added: [starlette.concurrency.run_in_threadpool]
  patterns: [TDD red-green, async FastAPI route, run_in_threadpool for CPU-bound work, dependency override for integration tests]
key_files:
  created:
    - backend/app/api/routes/backtest.py
    - backend/tests/test_backtest_api.py
  modified:
    - backend/app/main.py
    - backend/app/backtesting/engine.py
    - backend/app/models/backtest.py
decisions:
  - "run_in_threadpool wraps run_backtest() — keeps async event loop non-blocking during vectorbt CPU computation"
  - "get_session imported from market_data.py (not redefined) — single session dependency shared across routes"
  - "BacktestRun persisted after every successful backtest — provides history for Phase 4 comparison"
  - "_safe_float() in engine.py converts NaN/inf to 0.0 — vectorbt returns NaN win_rate when total_trades < 2"
metrics:
  duration: "4 minutes"
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_created: 2
  files_modified: 3
---

# Phase 3 Plan 02: Backtest API Endpoint Summary

**One-liner:** FastAPI POST /api/backtest wiring run_backtest() via run_in_threadpool with BacktestRun persistence and 5 integration tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement POST /api/backtest + test_backtest_api.py (TDD RED→GREEN) | 3acb603 | backtest.py, test_backtest_api.py, engine.py |
| 2 | Register backtest router in main.py; full suite green; ruff passes | ae535b7 | main.py, models/backtest.py |

## What Was Built

**POST /api/backtest** (`backend/app/api/routes/backtest.py`):
- Accepts `BacktestRequest` (symbol, interval, commission, slippage, init_cash)
- Loads all OHLCV candles for the symbol+interval from `market_data` table via async session
- Raises HTTP 422 "Insufficient data" when no candles found OR fewer than MIN_CANDLES
- Runs `run_backtest()` wrapped in `run_in_threadpool()` — event loop stays non-blocking
- Persists `BacktestRun` to `backtest_runs` table on every successful run
- Returns `BacktestResult.to_dict()` with all 7 fields: sharpe_ratio, max_drawdown, win_rate, profit_factor, total_return, total_trades, equity_curve

**main.py** updated: imports `backtest_router`, registers at `/api` prefix, version bumped to `0.3.0`, description updated.

**Integration tests** (`backend/tests/test_backtest_api.py`): 5 tests, all green, using in-memory SQLite with real vectorbt execution (no mocking).

## Decisions Made

1. `run_in_threadpool` wraps `run_backtest()` — the vectorbt simulation is CPU-bound/synchronous; this keeps the FastAPI async event loop responsive during computation.
2. `get_session` imported from `market_data.py` rather than redefined — DRY principle, single source of truth for the session dependency used in tests' `dependency_overrides`.
3. `BacktestRun` persisted after each successful backtest — Phase 4 paper trading comparison requires historical backtest baselines in DB.
4. `_safe_float()` helper added to `engine.py` — vectorbt returns `NaN` for `win_rate` and `profit_factor` when fewer than 2 completed round-trips occur (e.g. only 1 trade entered). JSON serialization converts `NaN` to `null`, failing the `0.0 <= win_rate <= 1.0` assertion. Fix: convert NaN/inf to 0.0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] NaN win_rate from vectorbt when total_trades < 2**
- **Found during:** Task 1 (GREEN phase — test_win_rate_in_valid_range failed)
- **Issue:** With MIN_CANDLES+50 synthetic rows and the configured signal thresholds, vectorbt sometimes produces only 1 trade entry without a corresponding exit. `pf.stats()["Win Rate [%]"]` returns `NaN`, which Python serializes to `null` in JSON. The test assertion `0.0 <= win_rate <= 1.0` raises `TypeError: '<=' not supported between instances of 'float' and 'NoneType'`.
- **Fix:** Added `_safe_float()` helper in `engine.py` that converts `math.isnan(v) or math.isinf(v)` to the supplied fallback (0.0). Applied to `sharpe_ratio`, `win_rate`, `profit_factor`, and `total_return`.
- **Files modified:** `backend/app/backtesting/engine.py`
- **Commit:** 3acb603

**2. [Rule 1 - Bug] Unused `datetime` import in models/backtest.py**
- **Found during:** Task 2 (ruff check)
- **Issue:** `from datetime import datetime` was imported in `app/models/backtest.py` but never used. Ruff F401 error.
- **Fix:** Removed the unused import.
- **Files modified:** `backend/app/models/backtest.py`
- **Commit:** ae535b7

## Verification Results

```
PYTHONPATH=. uv run pytest tests/ -q
52 passed in 5.82s

uv run ruff check app/backtesting/ app/models/backtest.py app/api/routes/backtest.py
All checks passed!
```

Structural checks (all passing):
- `from starlette.concurrency import run_in_threadpool` — line 21 of backtest.py
- `await run_in_threadpool(` — line 107 of backtest.py
- `backtest_router` — lines 20 and 38 of main.py (import + include_router)
- `raise HTTPException(status_code=422` — lines 101 and 115 of backtest.py
- `session.add(run)` — line 133 of backtest.py

## Known Stubs

None — the endpoint loads real DB data, runs real vectorbt, and persists real results.

## Self-Check: PASSED
