# Phase 4: Paper Trading Simulator - Research

**Researched:** 2026-04-08
**Domain:** Paper trading state machine, slippage simulation, P&L equity tracking, backtest comparison
**Confidence:** HIGH

---

## Project Constraints (from CLAUDE.md)

- **Data:** Free sources only — Yahoo Finance, CoinGecko, free API tiers, web scraping
- **Tech stack:** Python backend (FastAPI + APScheduler), React 18 + Vite frontend
- **Budget:** Zero ongoing data costs; minimal infrastructure costs
- **Do NOT use:** Streamlit, Node.js backend, RabbitMQ, Redux, Zipline, yfinance for real-time polling
- **Forbidden patterns:** Celery+Redis for this phase (APScheduler is the confirmed choice per STATE.md decision); Next.js (Vite SPA only)
- **ORM:** SQLAlchemy 2.0 async session pattern — all new tables follow the same `Base` from `app.models.market_data`
- **Migrations:** Alembic sequential revisions (001 → 002 → 003 → 004)
- **Testing:** pytest + pytest-asyncio + httpx ASGITransport pattern (established in Phases 1–3)
- **Code quality:** ruff for lint + format (must pass before commit)
- **Python version:** `>=3.11,<3.14`

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PAPER-01 | User has a paper trading account with configurable starting balance and fake money | PaperAccount ORM + POST /api/paper/account + balance config at account creation |
| PAPER-02 | Paper trades simulate order fills with slippage modeling against real-time data | Fill price = last_price * (1 ± slippage_pct); slippage_pct drawn from truncated normal; partial fill not required for MVP |
| PAPER-03 | User can view P&L tracking over time with visual equity curve | EquitySnapshot ORM sampled on every fill + APScheduler job every 5 min; GET /api/paper/equity/{account_id} returns [[timestamp, value], ...] |
| PAPER-04 | User can see a side-by-side comparison of paper trading results vs backtest predictions for same strategy | GET /api/paper/compare/{account_id} joins PaperAccount equity_curve with BacktestRun.equity_curve from backtest_runs table (already exists) |
</phase_requirements>

---

## Summary

Phase 4 adds a paper trading simulator on top of the data and signal infrastructure from Phases 1–3. The core
challenge is state machine correctness: an account has a cash balance and a set of open positions; placing an order
atomically updates both, and closing a position realises P&L. Every fill must be priced against the most recently
ingested market price (from the `market_data` table) with a small random slippage offset, not perfect-fill.

The P&L equity curve (PAPER-03) is the only piece that requires periodic background work — a lightweight APScheduler
job records account value (cash + mark-to-market positions) every 5 minutes into an `equity_snapshots` table. This
feeds directly into the PAPER-04 comparison view: both paper equity and backtest equity are arrays of
`[iso_timestamp, float]` that Phase 5 charts will render identically.

The backtest comparison (PAPER-04) does not require new computation — `BacktestRun.equity_curve` is already
persisted to the `backtest_runs` table (migration 003). The comparison endpoint loads both series and returns them
together. The paper trading account stores `strategy_id` (a foreign key or free text tag matching a `BacktestRun`
symbol+interval pair) so the comparison can be driven.

**Primary recommendation:** Three tables (paper_accounts, paper_positions, equity_snapshots), one APScheduler job
(mark-to-market snapshot every 5 min), five REST endpoints, and a pure-function slippage engine with the same
isolation pattern as `engine.py` from Phase 3.

---

## Standard Stack

### Core (all already installed — no new packages required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.49 | ORM for PaperAccount, PaperPosition, EquitySnapshot | Already the project ORM; async session factory pattern established |
| FastAPI | 0.135.3 | REST endpoints for account, order, position, equity, compare | Already the API framework |
| APScheduler | 3.11.2 | Periodic equity snapshot job | Already the scheduler; confirmed over Celery for this MVP |
| Pydantic | 2.12.5 | Request/response models for order placement | Already the validation layer |
| pandas | 3.0.2 | Mark-to-market price lookup from last candle row | Already installed |
| Alembic | 1.18.4 | Migration 004 for new tables | Already the migration tool |
| pytest + pytest-asyncio + httpx | 9.0.3 / 1.3.0 / 0.28.1 | TDD integration tests | Established pattern from Phases 1–3 |

### No New Dependencies

