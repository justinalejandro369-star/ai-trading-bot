---
phase: 02-analysis-engine
plan: "01"
subsystem: analysis-engine
tags: [indicators, technical-analysis, pandas-ta-classic, orm, migration, tdd]
dependency_graph:
  requires:
    - "01-data-foundation/01-01-PLAN.md (MarketData ORM model + Base)"
    - "01-data-foundation/01-03-PLAN.md (Alembic migration 001 + env.py)"
  provides:
    - "compute_indicators() pure function (used by 02-02 scanner)"
    - "IndicatorSet dataclass (data contract for 02-02 and 02-03)"
    - "TradingSignal ORM model (used by 02-02 for DB persistence)"
    - "Alembic migration 002 (signals table with composite PK)"
  affects:
    - "02-02-PLAN.md (imports compute_indicators, IndicatorSet, TradingSignal)"
    - "02-03-PLAN.md (reads signals table via TradingSignal)"
tech_stack:
  added:
    - "pandas-ta-classic==0.4.47 — technical indicator library (NOT pandas-ta)"
  patterns:
    - "Pure function design — compute_indicators() has zero DB access, fully testable in isolation"
    - "Dataclass for data contracts — IndicatorSet is a frozen value object"
    - "TDD RED/GREEN — tests written before implementation, committed separately"
    - "Shared DeclarativeBase — TradingSignal imports Base from market_data to share SQLAlchemy registry"
key_files:
  created:
    - "backend/app/analysis/__init__.py"
    - "backend/app/analysis/indicators.py"
    - "backend/app/models/signal.py"
    - "backend/alembic/versions/002_create_signals_table.py"
    - "backend/tests/__init__.py"
    - "backend/tests/conftest.py"
    - "backend/tests/test_indicators.py"
  modified:
    - "backend/pyproject.toml (added pandas-ta-classic>=0.4.47)"
    - "backend/uv.lock (updated)"
    - "backend/alembic/env.py (added TradingSignal import for Base.metadata)"
decisions:
  - "pandas-ta-classic (not pandas-ta) is the correct package — verified column names match research doc exactly"
  - "MIN_CANDLES=200 enforced as function contract, not a configuration value — EMA-200 needs exactly 200 rows"
  - "IndicatorSet uses float|None fields — None means insufficient lookback data, not an error"
  - "vol_sma_20 in IndicatorSet returns 0.0 for CoinGecko assets (volume=0.0) — scorer handles gracefully"
metrics:
  duration: "2 minutes"
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_created: 7
  files_modified: 3
---

# Phase 02 Plan 01: Indicator Engine — Foundation Summary

**One-liner:** pandas-ta-classic indicator engine with IndicatorSet dataclass, TradingSignal ORM model, Alembic migration 002, and 12-test TDD suite all passing green.

## What Was Built

### 1. pandas-ta-classic Dependency
Installed `pandas-ta-classic==0.4.47` via `uv add`. Critical distinction: the package name is `pandas-ta-classic` but the import is `import pandas_ta_classic as ta`. The wrong package (`pandas-ta`) was explicitly avoided.

### 2. TradingSignal ORM Model (`backend/app/models/signal.py`)
SQLAlchemy model for the `signals` table with composite PK `(symbol, interval)`. Stores the latest scan result per asset — one row is upserted on each analysis run. Fields cover direction (BUY/SELL/HOLD), confidence (0–100), regime (trending/ranging/volatile), prices, and four indicator values (rsi_14, macd_val, adx_14, atr_14). Imports `Base` from `market_data.py` to share the same declarative registry.

### 3. Alembic Migration 002 (`backend/alembic/versions/002_create_signals_table.py`)
Creates the `signals` table with `revision="002"` and `down_revision="001"`. Uses `sa.PrimaryKeyConstraint("symbol", "interval")` for upsert-safe composite PK. Also updated `alembic/env.py` to import `TradingSignal` so the new model is registered with `Base.metadata`.

### 4. Indicator Engine (`backend/app/analysis/indicators.py`)
Pure function `compute_indicators(df, symbol, interval) -> IndicatorSet | None` with no DB access. Returns `None` when the DataFrame has fewer than `MIN_CANDLES=200` rows. Computes 8 indicator families via pandas-ta-classic:
- RSI-14 → `rsi_14`
- MACD(12,26,9) → `macd_val`, `macd_signal`, `macd_hist` (using exact column name `MACD_12_26_9`)
- BBands(20,2) → `bb_upper`, `bb_lower`, `bb_pct` (using exact column name `BBP_20_2.0`)
- ADX-14 → `adx_14` (using exact column name `ADX_14`)
- ATR-14 → `atr_14`
- EMA-50, EMA-200 → `ema_50`, `ema_200`
- Volume SMA-20 → `vol_sma_20` (handles volume=0.0 gracefully)

### 5. Test Suite (TDD RED then GREEN)
12 tests in `backend/tests/test_indicators.py` with shared fixtures in `conftest.py`. Tests cover: insufficient data returns None, IndicatorSet type checking, all field types (float), close/volume pass-through, symbol/interval pass-through, zero-volume non-raise, MIN_CANDLES constant.

## Tasks Completed

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: Dependency + Model + Migration | 1c8affa | pandas-ta-classic installed, TradingSignal model, migration 002 |
| Task 2 RED: Failing tests | 90f1146 | 12 tests written, fail at import (indicators.py missing) |
| Task 2 GREEN: Implementation | 3d35315 | indicators.py implemented, all 12 tests pass |

## Test Results

```
12 passed in 0.07s
```

All tests pass. No external network calls. No DB required.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `compute_indicators()` is fully functional with real pandas-ta-classic computation. No mock data or placeholder values.

## Self-Check: PASSED

Files exist:
- FOUND: backend/app/analysis/indicators.py
- FOUND: backend/app/models/signal.py
- FOUND: backend/alembic/versions/002_create_signals_table.py
- FOUND: backend/tests/test_indicators.py
- FOUND: backend/tests/conftest.py

Commits exist:
- FOUND: 1c8affa (Task 1)
- FOUND: 90f1146 (Task 2 RED)
- FOUND: 3d35315 (Task 2 GREEN)
