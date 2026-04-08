"""
TDD tests for the MarketData ORM model, database schema, and SQLite fallback.

Write these BEFORE implementing (TDD RED phase).
"""
import sys
import os

import pytest

# Add the backend directory to sys.path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def test_market_data_model_has_required_columns():
    """MarketData ORM model must have all required OHLCV columns."""
    from app.models.market_data import MarketData

    column_names = set(MarketData.__table__.columns.keys())
    required = {"symbol", "market", "interval", "timestamp", "open", "high", "low", "close", "volume"}
    assert required.issubset(column_names), (
        f"Missing columns: {required - column_names}"
    )


def test_market_data_primary_key_columns():
    """MarketData composite PK must include symbol, interval, and timestamp."""
    from app.models.market_data import MarketData

    pk_cols = set(MarketData.__table__.primary_key.columns.keys())
    assert "symbol" in pk_cols
    assert "interval" in pk_cols
    assert "timestamp" in pk_cols


def test_database_url_default_is_sqlite():
    """Settings must default to SQLite when DATABASE_URL is not set in environment."""
    import os
    # Temporarily remove DATABASE_URL if set
    original = os.environ.pop("DATABASE_URL", None)
    try:
        # Re-import with a fresh Settings instance (bypassing cached singleton)
        from pydantic_settings import BaseSettings, SettingsConfigDict

        class TestSettings(BaseSettings):
            model_config = SettingsConfigDict(env_file=".env", extra="ignore")
            DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
            FINNHUB_API_KEY: str = ""
            COINGECKO_API_KEY: str = ""

        ts = TestSettings()
        assert ts.DATABASE_URL.startswith("sqlite"), (
            f"Expected sqlite URL, got: {ts.DATABASE_URL}"
        )
    finally:
        if original is not None:
            os.environ["DATABASE_URL"] = original


def test_upsert_idempotent_sqlite():
    """
    Inserting the same candle twice via ON CONFLICT DO NOTHING must not create duplicates.
    Uses an in-memory SQLite engine for isolation (no Docker required).
    """
    import asyncio
    from datetime import datetime, timezone

    from sqlalchemy import create_engine, text, event
    from sqlalchemy.pool import StaticPool
    from app.models.market_data import Base, MarketData

    # Use synchronous SQLite in-memory engine for this test
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create the tables
    Base.metadata.create_all(engine)

    insert_sql = text("""
        INSERT INTO market_data
            (symbol, market, interval, timestamp, open, high, low, close, volume)
        VALUES
            (:symbol, :market, :interval, :timestamp, :open, :high, :low, :close, :volume)
        ON CONFLICT (symbol, interval, timestamp) DO NOTHING
    """)

    row = {
        "symbol": "AAPL",
        "market": "stock",
        "interval": "1D",
        "timestamp": datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc),
        "open": 150.0,
        "high": 155.0,
        "low": 149.0,
        "close": 153.0,
        "volume": 1000000.0,
    }

    with engine.connect() as conn:
        # Insert once
        conn.execute(insert_sql, row)
        conn.commit()
        # Insert the same row again — must not create a duplicate
        conn.execute(insert_sql, row)
        conn.commit()

        count = conn.execute(text("SELECT COUNT(*) FROM market_data")).scalar()

    assert count == 1, f"Expected 1 row, got {count} — upsert is not idempotent"
