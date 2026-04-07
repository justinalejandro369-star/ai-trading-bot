# Phase 1: Data Foundation - Research

**Researched:** 2026-04-06
**Domain:** Data ingestion, time-series storage, provider abstraction, scheduling
**Confidence:** MEDIUM-HIGH (core stack HIGH; CoinGecko/Finnhub behavior under sustained load LOW)

---

## Project Constraints (from CLAUDE.md)

- **Data sources:** Free only — Yahoo Finance, CoinGecko, free API tiers
- **Tech stack:** Python-first backend
- **Deployment:** Web dashboard via browser
- **Budget:** Zero ongoing data costs; minimal infrastructure costs
- **Workflow:** All file changes must go through a GSD command entry point

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | System ingests US stock OHLCV data via yfinance with Finnhub WebSocket for real-time updates | yfinance 1.2.0 for batch historical; Finnhub free WS (50 symbols, 60 req/min) for live ticks |
| DATA-02 | System ingests crypto data (BTC, ETH, top altcoins) via CoinGecko API | pycoingecko 3.2.0; Demo plan: 30 req/min, 10k calls/month; OHLCV via `get_coin_ohlc_by_id` |
| DATA-03 | System supports multiple timeframes (1m, 5m, 15m, 1H, 4H, 1D candles) | yfinance supports 1m/5m/15m/30m/1h/1d natively; CoinGecko provides daily/hourly OHLCV |
| DATA-04 | Data provider abstraction layer allows swapping sources without code changes | ABC-based provider interface pattern; normalizer maps all sources to canonical OHLCV schema |
| DATA-05 | System stores historical OHLCV data in TimescaleDB for fast time-series queries | TimescaleDB 2.18 on Docker (timescale/timescaledb:latest-pg16); 3.4x faster than plain PG for OHLCV queries |
</phase_requirements>

---

## Summary

Phase 1 builds the data pipeline foundation that all later phases consume. The work breaks into four areas: (1) schema and database setup using TimescaleDB as a PostgreSQL extension, (2) a provider abstraction layer with a normalized OHLCV interface, (3) two concrete provider implementations (yfinance for stocks, pycoingecko for crypto), and (4) APScheduler jobs that maintain data freshness without manual intervention.

The most important constraint to build around is the CoinGecko rate limit: 30 calls/minute and 10,000 calls/month on the free Demo plan. At naive polling frequency this is exhausted in roughly 1.4 days. The entire scheduling and caching strategy must be designed around this cap from day one. Finnhub's WebSocket free tier allows 50 subscribed symbols simultaneously — sufficient for an MVP watchlist.

TimescaleDB is the right choice over plain PostgreSQL for this phase. Benchmarks show 3.4x faster OHLCV aggregation queries, and the Docker image (`timescale/timescaledb:latest-pg16`) makes the setup no more complex than plain Postgres. The critical Alembic friction point is that `create_hypertable()` must be called via raw SQL in a migration rather than through ORM table creation — this is a known pattern and requires one explicit migration step.

**Primary recommendation:** Build yfinance batch ingestion first, get TimescaleDB schema + Alembic migrations working, validate end-to-end data flow, then layer in Finnhub WebSocket and CoinGecko. Do not build all providers simultaneously.

---

## Standard Stack

### Core (Phase 1 specific)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| yfinance | 1.2.0 | Batch historical OHLCV for US stocks | Latest stable; supports all needed intervals; best free stock data coverage |
| pycoingecko | 3.2.0 | Crypto OHLCV via CoinGecko Demo API | Official Python wrapper; supports all CoinGecko endpoints |
| APScheduler | 3.11.2 | Periodic ingestion scheduling | In-process scheduler; no Redis/Celery complexity; `AsyncIOScheduler` integrates with FastAPI lifespan |
| SQLAlchemy | 2.0.49 | ORM for market_data table | Async-compatible; SQLite↔Postgres swap; required for Alembic |
| Alembic | 1.18.4 | Schema migrations | SQLAlchemy companion; TimescaleDB hypertable requires raw SQL in migration |
| psycopg2-binary | 2.9.11 | Synchronous PostgreSQL driver (dev/migration) | Required by Alembic for migration execution |
| asyncpg | 0.31.0 | Async PostgreSQL driver (runtime) | Required by SQLAlchemy async engine for FastAPI |
| websockets | (see notes) | Finnhub WebSocket client | Pure Python WS library; used by official Finnhub examples |
| httpx | 0.28.1 | Async HTTP client for REST API calls | Async-native; used for any REST fallback or rate-limit-aware fetching |
| pydantic | 2.12.5 | OHLCV schema validation | Already a FastAPI dependency; validates normalized candle records |

