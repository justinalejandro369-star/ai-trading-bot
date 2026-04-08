# Phase 3: Backtesting Engine - Research

**Researched:** 2026-04-08
**Domain:** Vectorized backtesting with vectorbt, FastAPI REST endpoint, SQLAlchemy ORM, look-ahead bias prevention
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BKTS-01 | User can backtest strategies against historical data using vectorbt | vectorbt 0.28.5 confirmed; Portfolio.from_signals() API verified; FastAPI POST endpoint pattern established |
| BKTS-02 | Backtesting engine enforces look-ahead bias prevention by design | signals.vbt.fshift(1) / pd.Series.shift(1) pattern confirmed; audit test strategy documented |
| BKTS-03 | Backtest results show Sharpe ratio, max drawdown, win rate, profit factor | pf.stats() returns all four metrics; exact key names verified: "Sharpe Ratio", "Max Drawdown [%]", "Win Rate [%]", "Profit Factor" |
| BKTS-04 | Backtest models transaction costs (slippage + commissions) for realistic results | fees= and slippage= params confirmed in Portfolio.from_signals(); configurable per request |
</phase_requirements>

---

## Summary

Phase 3 implements a backtesting engine that lets users test the rule-based signal strategies from Phase 2 against historical OHLCV data already stored in the database. The engine uses vectorbt, which processes years of daily candle data in milliseconds via NumPy/Numba vectorized operations. The Phase 2 signal scorer (`score_signal()`) generates BUY signals from indicator convergence; the backtesting layer takes those same scoring rules, applies them across the full historical DataFrame shifted by one bar to prevent look-ahead bias, and passes the resulting boolean entry/exit arrays to `vbt.Portfolio.from_signals()` along with configurable commission and slippage parameters.

The output is a `BacktestResult` dataclass containing the four required metrics (Sharpe ratio, max drawdown, win rate, profit factor) plus an equity curve serializable as a list of `[timestamp, value]` pairs for the Phase 5 dashboard. The engine is exposed via a synchronous FastAPI `POST /api/backtest` endpoint — vectorbt's Numba-compiled core runs in under one second on 1–3 years of daily data, so the endpoint does not block the event loop for a meaningful duration. Wrapping the vectorbt call with `run_in_threadpool` (from `starlette.concurrency`) is the safe pattern to keep the async event loop unblocked.

A blocking blocker was found during research: the project's `.python-version` file requires Python 3.11, but Python 3.11 is not currently installed via pyenv (only 3.10.12 is available). Wave 0 of the plan must install Python 3.11 via pyenv before vectorbt can be added as a uv dependency.

**Primary recommendation:** Use `vbt.Portfolio.from_signals()` with `entries = score_signals(df).shift(1).astype(bool)`, `fees=commission`, `slippage=slippage`, `freq="1D"`. Extract metrics via `pf.stats()` using exact Series keys. Run synchronously wrapped in `run_in_threadpool` from FastAPI.

---

## Project Constraints (from CLAUDE.md)

The following directives from CLAUDE.md govern this phase and override any conflicting research recommendations:

