"""
FastAPI application entry point.

Wires together:
- APScheduler lifespan (from ingestion/scheduler.py)
- Auth router (login, logout, /auth/me) [Phase 5]
- WebSocket router (/ws/live) [Phase 5]
- Market data REST router (from api/routes/market_data.py)
- Indicators REST router (from api/routes/indicators.py)  [Phase 2]
- Signals REST router (from api/routes/signals.py)        [Phase 2]
- Backtesting REST router (from api/routes/backtest.py)   [Phase 3]
- Paper trading REST router (from api/routes/paper_trading.py) [Phase 4]

Start with: uvicorn app.main:app --reload
"""
import logging

import secure
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes.alerts import router as alerts_router
from app.api.routes.auth import router as auth_router
from app.api.routes.backtest import router as backtest_router
from app.api.routes.education import router as education_router
from app.api.routes.indicators import router as indicators_router
from app.api.routes.market_data import router as market_data_router
from app.api.routes.paper_trading import router as paper_trading_router
from app.api.routes.signals import router as signals_router
from app.api.routes.websocket import router as ws_router
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.ingestion.scheduler import lifespan

__all__ = ["app"]

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Trading Bot API",
    description=(
        "AI-powered trading assistant — data ingestion, market data, signals, "
        "backtesting, and paper trading API."
    ),
    version="0.5.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS (must be before security headers middleware)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
)

# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------
_secure_headers = secure.Secure.with_default_headers()


@app.middleware("http")
async def set_secure_headers(request: Request, call_next):
    response = await call_next(request)
    await _secure_headers.set_headers_async(response)
    return response


# ---------------------------------------------------------------------------
# Routers — auth (unprotected) + WebSocket
# ---------------------------------------------------------------------------
app.include_router(auth_router, prefix="/auth")
app.include_router(ws_router)

# ---------------------------------------------------------------------------
# Routers — protected with JWT cookie dependency
# ---------------------------------------------------------------------------
_auth_dep = [Depends(get_current_user)]

app.include_router(market_data_router, prefix="/api", dependencies=_auth_dep)
app.include_router(indicators_router, prefix="/api", dependencies=_auth_dep)
app.include_router(signals_router, prefix="/api", dependencies=_auth_dep)
app.include_router(backtest_router, prefix="/api", dependencies=_auth_dep)
app.include_router(paper_trading_router, prefix="/api", dependencies=_auth_dep)
app.include_router(alerts_router, prefix="/api", dependencies=_auth_dep)
app.include_router(education_router, prefix="/api")