**Version verification:** All versions confirmed via `pip3 index versions` against PyPI on 2026-04-06. [VERIFIED: PyPI registry]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | latest | `.env` file loading | API keys for Finnhub, CoinGecko must never be in source |
| pydantic-settings | latest | Type-safe settings from env | FastAPI-idiomatic config management |
| pytest | 9.0.2 | Test runner | All ingestion logic needs unit tests |
| pytest-asyncio | 1.3.0 | Async test support | Scheduler and async provider tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APScheduler | Celery + Redis | Celery is for scale; APScheduler is simpler for single-process MVP — decision locked per STATE.md |
| TimescaleDB | Plain PostgreSQL + composite index | TimescaleDB is 3.4x faster for OHLCV aggregations; Docker complexity is identical |
| pycoingecko | Raw httpx calls to CoinGecko | pycoingecko 3.2.0 is actively maintained and wraps all endpoints; no reason to go raw |
| yfinance | Alpha Vantage | Alpha Vantage free tier is 25 req/day — insufficient for multi-symbol backfill |

**Installation:**
```bash
uv add yfinance pycoingecko apscheduler sqlalchemy alembic \
       psycopg2-binary asyncpg websockets httpx \
       python-dotenv pydantic-settings

uv add --dev pytest pytest-asyncio
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 1 scope)
```
backend/
├── app/
│   ├── main.py                    # FastAPI app; APScheduler started in lifespan
│   ├── core/
│   │   ├── config.py              # pydantic-settings; loads API keys from env
│   │   └── database.py            # SQLAlchemy async engine + session factory
│   ├── ingestion/
│   │   ├── base_provider.py       # ABC: OHLCVProvider interface
│   │   ├── normalizer.py          # maps all source formats to OHLCVCandle
│   │   ├── cache.py               # in-memory TTL cache; protects rate limits
│   │   ├── scheduler.py           # APScheduler job definitions + lifespan hook
│   │   └── providers/
│   │       ├── yfinance_provider.py    # stocks: batch history + incremental
│   │       ├── finnhub_provider.py    # stocks: WebSocket real-time ticks
│   │       └── coingecko_provider.py  # crypto: OHLCV via pycoingecko
│   └── models/
│       └── market_data.py         # SQLAlchemy model: OHLCVCandle table
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_create_ohlcv_hypertable.py   # raw SQL: CREATE TABLE + create_hypertable()
└── tests/
    ├── test_providers.py
    ├── test_normalizer.py
    └── test_scheduler.py
```

### Pattern 1: Provider Abstraction Interface

**What:** An abstract base class defines the contract all data sources must satisfy. Concrete providers implement this interface. The scheduler and ingestion pipeline only call the interface, never provider-specific code.

**When to use:** Any time a new data source is added. Strategy code in Phase 2 reads only from the database — it never calls providers directly.

```python
# Source: design pattern derived from Freqtrade and CCXT conventions [ASSUMED]
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class OHLCVCandle:
    symbol: str
    market: str          # "stock" | "crypto"
    timestamp: datetime
    interval: str        # "1m" | "5m" | "15m" | "1H" | "4H" | "1D"
    open: float
    high: float
    low: float
    close: float
    volume: float

class OHLCVProvider(ABC):
    @abstractmethod
    async def fetch_historical(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVCandle]:
        """Backfill: fetch historical candles for a date range."""
        ...

    @abstractmethod
    async def fetch_latest(
        self,
        symbol: str,
        interval: str,
    ) -> list[OHLCVCandle]:
        """Incremental: fetch the most recent N candles since last stored timestamp."""
        ...
```

### Pattern 2: yfinance Historical Download

**What:** `yf.download()` batch-fetches OHLCV for one or more symbols. Used only for historical backfill — never in a tight polling loop.

**Critical limits:**
- 1m data: last 7 days only [VERIFIED: PyPI / official yfinance docs]
- Intraday (1m–1h): last 60 days only [VERIFIED: PyPI / official yfinance docs]
- Daily (1d): multiple years available

```python
# Source: yfinance official README / pypi.org [CITED: https://pypi.org/project/yfinance/]
import yfinance as yf
import pandas as pd

