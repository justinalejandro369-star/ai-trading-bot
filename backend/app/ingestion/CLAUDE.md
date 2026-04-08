# ingestion/ — Data Provider Guide

Handles all external data fetching, normalization, caching, and DB upsert.

## OHLCVProvider ABC

All providers implement `OHLCVProvider` from `base_provider.py`. The scheduler and pipeline call only this interface — never provider-specific code.

```python
from app.ingestion.base_provider import OHLCVCandle, OHLCVProvider

class MyProvider(OHLCVProvider):
    async def fetch_historical(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> list[OHLCVCandle]:
        # Backfill: return candles in ascending timestamp order
        ...

    async def fetch_latest(
        self, symbol: str, interval: str
    ) -> list[OHLCVCandle]:
        # Incremental: return most recent N candles
        ...
```

`OHLCVCandle` is a frozen dataclass — all fields required:
```python
OHLCVCandle(
    symbol="AAPL",
    market="stock",     # "stock" | "crypto" | "forex"
    interval="1D",      # "1m" | "5m" | "15m" | "1H" | "4H" | "1D"
    timestamp=datetime(..., tzinfo=timezone.utc),
    open=150.0, high=155.0, low=149.0, close=153.0, volume=1_000_000.0,
)
```

## Available Providers

| Provider | File | Markets | Notes |
|----------|------|---------|-------|
| `YfinanceProvider` | `providers/yfinance_provider.py` | Stocks (OHLCV) | Unofficial scraper, rate-limited; used for historical backfill + incremental on 5-min schedule |
| `FinnhubProvider` | `providers/finnhub_provider.py` | US stocks (live ticks) | WebSocket connection; live ticks broadcast to `/ws/live` clients |
| `CoinGeckoProvider` | `providers/coingecko_provider.py` | Crypto (top-5 coins, 4H OHLCV) | Free Demo plan: 10,000 calls/month; inter-coin delay enforced |
| `CCXTProvider` | `providers/ccxt_provider.py` | Crypto OHLCV (Binance) | CCXT `enableRateLimit=True` auto-throttles; covers all CCXT_CRYPTO_SYMBOLS |
| `ForexProvider` | `providers/forex_provider.py` | Forex daily (major pairs) | Alpha Vantage; returns `[]` with warning log if `ALPHA_VANTAGE_API_KEY` is empty |

## TTL Cache (`cache.py`)

```python
from app.ingestion.cache import ttl_cache

@ttl_cache(ttl_seconds=300)
async def expensive_api_call(symbol: str) -> list:
    ...
```

Caches async function results by arguments. Prevents hammering rate-limited APIs when the scheduler fires multiple jobs in quick succession.

## Normalizer Functions (`normalizer.py`)

Convert raw API responses into `OHLCVCandle` lists:

```python
from app.ingestion.normalizer import normalize_yfinance, normalize_coingecko

# yfinance returns a DataFrame with DatetimeIndex
candles = normalize_yfinance(df, symbol="AAPL", interval="1D", market="stock")

# CoinGecko returns list of [timestamp_ms, open, high, low, close]
candles = normalize_coingecko(raw_list, symbol="bitcoin", interval="4H")
```

Both functions output `list[OHLCVCandle]` in ascending timestamp order.

## Upsert (`upsert.py`)

```python
from app.ingestion.upsert import upsert_candles

async with async_session_factory() as session:
    count = await upsert_candles(session, candles)
```

Uses `ON CONFLICT (symbol, interval, timestamp) DO NOTHING` — idempotent. Inserting the same candle twice is safe. The composite key on `market_data` is `(symbol, interval, timestamp)`.

**Do NOT use** `ON CONFLICT DO UPDATE` for market_data — candles are immutable historical facts. Only the `signals` table uses DO UPDATE.

## Scheduler (`scheduler.py`)

7 APScheduler jobs registered at FastAPI startup via `lifespan`:

| Job ID | Interval | Function |
|--------|---------|---------|
| `stock_incremental` | 5 min | `stock_incremental_job()` — yfinance for STOCK_WATCHLIST |
| `crypto_coingecko` | 30 min | `crypto_coingecko_job()` — CoinGecko top-5 coins |
| `crypto_ccxt` | 15 min | `crypto_ccxt_job()` — CCXT Binance OHLCV |
| `analysis_scan` | 5 min | `analysis_scan_job()` — signal scan (from analysis/) |
| `paper_equity_snapshot` | 5 min | `equity_snapshot_job()` — mark paper portfolio to market |
| `alert_check` | 5 min | `alert_check_job()` — evaluate alert rules |
| `forex_daily` | 24h | `forex_daily_job()` — Alpha Vantage daily FX |

All jobs wrap their work in `try/except` — a failing job never crashes the scheduler.

## Watchlists

**Defined in `app/core/watchlists.py`** (not here) to avoid circular imports:
- `STOCK_WATCHLIST` — list of stock tickers
- `CCXT_CRYPTO_SYMBOLS` — list of crypto pairs (e.g. "BTC/USDT")
- `STOCK_INTERVALS`, `CCXT_INTERVALS` — intervals to fetch per asset

Import: `from app.core.watchlists import STOCK_WATCHLIST, CCXT_CRYPTO_SYMBOLS`