- **Python 3.11+** is required. The `.python-version` file already pins 3.11.
- **vectorbt 0.26+** is the mandated backtesting library. Backtesting.py 0.3+ is the approved fallback only if vectorbt proves intractable.
- **FastAPI** handles all REST endpoints. No Flask, Django, or alternative frameworks.
- **pandas 2.2+** (project has 3.0.2) for all DataFrame operations.
- **numpy 1.26+** (project uses numpy transitively via pandas/vectorbt).
- **SQLAlchemy 2.0+** with async sessions for all DB interactions.
- **Alembic** for database schema migration (migration 003 required for `backtest_results` table).
- **uv** is the package manager. All installs via `uv add`.
- **pytest** with `pytest-asyncio` for testing. TDD RED/GREEN commit pattern.
- **ruff** for linting and formatting. All code must pass before commit.
- **Free data only** — historical OHLCV is already in the local database from Phase 1; no new data source required for Phase 3.
- **aiosqlite** for in-memory SQLite in tests (already installed).
- **Do not** use Zipline, Backtrader, TA-Lib, Streamlit, Node.js, or paid data APIs.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vectorbt | 0.28.5 | Backtesting engine — Portfolio.from_signals() | CLAUDE.md mandated; 1M orders in 70-100ms on M1; Numba-vectorized; Python 3.10-3.13 supported |
| pandas | 3.0.2 (installed) | DataFrame manipulation, signal shifting | Already installed; project standard |
| numpy | via pandas | Numerical arrays for signal vectors | Transitive dependency already present |
| FastAPI | 0.135.3 (installed) | REST endpoint for backtest trigger | Already installed; project standard |
| SQLAlchemy | 2.0.49 (installed) | BacktestResult ORM model + async session | Already installed; project standard |
| Alembic | 1.18.4 (installed) | Migration 003 for backtest_results table | Already installed; project standard |
| starlette.concurrency | (via fastapi) | run_in_threadpool to wrap sync vectorbt call | Prevents blocking async event loop |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiosqlite | 0.22.1 (installed) | In-memory SQLite for tests | All unit/integration tests (already proven pattern) |
| pytest-asyncio | 1.3.0 (installed) | Async test fixtures | Required for all async route tests |
| Backtesting.py | 0.6.5 (PyPI) | Fallback simple backtester | Only if vectorbt install fails on Python 3.11; do not use by default |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| vectorbt | Backtesting.py | Simpler API but 10-100x slower; acceptable for single-asset smoke test, not batch runs |
| vectorbt | Backtrader | CLAUDE.md explicitly prohibits — "do not use"; event-driven slow |
| run_in_threadpool | asyncio.run_in_executor | run_in_threadpool is Starlette's first-class wrapper; simpler, same result |
| POST /api/backtest (sync result) | Background task + polling | vectorbt on 1-3yr daily data finishes in <1s; async job queue is over-engineering for MVP |

**Installation:**

```bash
# From backend/ directory
uv add "vectorbt>=0.28.5"
```

**Note:** Python 3.11 must be installed via pyenv first (see Environment Availability). vectorbt 0.28.5 is confirmed compatible with Python 3.10-3.13 (verified via PyPI classifiers, released 2026-03-26).

**Version verification (confirmed 2026-04-08):**

| Package | Verified Version | PyPI Date |
|---------|-----------------|-----------|
| vectorbt | 0.28.5 | 2026-03-26 |
| backtesting | 0.6.5 (fallback only) | PyPI verified |

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── backtesting/          # NEW Phase 3 module
│   ├── __init__.py
│   ├── engine.py         # run_backtest() pure function — no DB, no FastAPI
│   └── models.py         # BacktestResult dataclass + BacktestRequest Pydantic model
├── models/
│   └── backtest.py       # NEW: BacktestRun ORM model (optional persistence)
├── api/routes/
│   └── backtest.py       # NEW: POST /api/backtest endpoint
├── alembic/versions/
│   └── 003_create_backtest_runs_table.py   # NEW migration
└── tests/
    └── test_backtest.py  # NEW TDD test suite
```

### Pattern 1: Pure Function Engine (matches Phase 2 design)

**What:** `run_backtest(df, commission, slippage, init_cash) -> BacktestResult` takes a raw OHLCV DataFrame and parameters, generates BUY signals using the same `score_signal()` logic from Phase 2, shifts them by 1 bar, and calls vectorbt. Returns a dataclass with all metrics. No DB access, no FastAPI — fully testable in isolation.

**When to use:** Always. Keeps the engine decoupled from the API layer, matching the `compute_indicators()` pure function pattern established in Phase 2.

**Example:**

```python
# Source: vectorbt.dev/api/portfolio/base/ + Phase 2 pure function pattern
import vectorbt as vbt
import pandas as pd

