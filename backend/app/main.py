"""
FastAPI application entry point.

Wires together:
- APScheduler lifespan (from ingestion/scheduler.py)
- Market data REST router (from api/routes/market_data.py)

Start with: uvicorn app.main:app --reload
"""
import logging

from fastapi import FastAPI

from app.api.routes.market_data import router as market_data_router
from app.ingestion.scheduler import lifespan

__all__ = ["app"]

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Trading Bot API",
    description="AI-powered trading assistant — data ingestion and market data API.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(market_data_router, prefix="/api")
