---
phase: 01-data-foundation
plan: 02
subsystem: ingestion
tags: [python, yfinance, finnhub, coingecko, ccxt, websocket, ttl-cache, rate-limiting, tdd]

# Dependency graph
requires:
  - OHLCVCandle frozen dataclass (from 01-01)
  - OHLCVProvider ABC (from 01-01)
  - normalize_yfinance() (from 01-01)
  - normalize_coingecko() (from 01-01)
  - Settings class with FINNHUB_API_KEY, COINGECKO_API_KEY (from 01-01)
provides:
  - TTLCache class with get/set/invalidate and per-key TTL (backend/app/ingestion/cache.py)
  - YfinanceProvider(OHLCVProvider) — historical batch + incremental fetch with 60s TTL and exponential backoff
  - FinnhubProvider — WebSocket tick receiver with reconnect loop (ping_interval=20), last_prices buffer, max 50 symbol validation
  - CoinGeckoProvider(OHLCVProvider) — rate-limit-safe CoinGecko OHLCV with 120s TTL and inter-coin asyncio.sleep(2)
  - CCXTProvider(OHLCVProvider) — Binance public OHLCV with enableRateLimit=True and CCXT_INTERVAL_MAP
  - ingest_all_coins() coroutine for 5-coin CoinGecko batch ingestion
  - COINGECKO_COINS list of 5 default coins
affects: [01-03, 02-signal-engine, 03-backtesting, 04-paper-trading, 05-dashboard, 06-alerts, 07-intelligence]

# Tech tracking
tech-stack:
  added:
    - websocket-client==1.9.0 (added to pyproject.toml; not in original scaffold)
  patterns:
    - TTL cache: in-memory dict-based cache with monotonic clock expiry (no background thread needed for async single-process MVP)
    - Exponential backoff with jitter: 2^attempt + random(0,1) seconds, max 3 retries, on 429/rate-limit errors
    - Lazy cache eviction: expired entries deleted on get() access, no background cleanup needed
    - WebSocket reconnect loop: while True + try/run_forever(ping_interval=20)/except + sleep(5) daemon thread
    - CCXT_INTERVAL_MAP: translate app convention (1H, 4H, 1D) to CCXT/Binance convention (1h, 4h, 1d)
    - Inter-coin delay: asyncio.sleep(2) between CoinGecko calls keeps rate under 2.5 req/min (budget: 7,200/month vs 10,000 cap)

key-files:
  created:
    - backend/app/ingestion/cache.py
    - backend/app/ingestion/providers/__init__.py
    - backend/app/ingestion/providers/yfinance_provider.py
    - backend/app/ingestion/providers/finnhub_provider.py
    - backend/app/ingestion/providers/coingecko_provider.py
    - backend/app/ingestion/providers/ccxt_provider.py
    - tests/test_stock_ingestion.py
    - tests/test_crypto_ingestion.py
  modified:
    - backend/pyproject.toml (added websocket-client dependency)
    - backend/uv.lock (updated lock file)

key-decisions:
  - "websocket-client (not websockets) chosen for FinnhubProvider — WebSocketApp class provides the on_open/on_message/on_error/on_close callback API required by the plan; pure websockets library lacks this convenience pattern"
  - "CoinGeckoProvider.fetch_historical ignores interval parameter — CoinGecko auto-selects candle granularity from the 'days' parameter; apps that pass interval=1H still get 4H candles for a 30-day window (documented in method docstring)"
  - "ingest_all_coins skips final sleep — asyncio.sleep(2) is only inserted between coins (not after the last), preventing unnecessary delay at job completion"
  - "CCXTProvider uses synchronous exchange.fetch_ohlcv — CCXT sync mode is called from an async method; acceptable for MVP since calls are infrequent; production upgrade would use ccxt.async_support"

requirements:
  - DATA-01
  - DATA-02

# Metrics
duration: 10min
completed: 2026-04-08
---

# Phase 1 Plan 2: Data Provider Implementations Summary

**Four concrete OHLCV data providers implemented with TTL caching, exponential backoff, WebSocket reconnect, and rate-limit-safe crypto ingestion; 15 tests all GREEN**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-08T05:14:06Z
- **Completed:** 2026-04-08T05:24:00Z
- **Tasks:** 2
- **Files modified:** 8 created, 2 modified

## Accomplishments

- TTLCache implemented with lazy expiry: monotonic clock, per-key TTL, no background thread needed for async single-process use
- YfinanceProvider wraps yfinance with a 60s TTL cache, YFINANCE_MAX_HISTORY interval caps, and exponential backoff (2^attempt + jitter) on 429 responses
- FinnhubProvider implements WebSocket reconnect loop in a daemon thread: ping_interval=20, ping_timeout=10, 5s reconnect sleep; last_prices dict updated on every trade tick; max 50 symbol subscriptions enforced
- CoinGeckoProvider uses 120s TTL cache (7,200 calls/month budget vs 10,000 cap), exponential backoff on rate limit, and asyncio.sleep(2) inter-coin delay for batch ingestion
- CCXTProvider uses Binance public OHLCV via ccxt.binance(enableRateLimit=True); CCXT_INTERVAL_MAP translates app convention (1H, 4H, 1D) to CCXT convention (1h, 4h, 1d); all timestamps are UTC-aware
- ingest_all_coins() coroutine iterates 5 default CoinGecko coins with inter-coin delay and ON CONFLICT DO NOTHING upsert
- Full TDD cycle: RED tests written first (import failures), then GREEN after implementation; 9 + 6 = 15 total tests all GREEN
- Full test suite: 24 tests across all 4 test files pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: TTL cache, yfinance, finnhub, coingecko, and ccxt providers** - `3677729` (feat)
2. **Task 2: Crypto ingestion tests for CoinGecko and CCXT** - `1b81c03` (test)

