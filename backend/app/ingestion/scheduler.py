"""
APScheduler job definitions and FastAPI lifespan hook.

Design:
- AsyncIOScheduler runs in the same event loop as FastAPI.
- Five recurring jobs:
  1. stock_incremental_job — every 5 min: yfinance OHLCV for STOCK_WATCHLIST
  2. crypto_coingecko_job — every 30 min: CoinGecko 4H candles for top-5 coins
  3. crypto_ccxt_job — every 15 min: CCXT Binance OHLCV for CCXT_CRYPTO_SYMBOLS
  4. analysis_scan_job — every 5 min: rule-based signal scan
  5. equity_snapshot_job — every 5 min: paper trading equity snapshots (max_instances=1)

Scheduler choice (from STATE.md decision):
  APScheduler (not Celery+Redis) is used by deliberate Phase 1 decision.
  AsyncIOScheduler integrates cleanly with FastAPI lifespan — no external queue
  infrastructure required for single-process MVP. Celery+Redis is the upgrade
  path for Phase 5+ when multi-worker scale is needed.

Error handling:
  All jobs wrap fetch+upsert in try/except — a failing job never crashes the
  scheduler. Errors are logged at ERROR level.
"""
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

from app.analysis.scanner import analysis_scan_job
from app.core.database import async_session_factory
from app.paper_trading.snapshot import equity_snapshot_job
from app.core.watchlists import CCXT_CRYPTO_SYMBOLS, CCXT_INTERVALS, STOCK_INTERVALS, STOCK_WATCHLIST
from app.ingestion.providers.ccxt_provider import CCXTProvider
from app.ingestion.providers.coingecko_provider import CoinGeckoProvider, ingest_all_coins
from app.ingestion.providers.yfinance_provider import YfinanceProvider
from app.ingestion.upsert import upsert_candles

__all__ = [
    "scheduler",
    "lifespan",
    "STOCK_WATCHLIST",
    "STOCK_INTERVALS",
    "CCXT_CRYPTO_SYMBOLS",
    "CCXT_INTERVALS",
    "stock_incremental_job",
    "crypto_coingecko_job",
    "crypto_ccxt_job",
    "analysis_scan_job",
    "equity_snapshot_job",
]

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Watchlist and interval constants
# ---------------------------------------------------------------------------
# Defined in app.core.watchlists to avoid circular import with scanner.py.
# Re-exported here for backward compatibility (existing callers import from scheduler).
# STOCK_WATCHLIST, STOCK_INTERVALS, CCXT_CRYPTO_SYMBOLS, CCXT_INTERVALS

# ---------------------------------------------------------------------------
# Scheduler jobs
# ---------------------------------------------------------------------------


async def stock_incremental_job() -> None:
    """
    Fetch and upsert the latest OHLCV candles for all STOCK_WATCHLIST symbols.

    Runs every 5 minutes. Fetches all STOCK_INTERVALS for each symbol.
    Individual symbol/interval failures are caught and logged — other pairs continue.
    """
    provider = YfinanceProvider()
    async with async_session_factory() as session:
        for symbol in STOCK_WATCHLIST:
            for interval in STOCK_INTERVALS:
                try:
                    candles = await provider.fetch_latest(symbol, interval)
                    await upsert_candles(session, candles)
                    log.info(
                        "Stock ingest: %s/%s → %d candles", symbol, interval, len(candles)
                    )
                except Exception as exc:
                    log.error("Stock ingest failed %s/%s: %s", symbol, interval, exc)


async def crypto_coingecko_job() -> None:
    """
    Fetch and upsert 4H OHLCV candles for all COINGECKO_COINS.

    Runs every 30 minutes. Delegates to ingest_all_coins() which enforces inter-coin
    delay to respect the CoinGecko free-tier rate limit (30 req/min).
    """
    provider = CoinGeckoProvider()
    try:
        async with async_session_factory() as session:
            await ingest_all_coins(session, provider)
            log.info("CoinGecko ingest: completed all coins")
    except Exception as exc:
        log.error("CoinGecko ingest failed: %s", exc)


async def crypto_ccxt_job() -> None:
    """
    Fetch and upsert OHLCV candles for all CCXT_CRYPTO_SYMBOLS × CCXT_INTERVALS.

    Runs every 15 minutes. CCXT auto-throttles via enableRateLimit=True.
    Individual symbol/interval failures are caught and logged — others continue.
    """
    provider = CCXTProvider()
    async with async_session_factory() as session:
        for symbol in CCXT_CRYPTO_SYMBOLS:
            for interval in CCXT_INTERVALS:
                try:
                    candles = await provider.fetch_latest(symbol, interval)
                    await upsert_candles(session, candles)
                    log.info(
                        "CCXT ingest: %s/%s → %d candles", symbol, interval, len(candles)
                    )
                except Exception as exc:
                    log.error("CCXT ingest failed %s/%s: %s", symbol, interval, exc)


# ---------------------------------------------------------------------------
# APScheduler instance and FastAPI lifespan
# ---------------------------------------------------------------------------

#: Module-level scheduler — one instance shared by the entire process
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager: start and stop the APScheduler.

    Five jobs are registered:
    - stock_incremental_job: every 5 minutes
    - crypto_coingecko_job: every 30 minutes
    - crypto_ccxt_job: every 15 minutes
    - analysis_scan_job: every 5 minutes (runs after data ingestion)
    - equity_snapshot_job: every 5 minutes (max_instances=1, paper equity snapshots)

    misfire_grace_time prevents job pile-up if a run is delayed (e.g., during startup).
    """
    scheduler.add_job(
        stock_incremental_job,
        IntervalTrigger(minutes=5),
        id="stock_incremental",
        replace_existing=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        crypto_coingecko_job,
        IntervalTrigger(minutes=30),
        id="crypto_coingecko",
        replace_existing=True,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        crypto_ccxt_job,
        IntervalTrigger(minutes=15),
        id="crypto_ccxt",
        replace_existing=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        analysis_scan_job,
        IntervalTrigger(minutes=5),
        id="analysis_scan",
        replace_existing=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        equity_snapshot_job,
        IntervalTrigger(minutes=5),
        id="paper_equity_snapshot",
        replace_existing=True,
        misfire_grace_time=60,
        max_instances=1,  # prevents duplicate snapshots if job runs long
    )

    scheduler.start()
    log.info(
        "Scheduler started — 5 jobs registered "
        "(stock/5min, CoinGecko/30min, CCXT/15min, analysis/5min, paper_equity/5min)"
    )

    yield  # FastAPI serves requests here

    scheduler.shutdown(wait=False)
    log.info("Scheduler stopped")
