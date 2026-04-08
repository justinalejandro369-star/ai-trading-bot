---
phase: 02-analysis-engine
plan: "03"
subsystem: analysis-scanner
tags: [scanner, apscheduler, upsert, integration-test, circular-import-fix]
dependency_graph:
  requires:
    - 02-01  # indicators.py compute_indicators(), MIN_CANDLES
    - 02-02  # signals.py score_signal(), regime.py detect_regime()
  provides:
    - scanner.py with scan_asset(), scan_all_assets(), analysis_scan_job()
    - 4th APScheduler job registered (analysis/5min)
    - watchlists.py (shared constants module)
  affects:
    - backend/app/ingestion/scheduler.py (4 jobs now)
    - backend/app/core/ (new watchlists.py)
tech_stack:
  added:
    - app/core/watchlists.py (new: shared watchlist constants)
  patterns:
    - ON CONFLICT (symbol, interval) DO UPDATE (upsert, not DO NOTHING)
    - in-memory SQLite for integration tests (aiosqlite)
    - ISO string timestamps for SQLite tz-aware compatibility
key_files:
  created:
    - backend/app/analysis/scanner.py
    - backend/app/core/watchlists.py
    - backend/tests/test_scanner.py
  modified:
    - backend/app/ingestion/scheduler.py
decisions:
  - "Watchlist constants extracted to app/core/watchlists.py to resolve circular import: scheduler imports scanner (analysis_scan_job), scanner was importing scheduler (STOCK_WATCHLIST). Both now import from watchlists.py"
  - "Timestamps stored as ISO strings in test SQLite inserts -- aiosqlite rejects timezone-aware pandas Timestamps directly"
  - "SCAN_INTERVAL is 1D only -- multi-timeframe deferred to Phase 7 per plan"
metrics:
  duration: "~4 minutes"
  completed: "2026-04-08"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
---

# Phase 2 Plan 03: Scanner Pipeline Summary

**One-liner:** Analysis scanner wiring indicators + signal scorer into a scheduled upsert pipeline via `scan_asset()` / `scan_all_assets()` / `analysis_scan_job()` with ON CONFLICT DO UPDATE semantics.

## What Was Built

### scanner.py

`backend/app/analysis/scanner.py` implements the complete analysis pipeline:

- `scan_asset(symbol, market, session)`: fetches up to `MIN_CANDLES + 20` candles from `market_data` for the given symbol/interval, computes `IndicatorSet` via `compute_indicators()`, derives ATR SMA for regime detection, calls `score_signal()` and `detect_regime()`, then upserts a `TradingSignal` row using ON CONFLICT DO UPDATE. Returns `None` if fewer than `MIN_CANDLES` rows exist.

- `scan_all_assets(session)`: iterates `STOCK_WATCHLIST` (5 stocks) then `CCXT_CRYPTO_SYMBOLS` (3 crypto), calling `scan_asset()` for each. Per-asset exceptions are caught and logged so one failure does not stop the scan.

- `analysis_scan_job()`: APScheduler wrapper that creates its own DB session via `async_session_factory()` and calls `scan_all_assets()`. Top-level exceptions are caught to prevent scheduler crashes.

### watchlists.py (new)

`backend/app/core/watchlists.py` extracted `STOCK_WATCHLIST`, `STOCK_INTERVALS`, `CCXT_CRYPTO_SYMBOLS`, `CCXT_INTERVALS` from `scheduler.py`. Both `scheduler.py` and `scanner.py` import from this module, eliminating the circular import.

### scheduler.py (updated)

Added `analysis_scan_job` as the 4th APScheduler job (every 5 minutes, `id="analysis_scan"`). The lifespan docstring updated to reflect 4 jobs.

### test_scanner.py

6 integration tests using in-memory SQLite (`sqlite+aiosqlite:///:memory:`):
1. `test_scan_asset_returns_none_when_insufficient_candles` -- 50 candles returns None
2. `test_scan_asset_returns_trading_signal_when_sufficient_candles` -- 250 candles returns TradingSignal
3. `test_scan_asset_upserts_signal_to_db` -- two scans produce exactly one DB row
4. `test_scan_asset_updates_existing_signal_timestamp` -- second scan refreshes scanned_at
5. `test_scan_all_assets_processes_symbols_with_sufficient_data` -- batch scan creates signal rows
6. `test_scan_asset_zero_volume_does_not_raise` -- CoinGecko zero-volume handled gracefully

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import between scanner.py and scheduler.py**
- **Found during:** Task 2, when adding `from app.analysis.scanner import analysis_scan_job` to scheduler.py
- **Issue:** scanner.py imported `STOCK_WATCHLIST`, `CCXT_CRYPTO_SYMBOLS` from scheduler.py; scheduler.py now imports `analysis_scan_job` from scanner.py -- creating a circular dependency at module initialization
- **Fix:** Extracted watchlist constants to `app/core/watchlists.py`. Both modules import from there. scheduler.py still re-exports the names via `__all__` for backward compatibility.
- **Files modified:** `backend/app/core/watchlists.py` (new), `backend/app/ingestion/scheduler.py`, `backend/app/analysis/scanner.py`
- **Commit:** 32c5432

**2. [Rule 1 - Bug] SQLite rejects timezone-aware pandas Timestamps in test inserts**
- **Found during:** Task 1, first test run (RED->GREEN iteration)
- **Issue:** `sqlite3.ProgrammingError: type 'Timestamp' is not supported` when inserting `pd.Timestamp` with timezone info into aiosqlite
- **Fix:** Convert timestamps to ISO string via `.isoformat()` before passing to `session.execute()` in `_insert_candles()` test helper
- **Files modified:** `backend/tests/test_scanner.py`
- **Commit:** 4241b03

## Phase 2 Requirements Coverage

| Requirement | Plan | Status |
|-------------|------|--------|
| ANLYS-01: compute_indicators() returns RSI, MACD, BB, ADX, EMA, volume | 02-01 | Complete |
| ANLYS-02: score_signal() returns BUY/SELL/HOLD with 0-100 confidence | 02-02 | Complete |
| ANLYS-04: scan_all_assets() scans stocks + crypto, /api/signals/top ranks by confidence | 02-03 | Complete |
| ANLYS-06: detect_regime() classifies trending/ranging/volatile | 02-02 | Complete |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (TDD - RED+GREEN) | 4241b03 | feat(02-03): implement scanner.py and add test_scanner.py |
| 2 (scheduler + fix) | 32c5432 | feat(02-03): register analysis_scan_job as 4th APScheduler job |

## Known Stubs

None. All data flows are wired end-to-end. `scan_asset()` reads from real DB tables, computes real indicators, and writes real signal rows.

## Self-Check: PASSED
