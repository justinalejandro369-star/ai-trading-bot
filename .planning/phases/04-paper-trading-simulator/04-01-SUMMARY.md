---
phase: 04-paper-trading-simulator
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, pydantic, python, paper-trading, tdd]

# Dependency graph
requires:
  - phase: 03-backtesting-engine
    provides: BacktestRun ORM model and backtest_runs table referenced as FK
  - phase: 01-data-foundation
    provides: Base declarative registry from app.models.market_data
provides:
  - PaperAccount, PaperPosition, EquitySnapshot ORM models
  - Alembic migration 004 creating all three paper trading tables
  - fill_order() pure function with Gaussian slippage model and commission
  - compute_equity() pure function for mark-to-market portfolio valuation
  - FillResult dataclass for fill execution results
  - Pydantic request/response models: CreateAccountRequest, PlaceOrderRequest, AccountSummaryResponse
  - 13 GREEN unit tests for engine functions
  - 7 RED integration test stubs defining Wave 2 API contract
affects: [04-02-paper-trading-api, comparison-charts, equity-curve-endpoints]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pure-function isolation: engine.py has zero SQLAlchemy/FastAPI imports — all business logic testable without DB
    - TDD RED→GREEN: test file written first, ImportError confirmed, then engine implemented
    - Gaussian slippage with 3-sigma clipping: abs(offset) for BUY (fills above mid), -abs(offset) for SELL (fills below mid)
    - avg_entry_price fallback in compute_equity() prevents zero-valuation when no live price available

key-files:
  created:
    - backend/app/models/paper_trading.py
    - backend/alembic/versions/004_create_paper_trading_tables.py
    - backend/app/paper_trading/__init__.py
    - backend/app/paper_trading/engine.py
    - backend/app/paper_trading/models.py
    - backend/tests/test_paper_trading.py
    - backend/tests/test_paper_trading_api.py
  modified: []

key-decisions:
  - "fill_order() uses abs(gauss_offset) for BUY and -abs(gauss_offset) for SELL — directional slippage enforced without branching on offset sign"
  - "slippage_std=0.0 short-circuits to offset=0.0 before calling random.gauss() — deterministic tests require exact price equality"
  - "3-sigma clipping on Gaussian offset prevents extreme outlier fills (e.g., 10x price from 10-sigma event)"
  - "Integration test stubs use assert False with Wave 2 marker — RED state is intentional and expected per plan"

patterns-established:
  - "Paper trading engine follows same pure-function isolation pattern as backtesting/engine.py — no DB, no FastAPI"
  - "ORM models import Base from app.models.market_data (shared registry) — same pattern as BacktestRun in backtest.py"
  - "Migration 004 follows 003's op.create_table() + sa.ForeignKeyConstraint() style exactly"

requirements-completed: [PAPER-01, PAPER-02, PAPER-03, PAPER-04]

# Metrics
duration: 4min
completed: 2026-04-08
---

# Phase 4 Plan 1: Paper Trading Data Models and Engine Summary

**Three-table paper trading schema (paper_accounts, paper_positions, equity_snapshots) with a pure fill_order() engine applying Gaussian slippage and flat commission, 13 unit tests all GREEN.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-08T13:34:14Z
- **Completed:** 2026-04-08T13:38:00Z
- **Tasks:** 2
- **Files modified:** 7 created

## Accomplishments
- ORM models for all three paper trading tables, importing the shared Base from app.models.market_data
- Alembic migration 004 with FK constraints and account_id indexes on positions and snapshots
- fill_order() pure function: Gaussian slippage (BUY above mid, SELL below), commission deduction, ValueError guards on insufficient cash/position, realized P&L calculation
- compute_equity() pure function: cash + sum(qty * mark_price), falls back to avg_entry_price when symbol absent from last_prices
- 13 unit tests covering all eight must-have truths from the plan — all PASS
- 7 integration test stubs in RED state defining Wave 2 API contract

## Task Commits

Each task was committed atomically:

1. **Task 1: ORM models + Alembic migration 004** - `a7cc6bd` (feat)
2. **Task 2: Pure engine functions (TDD RED → GREEN)** - `8837c4a` (feat)

## Files Created/Modified
- `backend/app/models/paper_trading.py` - PaperAccount, PaperPosition, EquitySnapshot ORM models
- `backend/alembic/versions/004_create_paper_trading_tables.py` - Migration 004 (revision="004", down_revision="003")
- `backend/app/paper_trading/__init__.py` - Module marker
- `backend/app/paper_trading/engine.py` - fill_order(), compute_equity(), FillResult dataclass
- `backend/app/paper_trading/models.py` - CreateAccountRequest, PlaceOrderRequest, AccountSummaryResponse Pydantic models
- `backend/tests/test_paper_trading.py` - 13 unit tests (all GREEN)
- `backend/tests/test_paper_trading_api.py` - 7 integration stubs (all RED, expected for Wave 2)

## Decisions Made
- `fill_order()` uses `abs(gauss_offset)` for BUY direction and `-abs(gauss_offset)` for SELL direction — this guarantees directional slippage invariants hold regardless of the random draw sign, enabling deterministic test assertions like `assert fill_price >= last_price`.
- `slippage_std=0.0` short-circuits before calling `random.gauss()` (sets `offset = 0.0` directly) — required for arithmetic equality tests (`fill_price == last_price` exactly, no floating-point noise from a gauss(0, 0) call).
- 3-sigma clipping (`max(-3*std, min(3*std, raw))`) prevents pathological fills that would occur ~0.3% of the time with pure Gaussian draws.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Known Stubs
None — no hardcoded placeholder data flows to UI. Integration test stubs are intentional RED markers for Wave 2 and contain no fake data wired to rendering.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ORM models, migration 004, and engine functions are fully ready for Wave 2 (Plan 04-02)
- Wave 2 will implement POST /api/paper/accounts, POST /api/paper/accounts/{id}/orders, GET /api/paper/accounts/{id}, GET /api/paper/accounts/{id}/equity, GET /api/paper/accounts/{id}/compare
- Integration test stubs in test_paper_trading_api.py define exact contract Wave 2 must satisfy (turn RED to GREEN)

---
*Phase: 04-paper-trading-simulator*
*Completed: 2026-04-08*
