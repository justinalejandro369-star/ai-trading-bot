"""
Trading signals REST endpoints.

GET /api/signals                   — all latest signals, unordered
GET /api/signals/top?limit={N}     — top N signals by confidence DESC

Both endpoints read pre-computed rows from the signals table.
No indicator computation happens here — the scanner populates the table.

Security:
  - limit: enforced ge=1, le=100 — 422 on violation
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
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> list[dict]:
    """Return all latest signals from the signals table (unordered)."""
    result = await session.execute(select(TradingSignal))
    rows = result.scalars().all()
    return [_serialize(r) for r in rows]


@router.get("/top")
async def get_top_signals(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    session: AsyncSession = Depends(get_session),  # type: ignore[assignment]
) -> list[dict]:
    """Return top N signals ranked by confidence DESC (highest opportunity first)."""
    result = await session.execute(
        select(TradingSignal)
        .order_by(TradingSignal.confidence.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [_serialize(r) for r in rows]
