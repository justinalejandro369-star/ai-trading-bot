"""
Backtesting REST endpoint.

POST /api/backtest
  Request: BacktestRequest (symbol, interval, commission, slippage, init_cash, strategy_name)
  Response: BacktestResult.to_dict() — all metrics + equity_curve + strategy_name

The vectorbt call is CPU-bound and synchronous. It is wrapped in
run_in_threadpool() to keep the FastAPI async event loop free during execution.

Candles are loaded from the market_data table via the standard async session.
Result is persisted to backtest_runs tagged with the requested strategy_name.
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
from app.strategies import get_strategy

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])


async def _load_candles_df(
    session: AsyncSession,
    symbol: str,
    interval: str,
):
    """Load all stored OHLCV candles for symbol+interval as a DataFrame.

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
    """Run a vectorbt backtest for a stored asset with the selected strategy."""
    try:
        strategy = get_strategy(request.strategy_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

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
            strategy,
            request.commission,
            request.slippage,
            request.init_cash,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    run = BacktestRun(
        symbol=request.symbol.upper(),
        interval=request.interval,
        strategy_name=result.strategy_name,
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
        "Backtest complete: %s/%s [%s] — Sharpe=%.2f Win=%.1f%% Trades=%d",
        request.symbol,
        request.interval,
        result.strategy_name,
        result.sharpe_ratio,
        result.win_rate * 100,
        result.total_trades,
    )

    return result.to_dict()


@router.get("/runs")
async def list_backtest_runs(
    symbol: str | None = None,
    strategy: str | None = None,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> list[dict]:
    """List historical backtest runs (without equity_curve)."""
    query = select(BacktestRun).order_by(BacktestRun.run_at.desc())
    if symbol:
        query = query.where(BacktestRun.symbol == symbol.upper())
    if strategy:
        query = query.where(BacktestRun.strategy_name == strategy)

    result = await session.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "interval": r.interval,
            "strategy_name": r.strategy_name,
            "run_at": r.run_at.isoformat() if r.run_at else None,
            "sharpe_ratio": r.sharpe_ratio,
            "max_drawdown": r.max_drawdown,
            "win_rate": r.win_rate,
            "profit_factor": r.profit_factor,
            "total_return": r.total_return,
            "total_trades": r.total_trades,
            "commission": r.commission,
            "slippage": r.slippage,
            "init_cash": r.init_cash,
        }
        for r in rows
    ]


@router.get("/runs/{run_id}")
async def get_backtest_run(
    run_id: int,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> dict:
    """Get a single backtest run including its full equity_curve."""
    result = await session.execute(
        select(BacktestRun).where(BacktestRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")

    return {
        "id": run.id,
        "symbol": run.symbol,
        "interval": run.interval,
        "strategy_name": run.strategy_name,
        "run_at": run.run_at.isoformat() if run.run_at else None,
        "sharpe_ratio": run.sharpe_ratio,
        "max_drawdown": run.max_drawdown,
        "win_rate": run.win_rate,
        "profit_factor": run.profit_factor,
        "total_return": run.total_return,
        "total_trades": run.total_trades,
        "commission": run.commission,
        "slippage": run.slippage,
        "init_cash": run.init_cash,
        "equity_curve": run.equity_curve_data(),
    }
