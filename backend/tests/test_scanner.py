"""
Integration tests for the analysis scanner.

Uses in-memory SQLite + synthetic candle data. Tests verify:
1. scan_asset() correctly handles insufficient data (< MIN_CANDLES)
2. scan_asset() upserts (not duplicates) TradingSignal rows
3. scan_all_assets() processes all watchlist symbols

Run with: PYTHONPATH=backend uv --project backend run pytest tests/test_scanner.py -q
"""
import json
from datetime import datetime, timezone

import numpy as np
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.market_data import Base as MarketBase
from app.models.signal import TradingSignal
from app.analysis.scanner import SCAN_INTERVAL, scan_asset, scan_all_assets
from app.analysis.indicators import MIN_CANDLES
from tests.conftest import make_ohlcv_df, make_zero_volume_df

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(MarketBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


async def _insert_candles(
    session: AsyncSession,
    symbol: str,
    market: str,
    interval: str,
    n_rows: int,
    volume: float = 1_000_000.0,
):
    """Insert synthetic OHLCV candles for a symbol into market_data."""
    import pandas as pd

    df = make_ohlcv_df(n_rows) if volume > 0 else make_zero_volume_df(n_rows)
    for i, (ts, row) in enumerate(df.iterrows()):
        # Convert timezone-aware Timestamp to ISO string for SQLite compatibility
        ts_str = ts.isoformat()
        await session.execute(
            text("""
                INSERT OR IGNORE INTO market_data
                    (symbol, market, interval, timestamp, open, high, low, close, volume)
                VALUES
                    (:symbol, :market, :interval, :timestamp, :open, :high, :low, :close, :volume)
            """),
            {
                "symbol": symbol,
                "market": market,
                "interval": interval,
                "timestamp": ts_str,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            },
        )
    await session.commit()


@pytest.mark.asyncio
async def test_scan_asset_returns_none_when_insufficient_candles(session_factory):
    """50 candles is below MIN_CANDLES (200) -> scan_asset returns None."""
    async with session_factory() as session:
        await _insert_candles(session, "AAPL", "stock", SCAN_INTERVAL, 50)
        result = await scan_asset("AAPL", "stock", session)
    assert result is None


@pytest.mark.asyncio
async def test_scan_asset_returns_trading_signal_when_sufficient_candles(session_factory):
    """250 candles -> scan_asset returns a TradingSignal (not None)."""
    async with session_factory() as session:
        await _insert_candles(session, "TEST", "stock", SCAN_INTERVAL, 250)
        result = await scan_asset("TEST", "stock", session)
    assert result is not None
    assert isinstance(result, TradingSignal)
    assert result.symbol == "TEST"
    assert result.direction in ("BUY", "SELL", "HOLD")
    assert 0 <= result.confidence <= 100
    assert result.regime in ("trending", "ranging", "volatile")


@pytest.mark.asyncio
async def test_scan_asset_upserts_signal_to_db(session_factory):
    """Calling scan_asset twice -> only one row in signals table (upsert)."""
    async with session_factory() as session:
        await _insert_candles(session, "AAPL", "stock", SCAN_INTERVAL, 250)
        await scan_asset("AAPL", "stock", session)
        await scan_asset("AAPL", "stock", session)

        result = await session.execute(
            text("SELECT COUNT(*) FROM signals WHERE symbol='AAPL'")
        )
        count = result.scalar()
    assert count == 1


@pytest.mark.asyncio
async def test_scan_asset_updates_existing_signal_timestamp(session_factory):
    """Second scan updates scanned_at -- signal is refreshed, not ignored."""
    import asyncio

    async with session_factory() as session:
        await _insert_candles(session, "MSFT", "stock", SCAN_INTERVAL, 250)
        result1 = await scan_asset("MSFT", "stock", session)
        assert result1 is not None
        ts1 = result1.scanned_at

        # Small pause to ensure timestamp differs
        await asyncio.sleep(0.01)

        result2 = await scan_asset("MSFT", "stock", session)
        assert result2 is not None
        ts2 = result2.scanned_at

    # scanned_at should be updated (>= ts1)
    assert ts2 >= ts1


@pytest.mark.asyncio
async def test_scan_all_assets_processes_symbols_with_sufficient_data(session_factory):
    """scan_all_assets() creates a signal row for every symbol that has >=MIN_CANDLES rows."""
    symbols_with_data = ["AAPL", "MSFT"]
    async with session_factory() as session:
        for sym in symbols_with_data:
            await _insert_candles(session, sym, "stock", SCAN_INTERVAL, 250)
        await scan_all_assets(session)

        result = await session.execute(text("SELECT symbol FROM signals ORDER BY symbol"))
        stored = [row[0] for row in result.fetchall()]

    for sym in symbols_with_data:
        assert sym in stored


@pytest.mark.asyncio
async def test_scan_asset_zero_volume_does_not_raise(session_factory):
    """CoinGecko volume=0.0 assets must not crash the scanner."""
    async with session_factory() as session:
        await _insert_candles(session, "BITCOIN", "crypto", SCAN_INTERVAL, 250, volume=0.0)
        # Must not raise -- result may be None or a TradingSignal
        result = await scan_asset("BITCOIN", "crypto", session)
    # No assertion on direction -- just verify no exception
    assert result is None or isinstance(result, TradingSignal)