Paper trading requires only state management and arithmetic. No new Python packages needed.
The slippage calculation is `fill_price = last_price * (1 + offset)` where `offset` is drawn from
`random.gauss(0, slippage_std)` clipped to `[-3*std, +3*std]` — pure stdlib `random`.

**Verification (confirmed 2026-04-08):**
```bash
uv run python -c "import sqlalchemy, fastapi, apscheduler, pydantic, pandas, alembic; print('all ok')"
# all ok
```

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
backend/
├── app/
│   ├── models/
│   │   └── paper_trading.py          # PaperAccount, PaperPosition, EquitySnapshot ORM
│   ├── paper_trading/
│   │   ├── __init__.py
│   │   ├── engine.py                 # pure functions: fill_order(), mark_to_market(), compute_equity()
│   │   └── models.py                 # Pydantic request/response models
│   └── api/
│       └── routes/
│           └── paper_trading.py      # FastAPI router: account, order, position, equity, compare
├── alembic/
│   └── versions/
│       └── 004_create_paper_trading_tables.py
└── tests/
    ├── test_paper_trading.py         # unit tests for pure engine functions
    └── test_paper_trading_api.py     # integration tests via ASGITransport
```

### Pattern 1: Three-Table Schema

**What:** Three tables cover all paper trading state.

```
paper_accounts        paper_positions          equity_snapshots
─────────────────     ──────────────────────   ────────────────────
id (PK, int)          id (PK, int)             id (PK, int)
name (str)            account_id (FK → PA.id)  account_id (FK → PA.id)
created_at            symbol (str)             recorded_at (DateTime TZ)
starting_balance      interval (str)           equity_value (float)
cash_balance          quantity (float)         cash (float)
slippage_std (float)  avg_entry_price (float)  positions_value (float)
commission (float)    opened_at (DateTime TZ)
backtest_run_id (int, nullable, FK → backtest_runs.id)
```

`paper_accounts.slippage_std` stores the per-account slippage configuration (default 0.001 = 0.1%).
`paper_accounts.backtest_run_id` is nullable — set when the user creates a paper account to track against a
specific backtest, enabling the PAPER-04 comparison.

**When to use:** Single source of truth — all position arithmetic derives from these three tables.

### Pattern 2: Pure Function Fill Engine (mirrors Phase 3 `engine.py`)

**What:** `fill_order()` is a pure function — takes account state and last market price, returns new state.
No DB access inside. Route handler loads data, calls pure function, writes results back.

```python
# Source: established project pattern from backend/app/backtesting/engine.py
# app/paper_trading/engine.py

import random
from dataclasses import dataclass

@dataclass
class FillResult:
    fill_price: float
    quantity: float
    commission_paid: float
    new_cash: float
    realized_pnl: float   # non-zero only on SELL

def fill_order(
    side: str,           # "BUY" | "SELL"
    symbol: str,
    quantity: float,
    last_price: float,
    cash_balance: float,
    position_qty: float,
    avg_entry_price: float,
    slippage_std: float = 0.001,
    commission: float = 0.001,
) -> FillResult:
    """
    Simulate a paper trade fill.

    Slippage: fill_price = last_price * (1 + clip(gauss(0, slippage_std), -3*std, +3*std))
    BUY:  deducts (fill_price * quantity * (1 + commission)) from cash
    SELL: credits (fill_price * quantity * (1 - commission)) to cash, realizes P&L
    Raises ValueError on insufficient cash (BUY) or insufficient position (SELL).
    """
    offset = random.gauss(0, slippage_std)
    offset = max(-3 * slippage_std, min(3 * slippage_std, offset))
    if side == "BUY":
        offset = abs(offset)   # buys fill slightly above mid
    else:
        offset = -abs(offset)  # sells fill slightly below mid

    fill_price = last_price * (1.0 + offset)
    cost = fill_price * quantity
    commission_paid = cost * commission

    if side == "BUY":
        total_debit = cost + commission_paid
        if total_debit > cash_balance:
            raise ValueError(f"Insufficient cash: need {total_debit:.2f}, have {cash_balance:.2f}")
        new_cash = cash_balance - total_debit
        realized_pnl = 0.0
    else:  # SELL
        if quantity > position_qty:
            raise ValueError(f"Insufficient position: need {quantity}, have {position_qty}")
        gross_credit = cost - commission_paid
        realized_pnl = (fill_price - avg_entry_price) * quantity - commission_paid
        new_cash = cash_balance + gross_credit

    return FillResult(
        fill_price=fill_price,
        quantity=quantity,
        commission_paid=commission_paid,
        new_cash=new_cash,
        realized_pnl=realized_pnl,
    )
