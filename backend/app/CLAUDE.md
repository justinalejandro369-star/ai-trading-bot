# app/ — Module Guide

Concise reference for every subdirectory. See each module's own CLAUDE.md for deeper docs.

## Subdirectory Map

| Directory | One-line purpose |
|-----------|-----------------|
| `core/` | Shared infrastructure: config, DB engine, auth dependency, rate limiter, security utils, watchlists |
| `ingestion/` | Data providers (yfinance, CoinGecko, CCXT, Finnhub, Forex), scheduler, upsert, normalizer, cache |
| `analysis/` | Pure-function indicator computation, weighted signal scoring, regime detection, LLM explainer, multi-timeframe |
| `backtesting/` | vectorbt backtest engine (pure fn), BacktestResult model |
| `paper_trading/` | Order fill simulation, equity computation, equity snapshot job |
| `alerts/` | Alert rule evaluation engine, scheduler job, Telegram/Discord notification dispatch |
| `education/` | Static lesson content (no DB) |
| `api/routes/` | FastAPI routers — one file per domain |
| `models/` | SQLAlchemy ORM models (market_data, signals, backtest_runs, paper_*, alert_rules, users) |

## Import Patterns

```python
# Settings — always singleton
from app.core.config import settings

# DB session — use context manager
from app.core.database import async_session_factory, get_session
async with async_session_factory() as session:
    ...

# Auth dependency (injected by main.py at router level, not per-route)
from app.core.auth import get_current_user

# Data provider ABC
from app.ingestion.base_provider import OHLCVCandle, OHLCVProvider

# Upsert helper
from app.ingestion.upsert import upsert_candles

# Analysis engines
from app.analysis.indicators import compute_indicators, IndicatorSet, MIN_CANDLES
from app.analysis.signals import score_signal, SignalResult
from app.analysis.regime import detect_regime
from app.analysis.scanner import scan_all_assets

# Watchlists (defined here to avoid circular import between scanner.py and scheduler.py)
from app.core.watchlists import STOCK_WATCHLIST, CCXT_CRYPTO_SYMBOLS
```

## Circular Import Avoidance

`app/core/watchlists.py` exists solely to break the circular import between:
- `app/ingestion/scheduler.py` (imports watchlists to iterate symbols)
- `app/analysis/scanner.py` (imports watchlists to iterate symbols)

If `STOCK_WATCHLIST` lived in `scheduler.py`, `scanner.py` would import `scheduler.py`, which imports `scanner.py` → circular. Solution: both import from `app.core.watchlists`.

## API Route Registration (main.py)

```python
# Unprotected
app.include_router(auth_router, prefix="/auth")
app.include_router(ws_router)
app.include_router(education_router, prefix="/api")

# JWT-protected (dependency injected at router level)
_auth_dep = [Depends(get_current_user)]
app.include_router(market_data_router, prefix="/api", dependencies=_auth_dep)
app.include_router(signals_router, prefix="/api", dependencies=_auth_dep)
# ... etc
```

## Database Session in Route Handlers

```python
from app.core.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

@router.get("/things")
async def handler(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("SELECT ..."), {})
    rows = result.fetchall()
    return rows
```

## Settings Access

```python
from app.core.config import settings

# All env vars are attributes — type-safe, validated at startup
settings.DATABASE_URL          # str
settings.llm_enabled           # bool
settings.openai_api_key        # str (empty = disabled)
settings.frontend_url          # str
settings.jwt_secret            # str
```