def fetch_stock_ohlcv(symbol: str, interval: str, period: str) -> pd.DataFrame:
    """
    interval: "1m", "5m", "15m", "1h", "1d"
    period:   "7d" (1m only), "60d" (intraday), "2y" (daily)
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    # Returns DataFrame with columns: Open, High, Low, Close, Volume
    # Index: DatetimeIndex (timezone-aware)
    return df

# Multi-symbol batch (cheaper — one request)
def fetch_multiple(symbols: list[str], interval: str, period: str) -> pd.DataFrame:
    data = yf.download(
        tickers=" ".join(symbols),
        period=period,
        interval=interval,
        group_by="ticker",
        auto_adjust=True,
        progress=False,
    )
    return data
```

### Pattern 3: CoinGecko OHLCV via pycoingecko

**What:** `get_coin_ohlc_by_id` returns OHLC data as a list of lists `[timestamp_ms, open, high, low, close]`. CoinGecko OHLCV does NOT include volume at the OHLC endpoint — volume must be fetched separately from `/coins/{id}/market_chart`.

**Rate limit budget (10,000 calls/month):**
- At 30 coins, polling every 5 minutes = 30 × 288 = 8,640 calls/day = exhausted in < 2 days
- Safe schedule: poll top-10 coins every 15 minutes = 10 × 96 = 960 calls/day → 28,800/month (**over cap**)
- **Actual safe schedule:** 5 coins every 30 minutes = 5 × 48 = 240 calls/day → 7,200/month (within cap)
- OR: cache OHLCV responses and only re-fetch when TTL (60 seconds minimum per Demo plan) expires

```python
# Source: pycoingecko README + CoinGecko API docs [CITED: https://docs.coingecko.com/reference/coins-id-ohlc]
from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI(api_key="YOUR_DEMO_KEY")  # Demo key: 30 req/min, 10k/month

# Returns: [[timestamp_ms, open, high, low, close], ...]
# days options: 1, 7, 14, 30, 90, 180, 365, "max"
ohlc_raw = cg.get_coin_ohlc_by_id(
    id="bitcoin",
    vs_currency="usd",
    days=30,
)
# Candle granularity is auto-determined by 'days':
#   1-2 days  → 30-minute candles
#   3-30 days → 4-hour candles
#   31+ days  → 4-day candles
# NOTE: CoinGecko does NOT support 1m/5m/15m OHLCV on the free tier
# [VERIFIED: CoinGecko API docs https://docs.coingecko.com/reference/coins-id-ohlc]
```

**CoinGecko granularity limitation:** The free Demo plan auto-selects candle size based on the `days` parameter. You cannot request arbitrary timeframes like 1H or 15m. 1-day requests return 30-minute candles; 3-30 day requests return 4-hour candles. This means DATA-03 (1m/5m/15m support) for crypto is NOT achievable via CoinGecko. Use CCXT (Binance public API) for fine-grained crypto candles. [VERIFIED: CoinGecko API docs]

### Pattern 4: Finnhub WebSocket

**What:** Finnhub provides a WebSocket endpoint for real-time trade events. Each message contains symbol, price, volume, and timestamp. Free tier: 60 API calls/minute and simultaneous subscription to up to 50 symbols.

```python
# Source: Finnhub official API docs [CITED: https://finnhub.io/docs/api/websocket-trades]
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    if data.get("type") == "trade":
        for trade in data.get("data", []):
            # trade: {"s": "AAPL", "p": 150.25, "v": 100, "t": 1617000000000}
            symbol = trade["s"]
            price  = trade["p"]
            volume = trade["v"]
            ts_ms  = trade["t"]
            # Write last-price tick to DB or in-memory buffer

def on_open(ws):
    symbols = ["AAPL", "MSFT", "GOOGL"]  # max 50 on free tier
    for sym in symbols:
        ws.send(json.dumps({"type": "subscribe", "symbol": sym}))

ws = websocket.WebSocketApp(
    f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}",
    on_message=on_message,
    on_open=on_open,
)
ws.run_forever()
```

**Important:** Finnhub WS only provides real-time TRADE events (last price). It does not produce pre-formed OHLCV candles. The ingestion layer must aggregate ticks into OHLCV bars in-memory or via a TimescaleDB continuous aggregate. For Phase 1 MVP, recording the last-price tick is sufficient; full 1m bar construction from ticks is a Phase 2 concern.

### Pattern 5: TimescaleDB Hypertable via Alembic

**What:** The `market_data` table must be converted to a TimescaleDB hypertable after creation. This cannot happen via ORM model definitions — it requires a raw SQL call in the Alembic migration.

**Alembic gotcha:** When Alembic autogenerates migrations after a hypertable is created, it will detect the TimescaleDB-managed index and try to drop it. Solution: use `include_object` in `alembic/env.py` to filter out TimescaleDB's internal catalog tables, or manually review autogenerated migrations before applying.

```python
# Source: Timescale official docs [CITED: https://docs.timescale.com/quick-start/latest/python/]
# In alembic migration: 001_create_ohlcv_hypertable.py

def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            symbol      VARCHAR(20)   NOT NULL,
            market      VARCHAR(10)   NOT NULL,
            interval    VARCHAR(5)    NOT NULL,
            timestamp   TIMESTAMPTZ   NOT NULL,
            open        DOUBLE PRECISION NOT NULL,
            high        DOUBLE PRECISION NOT NULL,
            low         DOUBLE PRECISION NOT NULL,
            close       DOUBLE PRECISION NOT NULL,
            volume      DOUBLE PRECISION NOT NULL
        );
    """)
    # create_hypertable partitions by time; chunk_time_interval of 1 week
    # is appropriate for OHLCV data with mixed 1m-1D candles
    op.execute("""
        SELECT create_hypertable(
            'market_data',
            'timestamp',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        );
    """)
    # Composite index for the query pattern: WHERE symbol=X AND interval=Y AND timestamp BETWEEN a AND b
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_market_data_symbol_interval_ts
        ON market_data (symbol, interval, timestamp DESC);
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS market_data;")
```

**SQLite dev fallback:** For local development without Docker, the `market_data` table can be created as a plain SQLite table (no hypertable). The ORM model is identical; only the migration diverges. Use an environment variable `DATABASE_URL` to switch:
- Dev: `sqlite+aiosqlite:///./dev.db`
- Prod: `postgresql+asyncpg://user:pass@localhost/tradingbot`

