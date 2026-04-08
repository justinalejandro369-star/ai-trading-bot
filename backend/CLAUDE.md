# Backend — Developer Guide

FastAPI backend: data ingestion, signal analysis, backtesting, paper trading, alerts, and LLM explanations.

## Running Tests

```bash
# From repo root — PYTHONPATH must include backend/
PYTHONPATH=backend uv --project backend run pytest tests/ -q

# Single file
PYTHONPATH=backend uv --project backend run pytest tests/test_indicators.py -v

# With coverage
PYTHONPATH=backend uv --project backend run pytest tests/ --cov=app -q
```

## Starting the Dev Server

```bash
cd backend
uv sync
uv run alembic upgrade head          # run migrations first
uv run uvicorn app.main:app --reload  # http://localhost:8000
```

## Module Map (`app/`)

| Directory | Purpose |
|-----------|---------|
| `core/` | Config (pydantic-settings), database engine, auth dependency, rate limiter, security utils, watchlists |
| `ingestion/` | OHLCVProvider ABC, 5 data providers, TTL cache, normalizers, upsert helper, APScheduler lifespan |
| `analysis/` | indicators, signals, scanner, regime classifier, multiframe, LLM explainer |
| `backtesting/` | vectorbt engine (pure fn), BacktestResult model, API router |
| `paper_trading/` | fill_order + compute_equity (pure fns), equity snapshot job, DB helpers |
| `alerts/` | check_alerts engine (pure fn), alert scheduler job, notification dispatch |
| `education/` | Static lesson content served via REST |
| `api/routes/` | One router per domain: auth, market_data, indicators, signals, backtest, paper_trading, alerts, education, websocket |
| `models/` | SQLAlchemy ORM models |

## Adding a New Data Provider

1. Create `app/ingestion/providers/my_provider.py`
2. Implement `OHLCVProvider` ABC from `app.ingestion.base_provider`:
   ```python
   from app.ingestion.base_provider import OHLCVCandle, OHLCVProvider

   class MyProvider(OHLCVProvider):
       async def fetch_historical(self, symbol, interval, start, end) -> list[OHLCVCandle]:
           ...  # normalize to OHLCVCandle dataclass

       async def fetch_latest(self, symbol, interval) -> list[OHLCVCandle]:
           ...
   ```
3. Add a scheduler job in `app/ingestion/scheduler.py` using `IntervalTrigger`
4. Call `upsert_candles(session, candles)` — DO NOTHING on conflict, idempotent

## Adding a New API Route

1. Create `app/api/routes/my_route.py`:
   ```python
   from fastapi import APIRouter
   router = APIRouter(prefix="/my-resource", tags=["my-resource"])

   @router.get("/")
   async def list_things(...):
       ...
   ```
2. Import and register in `app/main.py`:
   ```python
   from app.api.routes.my_route import router as my_router
   app.include_router(my_router, prefix="/api", dependencies=_auth_dep)
   ```

## Creating a New Alembic Migration

```bash
cd backend
uv run alembic revision --autogenerate -m "describe_change"
# Edit the generated file — verify down_revision matches previous migration id
uv run alembic upgrade head
```

**Critical:** `down_revision` must exactly match the `revision` value of the prior migration. Check `alembic/versions/` — files are numbered 001–007.

Current chain: `001 → 002 → 003 → 004 → 005 → 006 → 007`

## Key Patterns

### Pure Functions for Engines
All analysis engines take data in, return results out — no side effects:
```python
# Good — testable without DB/FastAPI
result = compute_indicators(df, "AAPL", "1D")
signal = score_signal(result)
regime = detect_regime(result, atr_sma_20=1.23)
```

### Async SQLAlchemy Sessions
```python
from app.core.database import async_session_factory

async with async_session_factory() as session:
    result = await session.execute(text("SELECT ..."), {"param": value})
    await session.commit()
```

Never use synchronous SQLAlchemy. All session creation uses `async_session_factory()`.

### Settings Access
```python
from app.core.config import settings

settings.DATABASE_URL
settings.openai_api_key
settings.llm_enabled
```

### run_in_threadpool for Sync Libs
```python
from starlette.concurrency import run_in_threadpool

# yfinance and some CCXT methods are synchronous
data = await run_in_threadpool(sync_fn, arg1, arg2)
```

### get_session in Route Handlers
```python
from app.core.database import get_session

@router.get("/things")
async def list_things(session: AsyncSession = Depends(get_session)):
    ...
```

## pandas-ta-classic Column Names

Package: `pandas-ta-classic` (NOT `pandas-ta`). Import: `import pandas_ta_classic as ta`.

Exact column names returned by each function:

| Indicator | Column Name(s) |
|-----------|---------------|
| RSI(14) | `rsi` Series — no column wrapping |
| MACD(12,26,9) | `MACD_12_26_9`, `MACDs_12_26_9`, `MACDh_12_26_9` |
| Bollinger Bands(20, 2.0) | `BBU_20_2.0`, `BBL_20_2.0`, `BBP_20_2.0` |
| ADX(14) | `ADX_14` |
| ATR(14) | `ATRr_14` |
| EMA(50) | `EMA_50` |
| EMA(200) | `EMA_200` |
| SMA(20) on volume | `SMA_20` |

**VWAP is intentionally omitted** — only valid on intraday candles; meaningless on 1D.

## MIN_CANDLES = 200

`compute_indicators()` returns `None` if `len(df) < 200`. EMA-200 requires exactly 200 rows. The scanner silently skips assets with insufficient history (logged at DEBUG).

## Upsert Semantics

- `market_data`: `ON CONFLICT (symbol, interval, timestamp) DO NOTHING` — candles are immutable
- `signals`: `ON CONFLICT (symbol, interval) DO UPDATE SET ...` — always refreshed on each scan

## Test Fixtures (`tests/conftest.py`)

- `db_session` — in-memory SQLite async session with schema applied
- `sample_df` — 250-row OHLCV DataFrame (enough for MIN_CANDLES=200)
- `sample_indicator_set` — pre-computed IndicatorSet for signal tests
- `mock_provider` — AsyncMock of OHLCVProvider returning synthetic candles
