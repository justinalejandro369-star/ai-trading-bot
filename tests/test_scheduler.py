"""
Tests for APScheduler job registration and interval configuration.

Phase 01 Plan 03: Scheduler wiring.
"""
from unittest.mock import AsyncMock, patch

import pytest


def test_scheduler_has_three_jobs():
    """Scheduler should register exactly 3 jobs: stock, coingecko, ccxt."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from app.ingestion.scheduler import (
        crypto_ccxt_job,
        crypto_coingecko_job,
        stock_incremental_job,
    )

    sched = AsyncIOScheduler()
    sched.add_job(
        stock_incremental_job,
        IntervalTrigger(minutes=5),
        id="stock_incremental",
        replace_existing=True,
        misfire_grace_time=60,
    )
    sched.add_job(
        crypto_coingecko_job,
        IntervalTrigger(minutes=30),
        id="crypto_coingecko",
        replace_existing=True,
        misfire_grace_time=120,
    )
    sched.add_job(
        crypto_ccxt_job,
        IntervalTrigger(minutes=15),
        id="crypto_ccxt",
        replace_existing=True,
        misfire_grace_time=60,
    )
    assert len(sched.get_jobs()) == 3


def test_stock_job_interval_is_5_minutes():
    """stock_incremental job must have a 5-minute interval trigger."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from app.ingestion.scheduler import stock_incremental_job

    sched = AsyncIOScheduler()
    sched.add_job(
        stock_incremental_job,
        IntervalTrigger(minutes=5),
        id="stock_incremental",
        replace_existing=True,
        misfire_grace_time=60,
    )
    job = sched.get_job("stock_incremental")
    assert job is not None
    # IntervalTrigger stores the interval as a timedelta
    trigger = job.trigger
    total_seconds = trigger.interval.total_seconds()
    assert total_seconds == 300  # 5 minutes = 300 seconds


def test_crypto_coingecko_job_interval_is_30_minutes():
    """crypto_coingecko job must have a 30-minute interval trigger."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from app.ingestion.scheduler import crypto_coingecko_job

    sched = AsyncIOScheduler()
    sched.add_job(
        crypto_coingecko_job,
        IntervalTrigger(minutes=30),
        id="crypto_coingecko",
        replace_existing=True,
        misfire_grace_time=120,
    )
    job = sched.get_job("crypto_coingecko")
    assert job is not None
    trigger = job.trigger
    total_seconds = trigger.interval.total_seconds()
    assert total_seconds == 1800  # 30 minutes = 1800 seconds


@pytest.mark.asyncio
async def test_stock_incremental_job_mocked():
    """stock_incremental_job calls upsert_candles len(STOCK_WATCHLIST) * len(STOCK_INTERVALS) times."""
    from datetime import datetime, timezone
    from app.ingestion.base_provider import OHLCVCandle
    from app.ingestion.scheduler import STOCK_WATCHLIST, STOCK_INTERVALS

    mock_candle = OHLCVCandle(
        symbol="AAPL",
        market="stock",
        interval="1d",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1_000_000.0,
    )
    mock_candles = [mock_candle] * 5

    expected_calls = len(STOCK_WATCHLIST) * len(STOCK_INTERVALS)

    with (
        patch(
            "app.ingestion.scheduler.YfinanceProvider.fetch_latest",
            new=AsyncMock(return_value=mock_candles),
        ),
        patch(
            "app.ingestion.scheduler.upsert_candles",
            new=AsyncMock(return_value=5),
        ) as mock_upsert,
        patch("app.ingestion.scheduler.async_session_factory") as mock_factory,
    ):
        # Set up async context manager for the session factory
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        from app.ingestion.scheduler import stock_incremental_job
        await stock_incremental_job()

    assert mock_upsert.call_count == expected_calls, (
        f"Expected {expected_calls} upsert calls "
        f"({len(STOCK_WATCHLIST)} symbols × {len(STOCK_INTERVALS)} intervals), "
        f"got {mock_upsert.call_count}"
    )