### Pattern 6: APScheduler with FastAPI Lifespan

**What:** `AsyncIOScheduler` runs in the same event loop as FastAPI. It is started and stopped via FastAPI's lifespan context manager.

```python
# Source: APScheduler docs + FastAPI lifespan pattern [CITED: https://sentry.io/answers/schedule-tasks-with-fastapi/]
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register jobs before starting
    scheduler.add_job(
        ingest_stocks_incremental,
        trigger=IntervalTrigger(minutes=5),
        id="stock_incremental",
        replace_existing=True,
        misfire_grace_time=60,      # tolerate 60s late start
    )
    scheduler.add_job(
        ingest_crypto_incremental,
        trigger=IntervalTrigger(minutes=30),  # rate-limit-safe for CoinGecko
        id="crypto_incremental",
        replace_existing=True,
        misfire_grace_time=120,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
```

### Pattern 7: Idempotent Upsert

**What:** All OHLCV inserts use `INSERT ... ON CONFLICT DO NOTHING` to make ingestion jobs safe to re-run. If a scheduler job fires twice or a backfill overlaps with incremental data, no duplicates are created.

```python
# Source: TimescaleDB documentation / PostgreSQL ON CONFLICT pattern [ASSUMED based on standard SQL]
from sqlalchemy import text

async def upsert_candles(session, candles: list[OHLCVCandle]):
    for c in candles:
        await session.execute(
            text("""
                INSERT INTO market_data
                    (symbol, market, interval, timestamp, open, high, low, close, volume)
                VALUES
                    (:symbol, :market, :interval, :timestamp, :open, :high, :low, :close, :volume)
                ON CONFLICT (symbol, interval, timestamp) DO NOTHING
            """),
            c.__dict__,
        )
    await session.commit()
```

### Anti-Patterns to Avoid

- **Calling yfinance in a polling loop:** Use only for batch historical backfill with a sleep between batches; never poll faster than once per minute per symbol.
- **Fetching all CoinGecko coins on startup:** Burst requests will exhaust the rate limit within minutes. Stagger requests with `asyncio.sleep(2)` between coins.
- **Mixing provider-specific field names into analysis code:** All strategy code must only see `OHLCVCandle` schema. Never let `df["Adj Close"]` (yfinance column name) appear outside the provider module.
- **Building fine-grained crypto candles from CoinGecko:** CoinGecko cannot produce 1m/5m/15m candles on the free tier. Use CCXT for intraday crypto candles.
- **Skipping the caching layer:** Every provider response must go through the TTL cache before hitting the API. The minimum CoinGecko cache TTL is 60 seconds (Demo plan refresh rate).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting per-provider | Custom token bucket logic | APScheduler interval triggers + asyncio.sleep between requests | Correct burst limiting is non-trivial; scheduler intervals enforce it by design |
| OHLCV data normalization per source | Ad-hoc field mapping in each provider | Single `normalizer.py` that all providers pass through | Prevents provider-specific column names leaking into analysis code |
| TimescaleDB time partitioning | Manual `PARTITION BY RANGE` in PostgreSQL | `create_hypertable()` from TimescaleDB extension | Automatic chunk management, compression, and retention built in |
| Crypto exchange OHLCV | Direct Binance REST calls | `ccxt` library | CCXT normalizes 100+ exchanges to the same OHLCV format; Binance has rate limits and IP bans |
| WebSocket reconnection logic | Custom ping/heartbeat loop | `websockets` library with `websocket-client` | Both handle reconnection; manual reconnect code is always incomplete |
| Database migration versioning | Manual ALTER TABLE scripts | Alembic | Schema changes without Alembic become untrackable across environments |

