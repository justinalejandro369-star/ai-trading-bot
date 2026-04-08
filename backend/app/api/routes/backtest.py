"""
Backtesting REST endpoint.

POST /api/backtest
  Request: BacktestRequest (symbol, interval, commission, slippage, init_cash)
  Response: BacktestResult.to_dict() — all 7 metrics + equity_curve

The vectorbt call is CPU-bound and synchronous. It is wrapped in
run_in_threadpool() to keep the FastAPI async event loop free during execution.

Candles are loaded from the market_data table via the standard async session.
Result is persisted to backtest_runs for Phase 4 comparison.
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.routes.market_data import get_session
from app.backtesting.engine import run_backtest
from app.backtesting.models import BacktestRequest
from app.models.backtest import BacktestRun
from app.models.market_data import MarketData

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])


async def _load_candles_df(
    session: AsyncSession,
    symbol: str,
    interval: str,
):
    """
    Load all stored OHLCV candles for symbol+interval from market_data as a DataFrame.

    Returns None if no rows exist. Returns a DataFrame with DatetimeIndex
    sorted ascending by timestamp, with columns [open, high, low, close, volume].
    """
    import pandas as pd

    result = await session.execute(
        select(MarketData)
        .where(
            MarketData.symbol == symbol.upper(),
            MarketData.interval == interval,
        )
        .order_by(MarketData.timestamp.asc())
    )
    rows = result.scalars().all()

    if not rows:
        return None

    records = [
        {
            "timestamp": r.timestamp,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
        }
        for r in rows
    ]
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    return df


@router.post("")
async def run_backtest_endpoint(
    request: BacktestRequest,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """
    Run a vectorbt backtest for a stored asset.

    Args:
        request: BacktestRequest with symbol, interval, commission, slippage, init_cash.
        session: Injected async DB session.

    Returns:
        BacktestResult dict with: sharpe_ratio, max_drawdown, win_rate, profit_factor,
        total_return, total_trades, equity_curve.

    Raises:
        HTTPException 422: If fewer than MIN_CANDLES candle rows are available.
    """
    df = await _load_candles_df(session, request.symbol, request.interval.lower())

    if df is None or len(df) == 0:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data: no candles found for {request.symbol}/{request.interval}",
        )

    try:
        result = await run_in_threadpool(
            run_backtest,
            df,
            request.commission,
            request.slippage,
            request.init_cash,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Persist result to backtest_runs for Phase 4 comparison
    run = BacktestRun(
        symbol=request.symbol.upper(),
        interval=request.interval,
        run_at=datetime.now(tz=timezone.utc),
        commission=request.commission,
        slippage=request.slippage,
        init_cash=request.init_cash,
        sharpe_ratio=result.sharpe_ratio,
        max_drawdown=result.max_drawdown,
        win_rate=result.win_rate,
        profit_factor=result.profit_factor,
        total_return=result.total_return,
        total_trades=result.total_trades,
        equity_curve=json.dumps(result.equity_curve),
    )
    session.add(run)
    await session.commit()

    log.info(
        "Backtest complete: %s/%s — Sharpe=%.2f Win=%.1f%% Trades=%d",
        request.symbol,
        request.interval,
        result.sharpe_ratio,
        result.win_rate * 100,
        result.total_trades,
    )

    return result.to_dict()