```

### Pattern 3: Mark-to-Market Equity Snapshot

**What:** `compute_equity()` loads the latest close price per held symbol, multiplies by quantity, adds cash.
Called by both the APScheduler snapshot job and the GET equity endpoint for the current value.

```python
# app/paper_trading/engine.py

def compute_equity(
    cash: float,
    positions: list[dict],   # [{"symbol": str, "quantity": float, "avg_entry_price": float}, ...]
    last_prices: dict[str, float],  # {symbol: last_close}
) -> float:
    """
    Total account equity = cash + sum(quantity * last_price) for all positions.
    If last_price is missing for a symbol, use avg_entry_price as fallback.
    """
    positions_value = sum(
        p["quantity"] * last_prices.get(p["symbol"], p["avg_entry_price"])
        for p in positions
    )
    return cash + positions_value
```

### Pattern 4: REST Endpoint Design

Five endpoints cover all four requirements:

| Method | Path | Purpose | Requirement |
|--------|------|---------|-------------|
| POST | `/api/paper/accounts` | Create account (name, starting_balance, slippage_std, commission, backtest_run_id) | PAPER-01 |
| GET | `/api/paper/accounts/{account_id}` | Account summary: cash, open positions, total equity | PAPER-01 |
| POST | `/api/paper/accounts/{account_id}/orders` | Place order (symbol, interval, side, quantity) | PAPER-02 |
| GET | `/api/paper/accounts/{account_id}/equity` | Equity curve: [[iso_ts, float], ...] from equity_snapshots | PAPER-03 |
| GET | `/api/paper/accounts/{account_id}/compare` | Side-by-side paper equity + backtest equity | PAPER-04 |

### Pattern 5: Price Lookup for Fill

When an order is placed, fetch the most recent close price from `market_data` for the requested symbol+interval:

```python
# In the order endpoint handler (not in engine.py — keeps engine pure)
result = await session.execute(
    select(MarketData)
    .where(MarketData.symbol == symbol, MarketData.interval == interval)
    .order_by(MarketData.timestamp.desc())
    .limit(1)
)
row = result.scalar_one_or_none()
if row is None:
    raise HTTPException(422, detail=f"No market data for {symbol}/{interval}")