---

## Common Pitfalls

### Pitfall 1: CoinGecko 10,000 Call Monthly Cap Exhaustion

**What goes wrong:** A scheduler polling 10 coins every 5 minutes makes 2,880 calls/day (86,400/month) — 8.6x the monthly cap. The account gets cut off partway through the month with no data.

**Why it happens:** The monthly cap is not visible per-call; it only appears in billing/usage dashboards. Developers discover it when data stops.

**How to avoid:** Calculate calls/month before writing the scheduler. Safe formula for Demo plan: `coins × (calls_per_day) × 30 ≤ 10,000`. With 5 coins and 1 call per hour per coin = 5 × 24 × 30 = 3,600 calls/month. Cache all responses for at least 60 seconds (the CoinGecko Demo plan refresh interval).

**Warning signs:** No call counter in logs; scheduler fires more frequently than 1 call per 3 minutes per coin.

### Pitfall 2: yfinance 1m Data Only Available for Last 7 Days

**What goes wrong:** A backfill job requests 6 months of 1-minute OHLCV for stock analysis. yfinance silently returns only 7 days. The DB appears full but is missing 99% of expected data.

**Why it happens:** yfinance enforces an undocumented cap: 1m interval → max 7 days history; 1h interval → max 60 days history. No error is raised.

**How to avoid:** Map intervals to their maximum available history in the provider config:
```python
YFINANCE_MAX_HISTORY = {
    "1m": "7d", "5m": "60d", "15m": "60d",
    "1h": "60d", "4h": "60d",
    "1d": "2y",  "1wk": "10y",
}
```
For backtesting that needs years of intraday data, daily OHLCV is the only practical option with free sources.

**Warning signs:** Backfill completes instantly; stored candle count is far below expected.

### Pitfall 3: Alembic Drops TimescaleDB's Hypertable Index

**What goes wrong:** After the initial migration creates the hypertable, running `alembic revision --autogenerate` produces a migration that drops the TimescaleDB-managed index. Applying it breaks the hypertable.

**Why it happens:** Alembic reflects the database and sees an index it didn't create, concluding it should be removed.

**How to avoid:** In `alembic/env.py`, add an `include_object` filter:
```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "index" and reflected and compare_to is None:
        return False  # skip TimescaleDB-managed indexes
    return True
```
Always review autogenerated migrations before applying.

**Warning signs:** Autogenerated migration contains a `DROP INDEX` with an index name starting with `_hyper_`.

### Pitfall 4: Finnhub WebSocket Disconnects Silently

**What goes wrong:** The Finnhub WebSocket connection drops after inactivity or network hiccup. The `websocket-client` library does not automatically reconnect. The scheduler continues running but no live prices are being received.

**Why it happens:** WebSocket connections are stateful; TCP timeouts or server-side disconnects close the connection without triggering Python exceptions in all cases.

**How to avoid:** Run the WebSocket in a separate thread or asyncio task with reconnect logic:
```python
import time

def run_finnhub_ws():
    while True:
        try:
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as e:
            log.error(f"Finnhub WS error: {e}")
        time.sleep(5)  # back-off before reconnect
```
Add a "last tick received" timestamp; alert (log warning) if no tick for > 2 minutes during market hours.

**Warning signs:** Live price column in DB shows timestamps frozen at a specific time.

### Pitfall 5: CoinGecko OHLCV Candle Size is Not Configurable

**What goes wrong:** A plan is written to store 1H crypto candles from CoinGecko. When implemented, `get_coin_ohlc_by_id` returns 4H candles for requests of 3-30 days. The timeframe column in the DB is wrong.

