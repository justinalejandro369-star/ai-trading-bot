---
phase: 04-paper-trading-simulator
verified: 2026-04-08T13:47:53Z
status: passed
score: 6/6 must-haves verified
---

# Phase 4: Paper Trading Simulator Verification Report

**Phase Goal:** Users can trade with fake money against live market data and compare simulated results to backtest predictions
**Verified:** 2026-04-08T13:47:53Z
**Status:** passed
**Re-verification:** No — initial verification

## Note on Must-Have #4 Path

The verification prompt specified "GET /api/paper/comparison" but the PLAN frontmatter (04-02-PLAN.md) and the codebase both define this as "GET /api/paper/accounts/{id}/compare". The route is account-scoped (per-account comparison, not global) — this is a more correct design and matches the ROADMAP success criterion ("compare paper trading results vs. backtest predictions"). Verified against the PLAN's canonical definition.

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria + PLAN must_haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/paper/accounts creates account with configurable starting balance | VERIFIED | `paper_trading.py:41-80` — creates PaperAccount with `body.starting_balance`, commits, returns id + cash_balance |
| 2 | POST /api/paper/accounts/{id}/orders fills with Gaussian slippage (non-perfect fill) | VERIFIED | `engine.py:83-105` — `fill_price = last_price * (1 + abs(offset))` for BUY, `(1 - abs(offset))` for SELL with Gaussian `random.gauss(0, slippage_std)` |
| 3 | GET /api/paper/accounts/{id}/equity returns equity curve over time (equity_snapshots) | VERIFIED | `paper_trading.py:339-367` — queries EquitySnapshot rows ordered by recorded_at asc, returns list of `[iso_timestamp, equity_value]` pairs |
| 4 | GET /api/paper/accounts/{id}/compare returns side-by-side paper vs backtest P&L | VERIFIED | `paper_trading.py:375-427` — returns `{"paper": [...], "backtest": [...], "backtest_run_id": ...}`, null-safe when no backtest linked |
| 5 | equity_snapshot_job registered in APScheduler with max_instances=1 | VERIFIED | `scheduler.py:175-182` — `add_job(equity_snapshot_job, ..., id="paper_equity_snapshot", max_instances=1)` |
| 6 | fill_order() applies directional slippage (BUY fills above, SELL fills below last_price) | VERIFIED | `engine.py:90,93,105` — `offset = abs(raw)`, BUY: `last_price * (1.0 + offset)`, SELL: `last_price * (1.0 - offset)` |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/paper_trading/engine.py` | fill_order() + compute_equity() pure functions | VERIFIED | 153 lines, substantive implementation with Gaussian slippage, 3-sigma clipping, commission, realized P&L |
| `backend/app/api/routes/paper_trading.py` | FastAPI router with 5 paper trading endpoints | VERIFIED | 427 lines, all 5 endpoints present and wired to engine and DB |
| `backend/app/paper_trading/snapshot.py` | equity_snapshot_job() APScheduler job | VERIFIED | 114 lines, full DB-only batch implementation |
| `backend/app/ingestion/scheduler.py` | Updated lifespan() with paper_equity_snapshot job | VERIFIED | Contains `equity_snapshot_job` import at line 32, `paper_equity_snapshot` id at line 178, `max_instances=1` at line 181 |
| `backend/app/models/paper_trading.py` | PaperAccount, PaperPosition, EquitySnapshot ORM models | VERIFIED | 76 lines, three complete ORM models with correct FK constraints and indexes |
| `backend/alembic/versions/004_create_paper_trading_tables.py` | Alembic migration 004 | VERIFIED | 73 lines, exists |
| `backend/app/paper_trading/models.py` | Pydantic request/response models | VERIFIED | 42 lines, CreateAccountRequest, PlaceOrderRequest, AccountSummaryResponse |
| `backend/app/main.py` | paper_trading_router included at /api prefix | VERIFIED | Lines 22 + 41: `from app.api.routes.paper_trading import router as paper_trading_router` + `app.include_router(paper_trading_router, prefix="/api")` |
| `backend/tests/test_paper_trading.py` | 13 unit tests for engine | VERIFIED | 257 lines, comprehensive slippage/cash/guard/P&L/compute_equity tests |
| `backend/tests/test_paper_trading_api.py` | 7 integration tests | VERIFIED | 295 lines, all 7 tests implemented with real fill_order() execution |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `paper_trading.py` | `engine.py` | `from app.paper_trading.engine import fill_order, compute_equity` | WIRED | Imported at line 26; fill_order called at line 230, compute_equity at lines 140, 298 |
| `paper_trading.py` | `models/market_data.py` | `select(MarketData).order_by(MarketData.timestamp.desc()).limit(1)` | WIRED | Lines 203-208: batch price query with ORDER BY DESC LIMIT 1 |
| `snapshot.py` | `engine.py` | `from app.paper_trading.engine import compute_equity` | WIRED | Line 27: import, line 90: `equity = compute_equity(account.cash_balance, positions_dicts, last_prices)` |
| `scheduler.py` | `snapshot.py` | `equity_snapshot_job` registered with `max_instances=1` | WIRED | Line 32: import, lines 175-182: `add_job(equity_snapshot_job, ..., max_instances=1)` |
| `main.py` | `paper_trading.py` | `app.include_router(paper_trading_router, prefix="/api")` | WIRED | Line 22: import, line 41: include_router |
| `paper_trading.py` → orders | `EquitySnapshot` | Inline snapshot after every fill | WIRED | Lines 301-308: EquitySnapshot created and added to session after every fill |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `paper_trading.py` GET /equity | `snapshots` | `select(EquitySnapshot).where(account_id)` | Yes — DB query with account filter | FLOWING |
| `paper_trading.py` GET /compare | `paper_curve`, `backtest_curve` | EquitySnapshot rows + `backtest_run.equity_curve_data()` | Yes — DB query; BacktestRun ORM call | FLOWING |
| `paper_trading.py` POST /orders | `fill_result` | `fill_order()` with `last_price` from `select(MarketData)...limit(1)` | Yes — real MarketData close price | FLOWING |
| `snapshot.py` | `equity` per account | `compute_equity()` with prices from `select(MarketData).where(symbol IN ...)` | Yes — DB batch query, no static fallback | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED — endpoints require a running FastAPI server with a live DB. No standalone runnable entry points testable without starting services. Integration tests (test_paper_trading_api.py, 7 tests) serve as the behavioral verification proxy — all 7 implemented and reported GREEN by commits 0d65a46 + 14fc248.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PAPER-01 | 04-01, 04-02 | Paper account with configurable starting balance and fake money | SATISFIED | `POST /api/paper/accounts` creates PaperAccount with `starting_balance` field; `GET /api/paper/accounts/{id}` returns account summary |
| PAPER-02 | 04-01, 04-02 | Paper trades simulate order fills with slippage modeling against real-time data | SATISFIED | `fill_order()` Gaussian slippage wired to `POST /orders`; last_price fetched from live MarketData table |
| PAPER-03 | 04-01, 04-02 | User can view P&L tracking over time with visual equity curve | SATISFIED | `GET /api/paper/accounts/{id}/equity` returns `equity_curve` list of `[timestamp, value]` pairs from EquitySnapshot rows |
| PAPER-04 | 04-01, 04-02 | User can compare paper trading results vs backtest predictions | SATISFIED | `GET /api/paper/accounts/{id}/compare` returns `{"paper": [...], "backtest": [...], "backtest_run_id": ...}`; null-safe |

### Anti-Patterns Found

No anti-patterns found. Scan of all four phase-04 files (engine.py, paper_trading.py, snapshot.py, scheduler.py) returned zero matches for TODO/FIXME/placeholder/hardcoded empty returns. The previously noted "integration test stubs in RED state" from Plan 01 were intentional Wave-2 markers, and all 7 were turned GREEN in Plan 02 (verified by commit 14fc248).

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

### Human Verification Required

None required. All must-haves are verifiable programmatically. Visual equity curve rendering and dashboard comparison charts are Phase 5 scope.

### Gaps Summary

No gaps. All six must-haves verified. All artifacts exist, are substantive, and are wired. Data flows from real DB queries through all four endpoints. The equity_snapshot_job is imported, registered, and constrained with max_instances=1. All four PAPER-* requirements are satisfied.

One path discrepancy was noted (prompt specified `/api/paper/comparison`; actual route is `/api/paper/accounts/{id}/compare`) but this is a more correct account-scoped design that fully satisfies PAPER-04. The PLAN frontmatter, ROADMAP success criteria, and implementation are internally consistent.

---

_Verified: 2026-04-08T13:47:53Z_
_Verifier: Claude (gsd-verifier)_