## Files Created/Modified

- `backend/app/ingestion/cache.py` - TTLCache: get/set/invalidate with monotonic TTL expiry
- `backend/app/ingestion/providers/__init__.py` - Package re-exports for all 4 providers
- `backend/app/ingestion/providers/yfinance_provider.py` - YfinanceProvider: batch historical, 60s TTL, backoff
- `backend/app/ingestion/providers/finnhub_provider.py` - FinnhubProvider: WebSocket reconnect, last_prices dict
- `backend/app/ingestion/providers/coingecko_provider.py` - CoinGeckoProvider: 120s TTL, inter-coin delay, batch ingest
- `backend/app/ingestion/providers/ccxt_provider.py` - CCXTProvider: Binance public, interval mapping, UTC timestamps
- `tests/test_stock_ingestion.py` - 9 tests: TTLCache (4), YfinanceProvider (2), FinnhubProvider (3)
- `tests/test_crypto_ingestion.py` - 6 tests: CoinGeckoProvider (3), CCXTProvider (2), ingest_all_coins (1)
- `backend/pyproject.toml` - Added websocket-client==1.9.0 dependency
- `backend/uv.lock` - Updated lock file with websocket-client

## Decisions Made

- websocket-client (not websockets) chosen for FinnhubProvider — the WebSocketApp callback API (on_open, on_message, on_error, on_close) is exactly what the plan specifies; the pure websockets library would require a different reconnect pattern
- CoinGeckoProvider.fetch_historical ignores the interval parameter — CoinGecko auto-selects granularity from 'days'; this is documented prominently in the method docstring so callers understand the limitation
- ingest_all_coins skips sleep after the last coin — inter-coin delay is only needed between calls, not after the batch completes; prevents unnecessary latency at job completion
- CCXTProvider sync fetch_ohlcv used from async context — acceptable for MVP since CoinGecko calls are infrequent; production path is ccxt.async_support module

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added websocket-client dependency to pyproject.toml**
- **Found during:** Task 1 setup
- **Issue:** websocket-client package not in pyproject.toml; `import websocket` would fail at runtime, blocking FinnhubProvider implementation
- **Fix:** `uv add websocket-client` added websocket-client==1.9.0 to pyproject.toml and uv.lock
- **Files modified:** backend/pyproject.toml, backend/uv.lock
- **Commit:** 3677729

**2. [Rule 2 - Missing Critical] Added test_ttl_cache_invalidate_removes_entry**
- **Found during:** Task 1 TDD RED phase
- **Issue:** Plan specified 7 tests but didn't include an explicit test for TTLCache.invalidate(); invalidate() is part of the public API specified in must_haves and should be tested
- **Fix:** Added test_ttl_cache_invalidate_removes_entry to test_stock_ingestion.py (9 total tests instead of 7+1 implied)
- **Files modified:** tests/test_stock_ingestion.py

---

**Total deviations:** 2 auto-fixed (1 blocking dependency, 1 missing test coverage)
**Impact on plan:** websocket-client is a hard requirement for FinnhubProvider; no scope creep. Extra invalidate() test improves coverage of a documented public API method.

## Known Stubs

- `FinnhubProvider.connect_websocket()` starts a daemon WebSocket thread but there is no integration test confirming real Finnhub connectivity. The thread runs indefinitely; testing is mocked. This is intentional — real WebSocket testing requires a live API key, which is excluded from the test suite by design.
- `CCXTProvider.fetch_historical` and `fetch_latest` call CCXT synchronously from async methods. For MVP single-user scale this is acceptable. A production upgrade would use `ccxt.async_support.binance` and `await exchange.fetch_ohlcv(...)`.

## User Setup Required

- Set `FINNHUB_API_KEY=your_key_here` in `.env` before calling `FinnhubProvider.connect_websocket()`
- Set `COINGECKO_API_KEY=your_key_here` in `.env` for authenticated CoinGecko requests (Demo plan key)
- Neither key is needed to run the unit test suite (all API calls are mocked)

## Next Phase Readiness

- All 4 providers ready for Plan 03 (APScheduler jobs, upsert layer, GET /api/market-data endpoint)
- YfinanceProvider and CoinGeckoProvider implement fetch_latest — suitable for periodic scheduler jobs
- FinnhubProvider.connect_websocket() starts background thread — integrate with FastAPI lifespan in Plan 03
- CCXTProvider ready for intraday crypto fetching in scheduler jobs

---
*Phase: 01-data-foundation*
*Completed: 2026-04-08*