**Why it happens:** CoinGecko auto-determines candle granularity based on the `days` parameter; this is documented but easy to miss.

**Resolution path:** For 1H crypto candles, use CCXT (Binance public API, no key required for OHLCV). CoinGecko is best for daily-level crypto data and market cap/metadata. The data model should record the actual candle interval, not the requested interval.

**Warning signs:** All crypto candles stored as "1H" but timestamps are exactly 4 hours apart.

### Pitfall 6: No Exponential Backoff on 429 Errors

**What goes wrong:** yfinance or CoinGecko returns a 429 (rate limit). The provider retries immediately, gets another 429, and goes into a retry storm that further exhausts the rate limit.

**How to avoid:** All HTTP calls must use exponential backoff with jitter:
```python
import asyncio, random

async def fetch_with_backoff(fetch_fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await fetch_fn()
        except RateLimitError:
            wait = (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait)
    raise Exception("Max retries exceeded")
```

---

## Code Examples

### Canonical OHLCV Schema (SQLAlchemy Model)
```python
# Source: derived from TimescaleDB trading tutorials [CITED: https://docs.timescale.com/quick-start/latest/python/]
from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class MarketData(Base):
    __tablename__ = "market_data"

    # TimescaleDB requires timestamp as part of primary key
    symbol    = Column(String(20),  nullable=False, primary_key=True)
    market    = Column(String(10),  nullable=False)   # "stock" | "crypto"
    interval  = Column(String(5),   nullable=False, primary_key=True)  # "1m" | "1h" | "1d"
    timestamp = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    open      = Column(Float, nullable=False)
    high      = Column(Float, nullable=False)
    low       = Column(Float, nullable=False)
    close     = Column(Float, nullable=False)
    volume    = Column(Float, nullable=False)

    # Note: the composite index is created in the Alembic migration, not here,
    # because TimescaleDB's create_hypertable() manages index strategy.
```

### Query Pattern: Last N Candles for Symbol + Interval
```python
# Source: TimescaleDB SQL patterns [ASSUMED — standard SQL, TimescaleDB-optimized]
from sqlalchemy import select, and_

async def get_latest_candles(
    session, symbol: str, interval: str, limit: int = 200
) -> list[MarketData]:
    result = await session.execute(
        select(MarketData)
        .where(and_(
            MarketData.symbol == symbol,
            MarketData.interval == interval,
        ))
        .order_by(MarketData.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()
```

### yfinance Normalizer
```python
# Source: yfinance API shape documented at aroussi.com [CITED: https://aroussi.com/post/python-yahoo-finance]
import pandas as pd
from datetime import timezone

def normalize_yfinance(df: pd.DataFrame, symbol: str, interval: str) -> list[OHLCVCandle]:
    candles = []
    for ts, row in df.iterrows():
        # yfinance returns timezone-aware index after auto_adjust=True
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        candles.append(OHLCVCandle(
            symbol=symbol,
            market="stock",
            interval=interval,
            timestamp=ts,
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=float(row["Volume"]),
        ))
    return candles
```

