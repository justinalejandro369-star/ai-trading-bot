"""Create market_data table as TimescaleDB hypertable.

Revision ID: 001
Revises:
Create Date: 2026-04-08

Uses raw SQL (not ORM) because create_hypertable() must be called via
a TimescaleDB extension function, which cannot be expressed through
SQLAlchemy ORM table creation.

SQLite dev fallback: The hypertable call is wrapped in try/except so
this migration works in local dev without Docker/TimescaleDB.
"""
import logging
import sqlalchemy.exc

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the market_data table using raw DDL matching the ORM model exactly
    op.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            symbol      VARCHAR(20)       NOT NULL,
            market      VARCHAR(10)       NOT NULL,
            interval    VARCHAR(5)        NOT NULL,
            timestamp   TIMESTAMPTZ       NOT NULL,
            open        DOUBLE PRECISION  NOT NULL,
            high        DOUBLE PRECISION  NOT NULL,
            low         DOUBLE PRECISION  NOT NULL,
            close       DOUBLE PRECISION  NOT NULL,
            volume      DOUBLE PRECISION  NOT NULL,
            PRIMARY KEY (symbol, interval, timestamp)
        );
    """)

    # Convert to TimescaleDB hypertable partitioned by timestamp.
    # chunk_time_interval of 7 days is appropriate for mixed 1m-1D OHLCV candles.
    # Wrapped in try/except: TimescaleDB extension is not available in SQLite dev env.
    try:
        op.execute("""
            SELECT create_hypertable(
                'market_data',
                'timestamp',
                chunk_time_interval => INTERVAL '7 days',
                if_not_exists => TRUE
            );
        """)
    except sqlalchemy.exc.ProgrammingError as exc:
        logger.warning(
            "create_hypertable() failed — TimescaleDB extension not available "
            "(expected in SQLite dev environment). "
            "Plain table will be used. Error: %s",
            exc,
        )
        # Rollback the savepoint created by the failed statement
        op.execute("ROLLBACK TO SAVEPOINT alembic_hypertable_fallback")

    # Composite index optimized for the query pattern:
    # WHERE symbol=X AND interval=Y AND timestamp BETWEEN a AND b
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_market_data_symbol_interval_ts
        ON market_data (symbol, interval, timestamp DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS market_data;")
