"""
Strategy registry REST endpoints.

GET /api/strategies            — list every registered strategy with metadata
GET /api/strategies/{name}     — single strategy metadata

The registry is populated at import time by the @register_strategy
decorators in app/strategies/*.py — no DB access happens here.
"""
import logging

from fastapi import APIRouter, HTTPException

from app.strategies import get_strategy, list_strategies

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("")
async def get_all_strategies() -> list[dict]:
    """Return every registered strategy's metadata."""
    return list_strategies()


@router.get("/{name}")
async def get_one_strategy(name: str) -> dict:
    """Return metadata for a single strategy. 404 if unknown."""
    try:
        strategy = get_strategy(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return strategy.to_metadata()
