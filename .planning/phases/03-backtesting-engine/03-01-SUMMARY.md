---
phase: 03-backtesting-engine
plan: 01
subsystem: backtesting
tags: [vectorbt, pandas, numpy, sqlalchemy, alembic, pytest, tdd, look-ahead-bias]

# Dependency graph
requires:
  - phase: 02-analysis-engine
    provides: compute_indicators(), score_signal(), THRESHOLD constant, MIN_CANDLES, IndicatorSet, signals.py scoring weights

provides:
  - run_backtest() pure function (engine.py) — vectorbt core, no DB/FastAPI coupling
  - BacktestResult dataclass and BacktestRequest Pydantic model (models.py)
  - BacktestRun SQLAlchemy ORM model (backtest.py) with backtest_runs table
  - Alembic migration 003 (revision=003, down_revision=002) for backtest_runs table
  - TDD test suite (test_backtest.py) with BKTS-02 look-ahead bias audit test

affects: [03-02-PLAN.md, phase-04-paper-trading, phase-05-dashboard]

# Tech tracking
tech-stack:
  added: [vectorbt>=0.28.5, numba (transitive), llvmlite (transitive)]
  patterns:
    - vectorbt Portfolio.from_signals() as backtesting core
    - shift(1).fillna(False).astype(bool) for look-ahead bias prevention
    - fees= and slippage= params for transaction cost modeling
    - pandas override in uv to resolve vectorbt<3.0 vs project pandas>=3.0 conflict

key-files:
  created:
    - backend/app/backtesting/__init__.py
    - backend/app/backtesting/engine.py
    - backend/app/backtesting/models.py
    - backend/app/models/backtest.py
    - backend/alembic/versions/003_create_backtest_runs_table.py
    - backend/tests/test_backtest.py
  modified:
    - backend/pyproject.toml
    - backend/uv.lock
    - backend/alembic/env.py

key-decisions:
  - "vectorbt pandas override: vectorbt 0.28.5 declares pandas<3.0 but works fine at runtime with pandas 3.x; resolved via [tool.uv] override-dependencies and environments (darwin/linux only)"
  - "BKTS-02 audit test uses shift(-1) for true look-ahead bias: original plan used close>close.shift(1) which is NOT future-peeking; correct test uses close.shift(-1)>close to create truly cheating signals"
  - "requires-python pinned to >=3.11,<3.14 to prevent uv from trying Windows Python 3.14 resolution path"
  - "Pre-existing circular import in scanner.py/scheduler.py (test_analysis_api, test_scanner) deferred — not caused by Phase 03"

patterns-established:
  - "Pure function pattern: engine.py has zero DB/FastAPI imports — testable in full isolation"
  - "TDD RED/GREEN: test file committed before implementation, RED confirmed by ImportError"
  - "Vectorized signal computation: replicate score_signal() logic across full DataFrame using boolean Series arithmetic"

requirements-completed: [BKTS-01, BKTS-02, BKTS-03, BKTS-04]

# Metrics
duration: 8min
completed: 2026-04-08
---

# Phase 03 Plan 01: Backtesting Engine Core Summary

**vectorbt 0.28.5 backtesting engine with shift(1) look-ahead bias prevention, configurable transaction costs, BacktestRun ORM, Alembic migration 003, and 9-test TDD suite all green**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-08T13:04:07Z
- **Completed:** 2026-04-08T13:12:13Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Installed vectorbt 0.28.5 and resolved pandas>=3.0 vs vectorbt's declared pandas<3.0 constraint via uv override-dependencies
- Implemented run_backtest() pure function: vectorized entry/exit signal computation mirroring Phase 2 score_signal() logic, shift(1) look-ahead bias prevention, configurable commission/slippage fees
- Created BacktestResult dataclass (7 fields), BacktestRequest Pydantic model, BacktestRun SQLAlchemy ORM, and Alembic migration 003 (revision=003, down_revision=002)
- All 9 tests pass including BKTS-02 look-ahead bias audit test (test_shift1_prevents_look_ahead_bias)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install vectorbt and define data contracts** - `d7d877a` (feat)
2. **Task 2 RED: Failing tests (TDD RED)** - `fa8e27b` (test)
3. **Task 2 GREEN: Implement engine.py (TDD GREEN)** - `37d7c56` (feat)

_Note: TDD task has two commits (test RED then feat GREEN)_

## Files Created/Modified

- `backend/pyproject.toml` - Added vectorbt>=0.28.5, platform environments restriction, pandas override
- `backend/uv.lock` - Updated with vectorbt 0.28.5 and transitive deps (numba, llvmlite, etc.)
- `backend/app/backtesting/__init__.py` - Empty module init
- `backend/app/backtesting/models.py` - BacktestResult dataclass + BacktestRequest Pydantic model
- `backend/app/backtesting/engine.py` - run_backtest() pure function with vectorbt core and look-ahead prevention
- `backend/app/models/backtest.py` - BacktestRun SQLAlchemy ORM (backtest_runs table, integer PK)
- `backend/alembic/versions/003_create_backtest_runs_table.py` - Migration 003 with all 14 columns
- `backend/alembic/env.py` - Added BacktestRun import to register with Base.metadata
- `backend/tests/test_backtest.py` - 9-test TDD suite including BKTS-02 and BKTS-04 tests

