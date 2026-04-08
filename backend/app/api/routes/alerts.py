"""
Alert rules CRUD + alert history endpoint.

Routes:
  POST   /api/alerts/rules          — create alert rule
  GET    /api/alerts/rules          — list all alert rules
  DELETE /api/alerts/rules/{id}     — delete alert rule
  GET    /api/alerts/history        — recent alert events (last 100)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.alert import AlertEvent, AlertRule

__all__ = ["router"]

router = APIRouter(prefix="/alerts", tags=["alerts"])

VALID_THRESHOLD_TYPES = {"price_spike", "volume_surge", "trend_reversal"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AlertRuleCreate(BaseModel):
    symbol: str
    threshold_type: str
    threshold_value: float


class AlertRuleOut(BaseModel):
    id: int
    symbol: str
    threshold_type: str
    threshold_value: float
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertEventOut(BaseModel):
    id: int
    rule_id: int
    triggered_at: datetime
    message: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def get_session():
    async with async_session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/rules", response_model=AlertRuleOut, status_code=201)
async def create_alert_rule(body: AlertRuleCreate, session: SessionDep):
    if body.threshold_type not in VALID_THRESHOLD_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"threshold_type must be one of {sorted(VALID_THRESHOLD_TYPES)}",
        )
    rule = AlertRule(
        symbol=body.symbol.upper(),
        threshold_type=body.threshold_type,
        threshold_value=body.threshold_value,
        created_at=datetime.now(tz=timezone.utc),
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("/rules", response_model=list[AlertRuleOut])
async def list_alert_rules(session: SessionDep):
    result = await session.execute(select(AlertRule).order_by(AlertRule.id))
    return result.scalars().all()


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_alert_rule(rule_id: int, session: SessionDep):
    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    await session.delete(rule)
    await session.commit()


@router.get("/history", response_model=list[AlertEventOut])
async def get_alert_history(session: SessionDep, limit: int = 100):
    result = await session.execute(
        select(AlertEvent)
        .order_by(AlertEvent.triggered_at.desc())
        .limit(min(limit, 500))
    )
    return result.scalars().all()
