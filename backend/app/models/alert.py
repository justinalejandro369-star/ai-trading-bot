"""
SQLAlchemy ORM models for alerts: AlertRule and AlertEvent.

AlertRule: user-configured threshold (symbol + type + value).
AlertEvent: each fired alert, linked to its rule, persisted for history.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.models.market_data import Base

__all__ = ["AlertRule", "AlertEvent"]


class AlertRule(Base):
    """User-defined alert threshold."""
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    # threshold_type: "price_spike" | "volume_surge" | "trend_reversal"
    threshold_type = Column(String(30), nullable=False)
    # threshold_value: percentage for price_spike, multiplier for volume_surge,
    # unused (0) for trend_reversal (RSI crossover)
    threshold_value = Column(Float, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )


class AlertEvent(Base):
    """Record of a fired alert."""
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False)
    triggered_at = Column(DateTime(timezone=True), nullable=False)
    message = Column(String(500), nullable=False)