## Decisions Made

1. **vectorbt pandas override:** vectorbt 0.28.5 declares `pandas>=2.0,<3.0` in its PyPI metadata but works fine at runtime with pandas 3.x (confirmed via direct pip install). Fixed by adding `[tool.uv] override-dependencies = ["pandas>=3.0.2"]` and restricting environments to darwin/linux in pyproject.toml. Required also pinning `requires-python = ">=3.11,<3.14"` to avoid failing Windows resolution.

2. **BKTS-02 audit test signal correction:** Plan's original audit test used `close > close.shift(1)` as the "biased" signal — this is a momentum signal, NOT a future-peeking signal. With seed=7 it failed because momentum signals can underperform with transaction costs. Fixed to use `close.shift(-1) > close` which genuinely peeks at next-bar price — biased Sharpe=11.2 vs honest Sharpe=-2.1, proving shift(1) works correctly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] uv dependency resolution failure for vectorbt vs pandas 3.x**
- **Found during:** Task 1 (Install vectorbt)
- **Issue:** uv's cross-platform dependency resolver rejected vectorbt because vectorbt's PyPI metadata says `pandas>=2.0,<3.0` but the project has `pandas>=3.0.2`. The conflict appears when uv solves for Windows Python 3.14 target.
- **Fix:** Added `[tool.uv] override-dependencies = ["pandas>=3.0.2"]` and `environments = ["sys_platform == 'darwin'", "sys_platform == 'linux'"]`; also pinned `requires-python = ">=3.11,<3.14"`. vectorbt works fine at runtime with pandas 3.x.
- **Files modified:** `backend/pyproject.toml`, `backend/uv.lock`
- **Verification:** `uv run python -c "import vectorbt; print(vectorbt.__version__)"` returns `0.28.5`
- **Committed in:** `d7d877a` (Task 1 commit)

**2. [Rule 1 - Bug] BKTS-02 audit test used non-future-peeking signal**
- **Found during:** Task 2 GREEN (test_shift1_prevents_look_ahead_bias failing)
- **Issue:** Plan's audit test used `close > close.shift(1)` as "biased" signal, but this is a lagging momentum signal — it uses past price, not future price. With seed=7, the honest (shifted by 1) variant happened to perform better, causing a false failure.
- **Fix:** Changed biased signal to `close.shift(-1) > close` — genuinely uses next bar's price. Biased strategy now shows Sharpe=11.2 vs honest=-2.1, correctly demonstrating look-ahead advantage.
- **Files modified:** `backend/tests/test_backtest.py`
- **Verification:** All 9 tests pass including this audit test
- **Committed in:** `37d7c56` (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 blocking installation issue, 1 test logic bug)
**Impact on plan:** Both auto-fixes essential — first enabled vectorbt install, second fixed a test that would give false negatives on certain seeds.

## Issues Encountered

**Pre-existing circular import failures** (out of scope — logged to deferred-items.md):
- `tests/test_analysis_api.py` and `tests/test_scanner.py` fail with `ImportError` due to circular import between `app/analysis/scanner.py` and `app/ingestion/scheduler.py`
- These existed before Phase 03 and are not caused by any Phase 03 changes
- All other tests (35) pass when excluding these two files

## User Setup Required

None - no external service configuration required. vectorbt runs fully offline.

## Next Phase Readiness

- `run_backtest()` is ready for Plan 02 to wrap in `POST /api/backtest` REST endpoint
- `BacktestRequest` Pydantic model is ready for FastAPI request body validation
- `BacktestRun` ORM and migration 003 are ready for DB persistence of results
- Pre-existing circular import in scanner/scheduler should be fixed before Phase 04

## Known Stubs

None - all fields in BacktestResult are populated from vectorbt stats. No hardcoded placeholder data.

## Self-Check: PASSED

All files exist and all commits verified:
- FOUND: backend/app/backtesting/__init__.py
- FOUND: backend/app/backtesting/engine.py
- FOUND: backend/app/backtesting/models.py
- FOUND: backend/app/models/backtest.py
- FOUND: backend/alembic/versions/003_create_backtest_runs_table.py
- FOUND: backend/tests/test_backtest.py
- FOUND: .planning/phases/03-backtesting-engine/03-01-SUMMARY.md
- Commit d7d877a: feat(03-01): install vectorbt and define data contracts
- Commit fa8e27b: test(03-01): add failing tests for backtesting engine (RED)
- Commit 37d7c56: feat(03-01): implement run_backtest() engine with look-ahead bias prevention (GREEN)

---
*Phase: 03-backtesting-engine*
*Completed: 2026-04-08*
