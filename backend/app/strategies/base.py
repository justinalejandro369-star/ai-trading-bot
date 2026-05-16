"""
Pluggable trading strategy interface.

Mirrors the OHLCVProvider ABC pattern (app/ingestion/base_provider.py):
abstract base class + concrete implementations + registry. Lets any
contributor drop their own algorithm under app/strategies/ and have it
scanned, backtested, paper-traded, and compared against the baseline.

A strategy implements TWO methods:
  - generate_signal(IndicatorSet) -> SignalResult       (per-bar, used by the scanner)
  - generate_entries_exits(df)    -> (entries, exits)   (vectorized, used by backtest)

Both methods MUST implement the same logic. The parity test in
tests/test_strategies.py verifies they agree on a fixed fixture.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

import pandas as pd

from app.analysis.indicators import IndicatorSet
from app.analysis.signals import SignalResult

__all__ = ["BaseStrategy"]


class BaseStrategy(ABC):
    """Abstract base for all trading strategies.

    Subclasses MUST set the three class variables and implement both
    abstract methods. Decorate the subclass with @register_strategy so
    the registry picks it up at import time.
    """

    #: Unique identifier (snake_case). Persisted on signals + backtest rows.
    name: ClassVar[str]

    #: Semantic version string. Bump this if you change the math.
    version: ClassVar[str]

    #: One-line description shown in the UI strategy picker.
    description: ClassVar[str]

    #: Optional metadata: indicator names required by generate_signal().
    required_indicators: ClassVar[list[str]] = []

    @abstractmethod
    def generate_signal(self, ind: IndicatorSet) -> SignalResult:
        """Compute a BUY/SELL/HOLD signal for the latest bar.

        Called by the scanner once per (symbol, interval) per scan.
        Must be a pure function — no DB access, no I/O.
        """

    @abstractmethod
    def generate_entries_exits(
        self, df: pd.DataFrame
    ) -> tuple[pd.Series, pd.Series]:
        """Compute vectorized BUY-entry and SELL-exit boolean Series.

        Called by the backtest engine. Returns two boolean Series with
        the same index as ``df`` — entries (BUY) and exits (SELL).

        The engine applies ``.shift(1).fillna(False)`` to enforce
        look-ahead bias prevention; do NOT shift inside this method.
        """

    def to_metadata(self) -> dict:
        """Serialize strategy metadata for the GET /api/strategies endpoint."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "required_indicators": list(self.required_indicators),
        }