### CoinGecko Rate-Limit-Safe Fetcher
```python
# Source: pycoingecko README + CoinGecko rate limit docs [CITED: https://docs.coingecko.com/docs/common-errors-rate-limit]
import asyncio
from pycoingecko import CoinGeckoAPI

COINGECKO_COINS = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple"]
COINGECKO_INTERVAL_SECONDS = 120  # 5 coins / 120s = 2.5 calls/min << 30 limit

async def ingest_crypto_batch(cg: CoinGeckoAPI, session):
    for coin_id in COINGECKO_COINS:
        try:
            raw = cg.get_coin_ohlc_by_id(id=coin_id, vs_currency="usd", days=30)
            candles = normalize_coingecko(raw, coin_id)
            await upsert_candles(session, candles)
        except Exception as e:
            log.error(f"CoinGecko fetch failed for {coin_id}: {e}")
        await asyncio.sleep(COINGECKO_INTERVAL_SECONDS / len(COINGECKO_COINS))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| yfinance 0.2.x | yfinance 1.x (1.2.0) | Late 2025 | New Ticker API structure; `ticker.history()` unchanged, but some internal endpoints changed |
| TimescaleDB 2.x default chunks | TimescaleDB 2.18 with better compression | 2024-2025 | Columnstore indexes available for better analytical query performance |
| APScheduler 3.9 | APScheduler 3.11.2 | 2025 | Bug fixes for async scheduler; `misfire_grace_time` behavior improved |
| pycoingecko 2.x (no API key) | pycoingecko 3.x (Demo key required for 30 req/min) | 2023-2024 | Public plan dropped to 5-15 req/min; Demo key (free) required for 30 req/min |

**Deprecated/outdated:**
- `pycoingecko` without a Demo API key: 5-15 req/min is insufficient for multi-coin scanning; always use the free Demo key.
- `yfinance.download()` as a real-time price feed: officially unsupported; use Finnhub WS.
- CoinGecko public endpoint `https://api.coingecko.com/api/v3` without `x-cg-demo-api-key` header: returns rate-limited responses.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Finnhub free tier allows 50 simultaneous WebSocket symbol subscriptions | Standard Stack / Finnhub Pattern | May need to reduce watchlist size or upgrade plan |
| A2 | yfinance 1.2.0 `ticker.history()` API is unchanged from 0.2.x pattern | Code Examples | Would require updating normalizer; low risk as API is stable |
| A3 | `ON CONFLICT DO NOTHING` is sufficient deduplication for OHLCV upserts | Code Examples / Don't Hand-Roll | Could miss updates to partially-formed candles; acceptable for MVP |
| A4 | TimescaleDB `create_hypertable` raw SQL in Alembic is the accepted pattern | Architecture Patterns | Alternative: sqlalchemy-timescaledb package (low adoption, not officially supported) |
| A5 | CCXT public Binance OHLCV endpoint works without API key for historical data | Common Pitfalls (CoinGecko limitation workaround) | If Binance requires auth, need fallback; CCXT is widely documented as key-free for public data |

---

## Open Questions

1. **Finnhub free tier symbol limit under sustained load**
   - What we know: Free tier advertises 60 req/min REST + WebSocket available
   - What's unclear: Whether 50-symbol WS subscriptions hold stable for 8+ hours without disconnect or silent failure
   - Recommendation: Phase 1 plan should include a Finnhub WS stability test (run for 2 hours, verify no silent drops) as an explicit task before declaring DATA-01 complete

2. **CoinGecko volume data for OHLCV**
   - What we know: `get_coin_ohlc_by_id` returns [ts, open, high, low, close] — no volume
   - What's unclear: Whether volume is required for Phase 1 (success criteria says "OHLCV") or if close-only candles are acceptable for crypto
   - Recommendation: Fetch volume separately from `get_coin_market_chart_by_id` and join, or mark crypto volume as NULL in Phase 1 and populate in a later enhancement

3. **SQLite dev environment for TimescaleDB-specific features**
   - What we know: TimescaleDB features (`create_hypertable`, time_bucket) are PostgreSQL-only
   - What's unclear: Whether the local dev workflow should require Docker for Postgres or if plain SQLite is acceptable for non-time-series queries
   - Recommendation: Use Docker Compose with `timescale/timescaledb:latest-pg16` for all environments including local dev. SQLite is acceptable only for unit tests with mocked DB sessions.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Backend runtime | Available (3.13.7) | 3.13.7 | — |
| Docker | TimescaleDB container | Available | 28.3.3 | Run plain PostgreSQL + extension manually |
| psql CLI | DB inspection / migration debug | Not found | — | Use Docker exec into container |
| TimescaleDB Docker image | DATABASE layer | Not pulled yet | timescale/timescaledb:latest-pg16 | Pull at setup |
| APScheduler | Scheduling | Not installed | 3.11.2 available on PyPI | — |
| yfinance | Stock data | Not installed | 1.2.0 available on PyPI | — |
| pycoingecko | Crypto data | Not installed | 3.2.0 available on PyPI | — |
| Finnhub API key | Stock WebSocket | Not configured | Requires free account at finnhub.io | Use yfinance polling as interim fallback |
| CoinGecko Demo API key | Crypto rate limit | Not configured | Requires free Demo account at coingecko.com | Public endpoint (5-15 req/min, insufficient) |

**Missing dependencies with no fallback:**
- Finnhub API key and CoinGecko Demo API key: must be obtained before implementing respective providers. Both are free.