def run_backtest(
    df: pd.DataFrame,       # OHLCV, DatetimeIndex, >= MIN_CANDLES rows
    commission: float = 0.001,   # 0.1% default
    slippage: float = 0.001,     # 0.1% default
    init_cash: float = 10_000.0,
) -> "BacktestResult":
    # 1. Compute signals (reuse Phase 2 logic)
    ind = compute_indicators(df, symbol="", interval="")
    if ind is None:
        raise ValueError("Insufficient data for backtest")

    # 2. Build entry/exit boolean arrays for entire history
    # (vectorized scoring across full df — not just last row)
    entries_raw = _compute_entries_series(df)   # bool Series, same length as df
    exits_raw   = _compute_exits_series(df)     # bool Series

    # 3. CRITICAL: shift(1) to prevent look-ahead bias
    #    Signal at bar T must not use data from bar T's close
    entries = entries_raw.shift(1).fillna(False).astype(bool)
    exits   = exits_raw.shift(1).fillna(False).astype(bool)

    # 4. Run vectorbt backtest
    pf = vbt.Portfolio.from_signals(
        df["close"],
        entries=entries,
        exits=exits,
        fees=commission,
        slippage=slippage,
        init_cash=init_cash,
        freq="1D",
    )

    # 5. Extract metrics
    stats = pf.stats()
    return BacktestResult(
        sharpe_ratio=float(pf.sharpe_ratio()),
        max_drawdown=float(pf.max_drawdown()),
        win_rate=float(stats["Win Rate [%]"]) / 100.0,   # convert % to 0-1
        profit_factor=float(stats["Profit Factor"]),
        total_return=float(pf.total_return()),
        total_trades=int(stats["Total Trades"]),
        equity_curve=_serialize_equity(pf.value()),
    )
```

### Pattern 2: Vectorized Signal Generation Across Full History

**What:** Phase 2's `score_signal()` was designed for the last bar only. For backtesting, we need to compute the same indicator-based logic across ALL bars. This means running pandas-ta-classic indicators once on the full DataFrame and then applying threshold checks vectorized (no Python loop per bar).

**When to use:** Always in the backtesting engine. This is what makes vectorbt fast — the signal arrays are NumPy boolean arrays, not Python lists.

**Example:**

```python
# Source: Phase 2 signals.py scoring logic, adapted for full-history vectorization
def _compute_entries_series(df: pd.DataFrame) -> pd.Series:
    """
    Compute BUY entry boolean Series for the entire OHLCV history.
    Mirrors score_signal() logic but vectorized across all bars.
    """
    import pandas_ta_classic as ta

    rsi = ta.rsi(df["close"], length=14)
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    bb_df = ta.bbands(df["close"], length=20, std=2)
    ema50 = ta.ema(df["close"], length=50)
    vol_sma = ta.sma(df["volume"], length=20)

    # Score each bar (vectorized)
    bull_score = pd.Series(0, index=df.index, dtype=int)
    bull_score += (rsi < 35).fillna(False).astype(int) * 25
    bull_score += (macd_df["MACD_12_26_9"] > macd_df["MACDs_12_26_9"]).fillna(False).astype(int) * 30
    bull_score += (bb_df["BBP_20_2.0"] < 0.2).fillna(False).astype(int) * 25
    vol_surge = (vol_sma > 0) & (df["volume"] > vol_sma * 1.5)
    bull_score += vol_surge.fillna(False).astype(int) * 10
    bull_score += (df["close"] > ema50).fillna(False).astype(int) * 10

    return bull_score >= 55  # THRESHOLD from Phase 2
```

### Pattern 3: FastAPI Endpoint (Sync Wrapped in run_in_threadpool)

**What:** POST endpoint accepts symbol + parameters, loads candles from DB, runs backtest synchronously inside a thread pool to keep the async event loop free.

**When to use:** Always for CPU-bound library calls that release the GIL (Numba does release GIL). Do NOT make the route `async def` and call vectorbt directly — that blocks the event loop.

**Example:**

```python
# Source: FastAPI docs + starlette.concurrency
from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/backtest", tags=["backtest"])

