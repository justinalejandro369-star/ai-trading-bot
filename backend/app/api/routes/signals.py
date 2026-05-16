"""
Trading signals REST endpoints.

GET /api/signals                       — all latest signals, optionally filtered
GET /api/signals/top?limit={N}         — top N signals by confidence DESC

Both endpoints read pre-computed rows from the signals table. Pass
``?strategy=<name>`` to scope results to one BaseStrategy; omit to see
every strategy.
"""
import logging
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.signal import TradingSignal

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/signals", tags=["signals"])


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


def _serialize(row: TradingSignal) -> dict:
    return {
        "symbol": row.symbol,
        "interval": row.interval,
        "strategy_name": row.strategy_name,
        "scanned_at": row.scanned_at.isoformat(),
        "direction": row.direction,
        "confidence": row.confidence,
        "regime": row.regime,
        "close": row.close,
        "entry_price": row.entry_price,
        "stop_loss": row.stop_loss,
        "target_price": row.target_price,
        "rsi_14": row.rsi_14,
        "macd_val": row.macd_val,
        "adx_14": row.adx_14,
        "atr_14": row.atr_14,
        "reasons": row.reasons_list(),
        "explanation": row.explanation or "",
        "multiframe_agreement": row.multiframe_dict(),
        "llm_adjustment": row.llm_adjustment or 0,
        "llm_reasoning": row.llm_reasoning or "",
        "llm_patterns": row.llm_patterns_list(),
    }


@router.get("")
async def get_all_signals(
    strategy: str | None = None,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> list[dict]:
    """Return latest signals. Filter by ``strategy`` (registered name) if provided."""
    query = select(TradingSignal)
    if strategy:
        query = query.where(TradingSignal.strategy_name == strategy)
    result = await session.execute(query)
    rows = result.scalars().all()
    return [_serialize(r) for r in rows]


@router.get("/top")
async def get_top_signals(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    strategy: str | None = None,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> list[dict]:
    """Return top N signals ranked by confidence DESC. Optional strategy filter."""
    query = select(TradingSignal).order_by(TradingSignal.confidence.desc()).limit(limit)
    if strategy:
        query = (
            select(TradingSignal)
            .where(TradingSignal.strategy_name == strategy)
            .order_by(TradingSignal.confidence.desc())
            .limit(limit)
        )
    result = await session.execute(query)
    rows = result.scalars().all()
    return [_serialize(r) for r in rows]
