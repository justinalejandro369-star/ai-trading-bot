"""
SQLAlchemy ORM model for the signals table.

Stores one row per (symbol, interval) — the scanner overwrites on each scan.
Composite PK ensures ON CONFLICT (symbol, interval) DO UPDATE works correctly.
Imports Base from market_data to share the same declarative registry.
"""
import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.models.market_data import Base

__all__ = ["TradingSignal"]


class TradingSignal(Base):
    """
    Latest trading signal per (symbol, interval).

    Upserted on every scan — one row per asset, always reflects the most
    recent analysis. Signal history is out of scope for Phase 2.

    Phase 7 additions:
      - explanation: cached LLM plain-language explanation (empty when LLM disabled)
      - multiframe_agreement: JSON dict of {interval: direction, agreement: bool}
    """
    __tablename__ = "signals"

    symbol                = Column(String(20),             nullable=False, primary_key=True)
    interval              = Column(String(5),              nullable=False, primary_key=True)
    strategy_name         = Column(String(64),             nullable=False, primary_key=True, default="baseline", server_default="baseline")
    scanned_at            = Column(DateTime(timezone=True), nullable=False)
    direction             = Column(String(4),              nullable=False)   # BUY|SELL|HOLD
    confidence            = Column(Integer,               nullable=False)   # 0-100
    regime                = Column(String(10),             nullable=False)   # trending|ranging|volatile
    close                 = Column(Float,                 nullable=False)
    entry_price           = Column(Float,                 nullable=True)
    stop_loss             = Column(Float,                 nullable=True)
    target_price          = Column(Float,                 nullable=True)
    rsi_14                = Column(Float,                 nullable=True)
    macd_val              = Column(Float,                 nullable=True)
    adx_14                = Column(Float,                 nullable=True)
    atr_14                = Column(Float,                 nullable=True)
    reasons               = Column(String(500),            nullable=True)    # JSON list serialized as string
    explanation           = Column(Text,                  nullable=True, default="")   # LLM explanation
    multiframe_agreement  = Column(Text,                  nullable=True, default="{}")  # JSON dict
    # LLM advisory fields — populated when LLM-enhanced signal scoring is enabled
    llm_adjustment        = Column(Integer,               nullable=True, default=0)     # -15 to +15
    llm_reasoning         = Column(Text,                  nullable=True, default="")    # LLM reasoning
    llm_patterns          = Column(Text,                  nullable=True, default="[]")  # JSON list of patterns

    def reasons_list(self) -> list[str]:
        """Deserialize reasons JSON string to list."""
        if self.reasons is None:
            return []
        try:
            return json.loads(self.reasons)
        except (json.JSONDecodeError, TypeError):
            return []

    def multiframe_dict(self) -> dict:
        """Deserialize multiframe_agreement JSON string to dict."""
        if self.multiframe_agreement is None:
            return {"agreement": False}
        try:
            return json.loads(self.multiframe_agreement)
        except (json.JSONDecodeError, TypeError):
            return {"agreement": False}

    def llm_patterns_list(self) -> list[str]:
        """Deserialize llm_patterns JSON string to list."""
        if self.llm_patterns is None:
            return []
        try:
            return json.loads(self.llm_patterns)
        except (json.JSONDecodeError, TypeError):
            return []