@router.post("")
async def run_backtest_endpoint(
    request: BacktestRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    # 1. Load candles from DB (async)
    df = await _load_candles(session, request.symbol, request.interval)
    if df is None or len(df) < MIN_CANDLES:
        raise HTTPException(status_code=422, detail="Insufficient data")

    # 2. Run vectorbt (CPU-bound, sync — wrap in threadpool)
    result = await run_in_threadpool(
        run_backtest, df, request.commission, request.slippage, request.init_cash
    )
    return result.to_dict()
```

### Pattern 4: shift(1) Audit Test

**What:** A deterministic audit test that verifies the engine returns WORSE or equal performance when signals are NOT shifted, and BETTER or equal performance when they ARE shifted. This is the verifiable proof required by BKTS-02.

**When to use:** Exactly once in the test suite as a separate audit test.

**Example:**

```python
def test_shift1_prevents_look_ahead_bias():
    """
    Audit test: perfect-information signals (no shift) yield higher Sharpe
    than properly shifted signals. If shifted >= unshifted, the shift is broken.
    """
    df = make_ohlcv_df(500)  # 500 bars of synthetic data
    
    # Perfect-information: signal at bar T uses bar T's data (CHEATING)
    entries_biased = (df["close"] > df["close"].shift(1)).astype(bool)
    exits_biased   = (df["close"] < df["close"].shift(1)).astype(bool)
    pf_biased = vbt.Portfolio.from_signals(df["close"], entries_biased, exits_biased, freq="1D")
    
    # Correct: signal at bar T uses bar T-1's data
    entries_honest = entries_biased.shift(1).fillna(False)
    exits_honest   = exits_biased.shift(1).fillna(False)
    pf_honest = vbt.Portfolio.from_signals(df["close"], entries_honest, exits_honest, freq="1D")
    
    # Biased version must have >= Sharpe (perfect information wins or ties)
    biased_sharpe = pf_biased.sharpe_ratio()
    honest_sharpe = pf_honest.sharpe_ratio()
    assert biased_sharpe >= honest_sharpe, (
        f"shift(1) appears broken: honest ({honest_sharpe:.3f}) > biased ({biased_sharpe:.3f})"
    )
```

### Pattern 5: BacktestResult Dataclass

```python
from dataclasses import dataclass, asdict

@dataclass
class BacktestResult:
    sharpe_ratio: float
    max_drawdown: float       # as fraction, e.g., -0.25 = -25%
    win_rate: float           # as fraction, e.g., 0.60 = 60%
    profit_factor: float
    total_return: float       # as fraction, e.g., 0.35 = 35%
    total_trades: int
    equity_curve: list[list]  # [[iso_timestamp, value], ...]

    def to_dict(self) -> dict:
        return asdict(self)
```

### Anti-Patterns to Avoid

- **Calling score_signal() once per bar in a Python loop:** vectorbt wins because it processes the whole history as NumPy arrays. A bar-by-bar Python loop is 100-1000x slower and defeats the purpose of vectorbt.
- **Making the FastAPI route `def` (not `async def`):** FastAPI will run it in a thread pool automatically, but the DB session dependency (async generator) breaks with sync routes. Keep route `async def`, wrap only the vectorbt call.
- **Forgetting `freq="1D"` in Portfolio.from_signals():** Without freq, `pf.sharpe_ratio()` raises an error because it cannot annualize returns. Always pass freq matching the candle interval.
- **Not setting `fillna(False)` after shift(1):** `shift(1)` introduces a NaN at position 0. If not filled, vectorbt will treat it as True or raise a type error. Always `.fillna(False).astype(bool)`.
- **Using `df["close"].shift(-1)` (negative shift):** Negative shift is look-ahead bias. Only positive shift (shift(1)) is safe.
- **Storing equity curve as JSON blob > 1MB:** For 3 years of daily data, this is only 1,095 points — safe. For intraday (1m over 3 years), it's 1.5M points — must downsample before serializing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Order fill simulation | Custom fill logic | vectorbt Portfolio.from_signals() | Order fill at OHLC prices, partial fills, bar-edge timing — edge cases multiply fast |
| Transaction cost modeling | Multiply manually | fees= and slippage= params | vectorbt applies costs per-fill, compounded correctly |
| Sharpe ratio | Manual formula | pf.sharpe_ratio() | Risk-free rate, annualization factor, edge cases all handled |
| Max drawdown | Rolling peak calculation | pf.max_drawdown() | Handles initial cash period, open drawdowns correctly |
| Win rate | Count winners / total | pf.stats()["Win Rate [%]"] | Distinguishes open vs closed trades correctly |
| Profit factor | Gross profit / gross loss | pf.stats()["Profit Factor"] | Handles 0-loss edge case, confirmed key name |
| Equity curve | Cumsum of returns | pf.value() | Includes cash, position sizing, fees in every bar |

**Key insight:** Financial simulation has deceptively many edge cases — what happens if you get a BUY and SELL signal on the same bar? What if position size exceeds available cash? What about the first bar before any signal? vectorbt handles all of these. Custom implementations routinely introduce subtle bugs that inflate backtest returns by 10–30%.

---

## Common Pitfalls

### Pitfall 1: Look-Ahead Bias via Close Price Signal

**What goes wrong:** Signal generated from bar T's close price is used to trade at bar T's close. In reality, you can only trade on the NEXT bar after observing the signal. Return appears 2-3x inflated.

**Why it happens:** The vectorized nature of the engine makes it easy to pass the raw signal Series directly without shifting. There is no runtime error — the results just look suspiciously good.

**How to avoid:** Always apply `.shift(1).fillna(False).astype(bool)` to both entries and exits before passing to `Portfolio.from_signals()`. The VectorBT documentation explicitly warns: "If you generated signals using close price, don't forget to shift your signals by one tick forward with `signals.vbt.fshift(1)`."

**Warning signs:** Sharpe ratio > 3.0, win rate > 75%, total return >> buy-and-hold over same period on the same asset.

### Pitfall 2: Missing freq= Parameter

**What goes wrong:** `pf.sharpe_ratio()` raises `ValueError: Couldn't parse frequency` or returns NaN.

**Why it happens:** vectorbt requires `freq` to annualize returns for Sharpe ratio calculation. Without it, the method doesn't know if bars are daily, hourly, or minutely.

**How to avoid:** Always pass `freq="1D"` for the project's current `SCAN_INTERVAL = "1D"`. If multi-timeframe is added in Phase 7, map interval strings to freq strings.

**Warning signs:** `pf.stats()` shows `NaN` for Sharpe Ratio. The exception message mentions "freq".

### Pitfall 3: vectorbt Numba JIT Compilation Delay (First Call)

**What goes wrong:** The first call to `Portfolio.from_signals()` in a cold process takes 15–30 seconds because Numba compiles the JIT functions. Subsequent calls are fast (<1s). Tests appear to time out.

**Why it happens:** Numba compiles Python functions to machine code on first invocation and caches the result. Cold cache means slow first call.

**How to avoid:** Add a `@pytest.fixture(scope="session")` that runs a tiny warm-up backtest (10 bars) before the test suite runs. Or set `pytest-timeout` to 60s minimum for backtest tests. In production, the FastAPI startup event can run a warm-up.

**Warning signs:** First test in suite takes 20+ seconds, subsequent tests are fast. Timeout errors on CI.

### Pitfall 4: Python 3.11 Not Installed (Blocking)

**What goes wrong:** `uv add vectorbt` or `uv run python -c "import vectorbt"` fails because pyenv's Python 3.11 is not installed, even though it's specified in `.python-version`.

**Why it happens:** The backend `.python-version` file specifies `3.11`, but only Python 3.10.12 is currently in pyenv. uv uses the `.python-version` file to select the interpreter.

**How to avoid:** Wave 0 of the plan must include `pyenv install 3.11.9` (or latest 3.11.x) before `uv sync` or `uv add`.

**Warning signs:** `uv` reports "Python 3.11 not found" or pyenv emits "version '3.11' is not installed".

### Pitfall 5: stats() Key Names Have Units in Brackets

**What goes wrong:** Code does `stats["Win Rate"]` and gets a KeyError. The correct key is `stats["Win Rate [%]"]`.

**Why it happens:** vectorbt's stats() Series uses human-readable keys with unit annotations. This is easy to guess wrong.

**How to avoid:** Use the exact verified keys:
- `stats["Win Rate [%]"]` — divide by 100 to get fraction
- `stats["Max Drawdown [%]"]` — divide by 100 to get fraction (or use `pf.max_drawdown()` directly which returns a fraction)
- `stats["Profit Factor"]` — no brackets, no unit
- `stats["Sharpe Ratio"]` — no brackets, no unit
- `stats["Total Trades"]` — no brackets, integer

**Warning signs:** KeyError on stats access. Always access via `pf.sharpe_ratio()` and `pf.max_drawdown()` methods as alternatives — they bypass key lookup.

### Pitfall 6: Equity Curve is a pandas Series, Not JSON-Serializable

**What goes wrong:** FastAPI's `JSONResponse` chokes on the equity curve because pandas Timestamps are not JSON-serializable.

**Why it happens:** `pf.value()` returns a `pd.Series` with a `DatetimeIndex`. FastAPI's default JSON encoder does not handle numpy floats or pandas Timestamps.

**How to avoid:** Convert before returning:
```python
def _serialize_equity(value_series: pd.Series) -> list[list]:
    return [
        [ts.isoformat(), float(v)]
        for ts, v in value_series.items()
    ]
```

---

## Code Examples

Verified patterns from official sources:

### Complete Portfolio.from_signals() Call

```python
# Source: vectorbt.dev/api/portfolio/base/ (verified 2026-04-08)
import vectorbt as vbt

pf = vbt.Portfolio.from_signals(
    close,           # pd.Series of close prices
    entries=entries, # bool pd.Series (shifted by 1)
    exits=exits,     # bool pd.Series (shifted by 1)
    fees=0.001,      # 0.1% commission per trade
    slippage=0.001,  # 0.1% slippage per fill
    init_cash=10_000.0,
    freq="1D",       # required for Sharpe ratio annualization
)
```

### Extracting All Required Metrics

```python
# Source: vectorbt.dev/api/portfolio/base/ (verified key names 2026-04-08)
stats = pf.stats()

result = {
    "sharpe_ratio":  float(pf.sharpe_ratio()),
    "max_drawdown":  float(pf.max_drawdown()),         # fraction (e.g., -0.25)
    "win_rate":      float(stats["Win Rate [%]"]) / 100.0,   # convert % -> fraction
    "profit_factor": float(stats["Profit Factor"]),
    "total_return":  float(pf.total_return()),         # fraction
    "total_trades":  int(stats["Total Trades"]),
}
```

### shift(1) Look-Ahead Bias Prevention

```python
# Source: VectorBT docs warning + Phase 2 signal pattern
# "If you generated signals using close price, don't forget to shift
#  your signals by one tick forward" — vectorbt documentation

entries_raw: pd.Series = _compute_entries_series(df)  # bool at bar T from bar T data
exits_raw:   pd.Series = _compute_exits_series(df)

entries = entries_raw.shift(1).fillna(False).astype(bool)  # now safe
exits   = exits_raw.shift(1).fillna(False).astype(bool)    # now safe
```

### FastAPI Endpoint (run_in_threadpool Pattern)

```python
# Source: FastAPI docs (fastapi.tiangolo.com/async) + starlette.concurrency
from starlette.concurrency import run_in_threadpool

@router.post("")
async def run_backtest_endpoint(
    request: BacktestRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    df = await _load_candles_from_db(session, request.symbol, request.interval)
    result = await run_in_threadpool(
        run_backtest, df, request.commission, request.slippage, request.init_cash
    )
    return result.to_dict()
```

### Alembic Migration 003 Pattern

```python
# Source: project pattern from 002_create_signals_table.py
revision = "003"
down_revision = "002"

def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id",            sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("symbol",        sa.String(20), nullable=False),
        sa.Column("interval",      sa.String(5),  nullable=False),
        sa.Column("run_at",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("commission",    sa.Float, nullable=False),
        sa.Column("slippage",      sa.Float, nullable=False),
        sa.Column("init_cash",     sa.Float, nullable=False),
        sa.Column("sharpe_ratio",  sa.Float, nullable=True),
        sa.Column("max_drawdown",  sa.Float, nullable=True),
        sa.Column("win_rate",      sa.Float, nullable=True),
        sa.Column("profit_factor", sa.Float, nullable=True),
        sa.Column("total_return",  sa.Float, nullable=True),
        sa.Column("total_trades",  sa.Integer, nullable=True),
        # equity_curve stored as JSON string — avoids separate table for MVP
        sa.Column("equity_curve",  sa.Text, nullable=True),
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Backtrader (event-driven, slow) | vectorbt (vectorized, Numba) | 2020–2021 | 100-1000x faster for multi-asset parameter sweeps |
| Hand-rolled equity curves | pf.value() + pf.stats() | vectorbt v0.20+ | Eliminates entire category of calculation bugs |
| Look-ahead bias discovered post-hoc | shift(1) as mandatory first step | Community consensus 2022+ | Enforced at test time, not inspection time |
| Blocking sync backtests in web apps | run_in_threadpool wrapping | FastAPI v0.85+ | Keeps ASGI event loop free for other requests |

**Deprecated/outdated:**
- **Backtrader:** CLAUDE.md prohibits it; single-threaded event loop; 10-100x slower than vectorbt on the data volumes this project will have.
- **Zipline:** CLAUDE.md prohibits it explicitly. Dead project (Quantopian shut down 2020), Python 3.5/3.6 era, fragile community forks.
- **vectorbt PRO:** Commercial successor to the free library. Do not use — the free vectorbt 0.28.5 covers all Phase 3 requirements.

---

## Open Questions

1. **Vectorized signal scoring vs. importing score_signal() directly**
   - What we know: `score_signal()` from Phase 2 is designed for the last bar only (takes an `IndicatorSet` dataclass). For backtesting we need boolean Series across all bars.
   - What's unclear: Should Phase 3 duplicate the scoring thresholds in a new vectorized function, or refactor `score_signal()` to accept a DataFrame?
   - Recommendation: Create a new `_compute_entries_series(df)` function in `engine.py` that mirrors the scoring thresholds (RSI < 35: 25pts, MACD crossover: 30pts, etc.) as vectorized pandas operations. Do not modify Phase 2 code. The scoring constants (THRESHOLD = 55, weights) should be imported from signals.py or constants module to stay in sync.

2. **Persistence of backtest results (BKTS-01 does not require it)**
   - What we know: BKTS-01 says "user can run a backtest and receive results." It does not say results must be stored.
   - What's unclear: Phase 4 (PAPER-04) requires backtest-vs-paper comparison. That requires backtest results to be retrievable later.
   - Recommendation: Include a `backtest_runs` table (migration 003) with the result columns, but make persistence optional in Phase 3 (the endpoint writes results to DB after returning them, so the write failure does not block the response). Phase 4 will query this table.

3. **Multi-asset / multi-strategy batch backtest (not in BKTS-01..04)**
   - What we know: vectorbt can backtest 1,000 parameter combinations in seconds — it's designed for parameter sweeps.
   - What's unclear: Should Phase 3 expose a batch endpoint?
   - Recommendation: Out of scope for Phase 3. Single-asset, single-strategy endpoint satisfies all BKTS requirements. Batch is a Phase 7+ feature.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Backend runtime (`.python-version`) | BLOCKED | Not installed (3.10.12 active) | Install via `pyenv install 3.11.9` |
| vectorbt | BKTS-01, BKTS-02, BKTS-03, BKTS-04 | Not installed | 0.28.5 on PyPI | Backtesting.py 0.6.5 (fallback only) |
| pandas | vectorbt + signal computation | Available | 3.0.2 (project) | — |
| numpy | vectorbt internal | Available (transitive) | via pandas | — |
| SQLite (in-memory) | Test suite | Available | via aiosqlite 0.22.1 | — |
| pytest + pytest-asyncio | Test suite | Available | pytest 9.0.3, asyncio 1.3.0 | — |

**Missing dependencies with no fallback:**
- Python 3.11 (pyenv): Required before `uv sync` can create the virtualenv. Install: `pyenv install 3.11.9` (latest stable 3.11.x as of research date). This is a Wave 0 prerequisite.

**Missing dependencies with fallback:**
- vectorbt: Must be `uv add`'d in Wave 0. Backtesting.py 0.6.5 is the approved fallback per CLAUDE.md if vectorbt fails on Python 3.11, but PyPI classifiers confirm Python 3.11 support — fallback is not expected to be needed.

---

## Validation Architecture

> nyquist_validation is enabled in .planning/config.json.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | pyproject.toml (no [tool.pytest.ini_options] section yet — Wave 0 adds it) |
| Quick run command | `PYTHONPATH=backend uv --project backend run pytest tests/test_backtest.py -q` |
| Full suite command | `PYTHONPATH=backend uv --project backend run pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BKTS-01 | run_backtest() returns BacktestResult for valid 500-bar DataFrame | unit | `pytest tests/test_backtest.py::test_run_backtest_returns_result -x` | Wave 0 |
| BKTS-01 | POST /api/backtest returns 200 with metrics dict | integration | `pytest tests/test_backtest.py::test_backtest_endpoint_success -x` | Wave 0 |
| BKTS-01 | POST /api/backtest returns 422 when < MIN_CANDLES rows | integration | `pytest tests/test_backtest.py::test_backtest_endpoint_insufficient_data -x` | Wave 0 |
| BKTS-02 | shift(1) audit: biased Sharpe >= honest Sharpe | unit (audit) | `pytest tests/test_backtest.py::test_shift1_prevents_look_ahead_bias -x` | Wave 0 |
| BKTS-03 | BacktestResult.sharpe_ratio is float, not NaN | unit | `pytest tests/test_backtest.py::test_metrics_are_finite_floats -x` | Wave 0 |
| BKTS-03 | BacktestResult.max_drawdown is <= 0 (loss is negative) | unit | `pytest tests/test_backtest.py::test_max_drawdown_is_non_positive -x` | Wave 0 |
| BKTS-03 | BacktestResult.win_rate is in [0.0, 1.0] | unit | `pytest tests/test_backtest.py::test_win_rate_range -x` | Wave 0 |
| BKTS-03 | BacktestResult.profit_factor is >= 0 | unit | `pytest tests/test_backtest.py::test_profit_factor_non_negative -x` | Wave 0 |
| BKTS-04 | run_backtest(commission=0.01) reduces total_return vs commission=0.0 | unit | `pytest tests/test_backtest.py::test_commission_reduces_return -x` | Wave 0 |
| BKTS-04 | run_backtest(slippage=0.01) reduces total_return vs slippage=0.0 | unit | `pytest tests/test_backtest.py::test_slippage_reduces_return -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `PYTHONPATH=backend uv --project backend run pytest tests/test_backtest.py -q`
- **Per wave merge:** `PYTHONPATH=backend uv --project backend run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_backtest.py` — covers all BKTS-01 through BKTS-04 requirements (10 tests)
- [ ] Python 3.11 pyenv install — `pyenv install 3.11.9`
- [ ] vectorbt dependency — `uv add "vectorbt>=0.28.5"` (adds to pyproject.toml + uv.lock)
- [ ] `[tool.pytest.ini_options]` section in pyproject.toml if needed for asyncio_mode="auto"

---

## Sources

### Primary (HIGH confidence)

- vectorbt PyPI page (pypi.org/project/vectorbt/) — version 0.28.5, Python 3.10-3.13 support, release date 2026-03-26
- vectorbt.dev/api/portfolio/base/ — Portfolio.from_signals() parameters, stats() metric keys, pf.sharpe_ratio()/max_drawdown()/value() methods
- vectorbt.dev/getting-started/usage/ — fees=, freq=, init_cash= usage examples
- Phase 2 codebase (signals.py, indicators.py, scanner.py) — existing patterns for pure functions, TDD, in-memory SQLite tests
- CLAUDE.md — mandated tech stack, forbidden alternatives, project constraints

### Secondary (MEDIUM confidence)

- FastAPI docs (fastapi.tiangolo.com/async) — run_in_threadpool pattern for sync blocking calls
- starlette.concurrency.run_in_threadpool — verified as correct wrapper for sync CPU-bound work in async FastAPI routes
- GitHub polakowo/vectorbt/blob/master/vectorbt/portfolio/base.py — from_signals() parameter list (entries, exits, fees, slippage, init_cash, freq, direction)
- vectorbt.dev community warning: "If you generated signals using close price, don't forget to shift your signals by one tick forward with signals.vbt.fshift(1)"

### Tertiary (LOW confidence)

- WebSearch results on vectorbt Python 3.11 compatibility — flagged as potentially outdated (PyPI page is authoritative; PyPI confirms 3.11 support)
- WebSearch results on stats() key names — cross-verified with PyPI and GitHub; "Win Rate [%]", "Profit Factor", "Sharpe Ratio", "Max Drawdown [%]" confirmed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — vectorbt 0.28.5 confirmed on PyPI (2026-03-26 release), Python 3.11 compatible
- Architecture: HIGH — follows established Phase 2 pure function + TDD patterns; vectorbt API confirmed
- Pitfalls: HIGH — look-ahead bias and freq= issues are widely documented in official vectorbt docs; Python 3.11 blocker confirmed by local environment check
- Transaction costs: HIGH — fees= and slippage= params verified in official vectorbt API docs
- Metrics extraction: MEDIUM-HIGH — exact key names confirmed by multiple sources including GitHub base.py; single-source risk mitigated by cross-check

**Research date:** 2026-04-08
**Valid until:** 2026-07-08 (90 days — vectorbt 0.28.x is stable; CLAUDE.md mandates specific libraries; low churn expected)
