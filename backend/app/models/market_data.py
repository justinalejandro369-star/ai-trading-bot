"""
SQLAlchemy ORM model for the market_data table.

The composite primary key (symbol, interval, timestamp) mirrors the TimescaleDB
hypertable DDL in alembic/versions/001_create_ohlcv_hypertable.py.
Columns must stay in sync with OHLCVCandle fields in base_provider.py.
"""
from sqlalchemy import Column, DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase

__all__ = ["Base", "MarketData"]


class Base(DeclarativeBase):
    pass


class MarketData(Base):
    """
    Canonical storage model for OHLCV candle data.

    Mirrors the TimescaleDB hypertable created in the 001 Alembic migration.
    The composite primary key (symbol, interval, timestamp) ensures ON CONFLICT
    DO NOTHING upserts work correctly for idempotent ingestion.
    """
    __tablename__ = "market_data"

    symbol    = Column(String(20),            nullable=False, primary_key=True)
    market    = Column(String(10),            nullable=False)
    interval  = Column(String(5),             nullable=False, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    open      = Column(Float,                 nullable=False)
    high      = Column(Float,                 nullable=False)
    low       = Column(Float,                 nullable=False)
    close     = Column(Float,                 nullable=False)
    volume    = Column(Float,                 nullable=False)