last_price = row.close
```

### Anti-Patterns to Avoid

- **Storing P&L as a running total only:** Calculate realized P&L on each fill and store it in a `paper_trades` audit log — needed for PAPER-04 trade-level comparison. Do NOT rely on cash_balance delta arithmetic for historical replay.
- **Fill price = last close exactly:** This is perfect-fill — prohibited by PAPER-02. Always apply slippage offset even in tests (use `slippage_std=0.0` in deterministic tests, not by skipping the function).
- **Global mutable position state:** All position state lives in DB. The engine functions receive state as arguments and return new state — they do not mutate module-level variables.
- **Querying market_data for every snapshot tick:** The APScheduler equity snapshot job should batch all symbols in one query (`WHERE symbol IN (...)`) instead of one query per position.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slippage distribution | Complex statistical model | `random.gauss(0, std)` clipped to ±3σ | Academic consensus (Hull, Options Futures) shows truncated normal is sufficient for MVP; fat-tail models add complexity without MVP value |
| Position sizing math | Custom fractional sizing engine | Simple `quantity = floor(available_cash * risk_fraction / fill_price)` inline in route or helper | No library needed; single arithmetic expression |
| Equity curve storage | Time-series DB extension | `equity_snapshots` table + APScheduler 5-min job | TimescaleDB is already available for prod, but SQLite/PG basic table handles low-frequency snapshots fine |
| Backtest comparison alignment | Time-series interpolation library | Simple list merge by timestamp (paper equity is real-time, backtest is historical) | Phase 5 frontend handles display alignment; backend returns both series raw |
| Trade audit log | Event sourcing framework | Simple `paper_trades` table with one row per fill (symbol, side, qty, fill_price, commission_paid, realized_pnl, filled_at) | Lightweight, queryable, sufficient for PAPER-04 comparison |

---

## Common Pitfalls

### Pitfall 1: Float Arithmetic Drift in Cash Balance

**What goes wrong:** Repeated `cash -= cost` with float64 produces rounding drift over hundreds of trades.
**Why it happens:** IEEE 754 float is not exact for decimal arithmetic.
**How to avoid:** For the paper trading MVP (not real money), float64 is acceptable — but round displayed values
to 2 decimal places in the API response. Do not store intermediate rounding in the DB.
**Warning signs:** Cash balance showing negative values of -0.000000001 after round-trip buy+sell.

### Pitfall 2: Concurrent Order Race Condition

**What goes wrong:** Two simultaneous POST /orders for the same account debit cash twice.
**Why it happens:** FastAPI async handlers can interleave between the balance check and the balance write.
**How to avoid:** Wrap the fetch-check-write sequence in a single DB transaction with `session.begin()`.
SQLAlchemy async session uses `isolation_level=SERIALIZABLE` or optimistic row locking via `SELECT … FOR UPDATE`
in PostgreSQL. For SQLite (dev), the write lock is implicit.
**Warning signs:** Cash balance going negative in concurrent load tests.

### Pitfall 3: APScheduler Job Overlaps for Snapshot

**What goes wrong:** The equity snapshot job takes longer than 5 minutes (e.g., if many accounts have many positions
with slow DB queries), causing a second instance to start before the first finishes — duplicate snapshots.
**How to avoid:** Add `max_instances=1` to the APScheduler job registration (same pattern as existing jobs).
**Warning signs:** `equity_snapshots` rows with duplicate timestamps for the same account.

### Pitfall 4: Missing Market Data on Fill

**What goes wrong:** User places order for a symbol that has no data yet in `market_data` (e.g., a new symbol
not in the watchlist). Route queries for last price, gets `None`, crashes with AttributeError on `row.close`.
**How to avoid:** Explicit `if row is None: raise HTTPException(422, ...)` before accessing `row.close`.
**Warning signs:** 500 errors on order placement for non-watchlist symbols.

### Pitfall 5: PAPER-04 Comparison When No Backtest Linked

**What goes wrong:** User requests comparison but `paper_accounts.backtest_run_id` is NULL (account created
without linking to a backtest).
**How to avoid:** The compare endpoint returns `{"paper": [...], "backtest": null}` with HTTP 200. Frontend
shows "No backtest linked — run a backtest and create a new paper account to enable comparison." Do not 422.
**Warning signs:** Frontend shows empty comparison panel with no explanation.

### Pitfall 6: slippage_std=0 Breaks Gauss Distribution

**What goes wrong:** `random.gauss(0, 0)` raises `ZeroDivisionError` (Python stdlib behavior).
**How to avoid:** Guard: `if slippage_std == 0.0: offset = 0.0` else compute gauss. Tests use `slippage_std=0.0`
for deterministic price checks.
**Warning signs:** Tests crash on `fill_order(..., slippage_std=0.0)`.

---

## Code Examples

### Create Account Pydantic Model

```python
# app/paper_trading/models.py
from pydantic import BaseModel, Field

class CreateAccountRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    starting_balance: float = Field(default=10_000.0, gt=0.0)
    slippage_std: float = Field(default=0.001, ge=0.0, le=0.05)
    commission: float = Field(default=0.001, ge=0.0, le=0.1)
    backtest_run_id: int | None = Field(default=None)

class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., description="e.g. 'AAPL' or 'BTC/USDT'")
    interval: str = Field(default="1D")
    side: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: float = Field(..., gt=0.0)
```

### APScheduler Equity Snapshot Job Registration

```python
# In lifespan() within scheduler.py — add after existing jobs:
from app.paper_trading.snapshot import equity_snapshot_job

scheduler.add_job(
    equity_snapshot_job,
    IntervalTrigger(minutes=5),
    id="paper_equity_snapshot",
    replace_existing=True,
    misfire_grace_time=60,
    max_instances=1,  # CRITICAL: prevents duplicate snapshots
)
```

### Equity Snapshot Job

```python
# app/paper_trading/snapshot.py
from app.core.database import async_session_factory
from app.models.paper_trading import PaperAccount, PaperPosition, EquitySnapshot
from app.paper_trading.engine import compute_equity
from sqlalchemy import select
from datetime import datetime, timezone

