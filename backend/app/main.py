"""
FastAPI application entry point.

Wires together:
- APScheduler lifespan (from ingestion/scheduler.py)
- Market data REST router (from api/routes/market_data.py)
- Indicators REST router (from api/routes/indicators.py)  [Phase 2]
- Signals REST router (from api/routes/signals.py)        [Phase 2]
- Backtesting REST router (from api/routes/backtest.py)   [Phase 3]

Start with: uvicorn app.main:app --reload
"""
import logging

from fastapi import FastAPI

from app.api.routes.market_data import router as market_data_router
from app.api.routes.indicators import router as indicators_router
from app.api.routes.signals import router as signals_router
from app.api.routes.backtest import router as backtest_router
from app.ingestion.scheduler import lifespan

__all__ = ["app"]

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Trading Bot API",
    description="AI-powered trading assistant — data ingestion, market data, signals, and backtesting API.",
    version="0.3.0",
    lifespan=lifespan,
)

app.include_router(market_data_router, prefix="/api")
app.include_router(indicators_router, prefix="/api")
app.include_router(signals_router, prefix="/api")
app.include_router(backtest_router, prefix="/api")