**Missing dependencies with fallback:**
- psql CLI: Docker exec into container covers all inspection needs.
- TimescaleDB image: needs `docker pull timescale/timescaledb:latest-pg16` during Wave 0.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `backend/pyproject.toml` (none yet — see Wave 0) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | yfinance provider returns normalized OHLCVCandle list | unit | `pytest tests/test_providers.py::test_yfinance_returns_candles -x` | Wave 0 |
| DATA-01 | Finnhub WS message parsed into OHLCVCandle | unit | `pytest tests/test_providers.py::test_finnhub_message_parsing -x` | Wave 0 |
| DATA-02 | CoinGecko provider returns normalized OHLCVCandle list | unit | `pytest tests/test_providers.py::test_coingecko_returns_candles -x` | Wave 0 |
| DATA-03 | All 6 intervals stored and retrievable from DB | integration | `pytest tests/test_db.py::test_all_intervals_round_trip -x` | Wave 0 |
| DATA-04 | Swapping provider does not change downstream query | unit | `pytest tests/test_providers.py::test_provider_interface_contract -x` | Wave 0 |
| DATA-05 | OHLCV range query returns in < 1 second | integration | `pytest tests/test_db.py::test_query_performance -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_providers.py` — covers DATA-01, DATA-02, DATA-04
- [ ] `backend/tests/test_db.py` — covers DATA-03, DATA-05
- [ ] `backend/tests/conftest.py` — async session fixture, in-memory SQLite for unit tests
- [ ] `backend/pyproject.toml` — pytest config with `asyncio_mode = "auto"`
- [ ] Framework install: `uv add --dev pytest pytest-asyncio` — if none detected

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user login in Phase 1 |
| V3 Session Management | No | No sessions in Phase 1 |
| V4 Access Control | No | No multi-user access in Phase 1 |
| V5 Input Validation | Yes | pydantic validates all OHLCVCandle fields before DB insert |
| V6 Cryptography | No | No encryption needed for market data |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key in source code | Information Disclosure | Use python-dotenv; `.env` in `.gitignore` from day one |
| SQL injection via symbol name | Tampering | SQLAlchemy parameterized queries; never string-format SQL |
| Resource exhaustion via scheduler misconfiguration | Denial of Service | APScheduler `max_instances=1` per job; prevents concurrent duplicate runs |

**Critical:** `.env` file must be in `.gitignore` before the first commit. Finnhub and CoinGecko keys committed to git result in account suspension.

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: PyPI registry] — yfinance 1.2.0, pycoingecko 3.2.0, APScheduler 3.11.2, SQLAlchemy 2.0.49, Alembic 1.18.4, psycopg2-binary 2.9.11, asyncpg 0.31.0 (verified via `pip3 index versions` on 2026-04-06)
- [CITED: https://docs.coingecko.com/reference/coins-id-ohlc] — CoinGecko OHLCV endpoint; auto-granularity by days parameter
- [CITED: https://docs.coingecko.com/docs/common-errors-rate-limit] — Demo plan: 30 req/min, 10k calls/month, 60-second cache TTL
- [CITED: https://finnhub.io/docs/api/websocket-trades] — Finnhub WS protocol; subscribe/unsubscribe message format
- [CITED: https://docs.timescale.com/quick-start/latest/python/] — TimescaleDB Python quick start; `create_hypertable()` call pattern
- [CITED: https://pypi.org/project/yfinance/] — yfinance intervals, historical limits (7d for 1m, 60d for intraday)

### Secondary (MEDIUM confidence)
- [CITED: https://aroussi.com/post/python-yahoo-finance] — yfinance author's documentation; `ticker.history()` usage
- [CITED: https://sentry.io/answers/schedule-tasks-with-fastapi/] — APScheduler + FastAPI lifespan integration pattern
- [CITED: https://oneuptime.com/blog/post/2026-02-08-how-to-run-timescaledb-in-docker-with-hypertables/view] — TimescaleDB Docker + hypertable setup, 2026
- [CITED: https://tradermade.com/tutorials/6-steps-fx-stock-ticks-ohlc-timescaledb] — TimescaleDB OHLCV pipeline pattern

### Tertiary (LOW confidence)
- TimescaleDB 3.4x faster than PostgreSQL for OHLCV aggregations — cited from search result summary; original benchmark source not directly verified [ASSUMED direction is correct based on multiple sources agreeing]
- Finnhub 50 symbol WS limit on free tier — cited from search result; not verified against current Finnhub pricing page

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via PyPI registry on research date
- Architecture: MEDIUM-HIGH — patterns derived from official docs and established open-source projects (Freqtrade, CCXT)
- API behaviors: MEDIUM — CoinGecko rate limits and candle granularity verified via official docs; Finnhub WS behavior under load is LOW (unvalidated)
- Pitfalls: HIGH — multiple independent sources corroborate; most are documented in official API documentation

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (CoinGecko API plan terms change; yfinance breaks occasionally with Yahoo page changes)