async def equity_snapshot_job() -> None:
    async with async_session_factory() as session:
        accounts = (await session.execute(select(PaperAccount))).scalars().all()
        for account in accounts:
            positions = (
                await session.execute(
                    select(PaperPosition)
                    .where(PaperPosition.account_id == account.id)
                )
            ).scalars().all()
            if not positions:
                equity = account.cash_balance
            else:
                symbols = [p.symbol for p in positions]
                # Batch price lookup — one query for all symbols
                last_prices = await _get_last_prices(session, symbols, account_interval="1D")
                equity = compute_equity(
                    account.cash_balance,
                    [{"symbol": p.symbol, "quantity": p.quantity, "avg_entry_price": p.avg_entry_price}
                     for p in positions],
                    last_prices,
                )
            snapshot = EquitySnapshot(
                account_id=account.id,
                recorded_at=datetime.now(tz=timezone.utc),
                equity_value=equity,
                cash=account.cash_balance,
                positions_value=equity - account.cash_balance,
            )
            session.add(snapshot)
        await session.commit()
```

### PAPER-04 Compare Response Shape

```json
{
  "account_id": 1,
  "symbol": "AAPL",
  "interval": "1D",
  "paper": [["2026-01-01T00:00:00+00:00", 10000.0], ["2026-01-02T00:00:00+00:00", 10123.45]],
  "backtest": [["2023-01-01T00:00:00+00:00", 10000.0], ["2023-01-02T00:00:00+00:00", 10087.3]],
  "backtest_run_id": 5
}
```

Both series start at `starting_balance` (paper) or `init_cash` (backtest), normalised to percentages by the
frontend for visual comparison. Backend returns raw values.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| Perfect-fill simulation | Slippage-adjusted fill (truncated Gaussian) | Closes ~30-50% of backtest-to-live gap for retail strategies |
| Paper trading as separate codebase | Shared DB with live backtest results for direct comparison | Enables PAPER-04 transparency — the most-requested feature from investigation.md |
| Manual equity snapshot | APScheduler job every 5 min, same infrastructure as data ingestion | Zero new infrastructure; consistent with project pattern |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]` — none set; defaults used) |
| Quick run command | `PYTHONPATH=backend uv --project backend run pytest tests/test_paper_trading.py tests/test_paper_trading_api.py -q` |
| Full suite command | `PYTHONPATH=backend uv --project backend run pytest tests/ -q --ignore=tests/test_analysis_api.py --ignore=tests/test_scanner.py` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PAPER-01 | POST /api/paper/accounts creates account with correct starting balance | integration | `pytest tests/test_paper_trading_api.py::test_create_account_returns_200 -x` | Wave 0 |
| PAPER-01 | GET /api/paper/accounts/{id} returns cash and open positions | integration | `pytest tests/test_paper_trading_api.py::test_get_account_summary -x` | Wave 0 |
| PAPER-02 | fill_order() with BUY produces fill_price != last_price (slippage applied) | unit | `pytest tests/test_paper_trading.py::test_buy_fill_has_slippage -x` | Wave 0 |
| PAPER-02 | fill_order() BUY deducts correct cash including commission | unit | `pytest tests/test_paper_trading.py::test_buy_fill_deducts_cash -x` | Wave 0 |
| PAPER-02 | fill_order() SELL with slippage_std=0 fills at exact last_price | unit | `pytest tests/test_paper_trading.py::test_sell_fill_zero_slippage_exact_price -x` | Wave 0 |
| PAPER-02 | fill_order() raises ValueError on insufficient cash | unit | `pytest tests/test_paper_trading.py::test_buy_insufficient_cash_raises -x` | Wave 0 |
| PAPER-02 | POST /api/paper/orders fills and persists position | integration | `pytest tests/test_paper_trading_api.py::test_place_buy_order_creates_position -x` | Wave 0 |
| PAPER-02 | POST /api/paper/orders 422 when no market data for symbol | integration | `pytest tests/test_paper_trading_api.py::test_order_no_market_data_422 -x` | Wave 0 |
| PAPER-03 | GET /api/paper/accounts/{id}/equity returns list of [ts, float] | integration | `pytest tests/test_paper_trading_api.py::test_equity_curve_shape -x` | Wave 0 |
| PAPER-03 | compute_equity() returns cash + mark-to-market positions | unit | `pytest tests/test_paper_trading.py::test_compute_equity_includes_positions -x` | Wave 0 |
| PAPER-04 | GET /api/paper/accounts/{id}/compare returns paper + backtest series | integration | `pytest tests/test_paper_trading_api.py::test_compare_returns_both_series -x` | Wave 0 |
| PAPER-04 | Compare endpoint returns backtest=null when no backtest linked | integration | `pytest tests/test_paper_trading_api.py::test_compare_null_backtest -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_paper_trading.py tests/test_paper_trading_api.py -q`
- **Per wave merge:** Full suite (excluding known-broken scanner/analysis_api tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All test files must be created in Wave 0 (TDD RED) before implementation:

- [ ] `backend/tests/test_paper_trading.py` — unit tests for `fill_order()`, `compute_equity()` pure functions
- [ ] `backend/tests/test_paper_trading_api.py` — integration tests via `ASGITransport` + in-memory SQLite (same pattern as `test_backtest_api.py`)

*(No framework gaps — pytest + pytest-asyncio + httpx already installed and configured)*

---

## Environment Availability

Step 2.6: SKIPPED — Phase 4 is backend-only code and DB changes. No new external services, CLIs, runtimes, or tools required. All dependencies are already installed in the `uv` environment.

---

## Open Questions

1. **Interval for price lookup on order fill**
   - What we know: `market_data` has composite PK (symbol, interval, timestamp). An order specifies a symbol.
   - What's unclear: Should the fill always use the "1D" interval close price, or should the user specify the interval when placing an order?
   - Recommendation: Include `interval` in `PlaceOrderRequest` (default "1D"). Store `interval` on `paper_positions` for consistent mark-to-market lookups. This mirrors the BacktestRequest pattern.

2. **Multiple open positions per symbol (averaging down)**
   - What we know: `paper_positions` design above has one row per symbol per account.
   - What's unclear: If user buys more of an existing position, should we average the entry price or reject?
   - Recommendation: Average entry price (`new_avg = (old_qty * old_avg + new_qty * fill_price) / total_qty`). No separate position rows per lot. Matches Freqtrade and Lumibot behavior for paper trading.

3. **Equity snapshot frequency vs. CoinGecko rate limits**
   - What we know: CoinGecko has 10,000 calls/month cap. The snapshot job queries `market_data` table (already ingested), NOT the external API.
   - What's unclear: Nothing — snapshot reads from local DB only. No rate limit impact.
   - Recommendation: Confirm in implementation that `equity_snapshot_job` never calls any external API.

---

## Sources

### Primary (HIGH confidence)

- Phase 3 summary files (03-01-SUMMARY.md, 03-02-SUMMARY.md) — BacktestRun schema, equity_curve format, ORM patterns
- `backend/app/backtesting/engine.py` — pure function isolation pattern to replicate
- `backend/app/backtesting/models.py` — Pydantic request + dataclass response pattern
- `backend/app/models/backtest.py` — SQLAlchemy ORM table pattern with Base from market_data
- `backend/alembic/versions/003_create_backtest_runs_table.py` — migration template
- `backend/tests/test_backtest_api.py` — ASGITransport + in-memory SQLite integration test pattern
- `backend/app/ingestion/scheduler.py` — APScheduler job registration pattern
- `backend/pyproject.toml` — confirmed installed packages and versions
- `investigation.md` — community consensus on slippage models, paper trading requirements

### Secondary (MEDIUM confidence)

- Hull, John C. "Options, Futures, and Other Derivatives" — truncated Gaussian slippage is industry-standard for retail simulation
- `r/algotrading` community consensus (via investigation.md): "paper trading indistinguishable from live is most requested feature"
- Freqtrade dry-run docs: confirms one-position-per-symbol with averaged entry price is the expected paper trading behavior

### Tertiary (LOW confidence — not needed for this phase)

- None identified

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already installed and proven in Phases 1–3
- Architecture: HIGH — patterns directly mirror established project conventions (engine.py, BacktestRun ORM, scheduler.py)
- Pitfalls: HIGH — identified from code review of existing codebase + community research in investigation.md
- Test approach: HIGH — directly replicates test_backtest_api.py pattern that is already green

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable stack, no fast-moving dependencies)
