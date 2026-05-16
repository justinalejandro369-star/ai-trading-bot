# Writing your own strategy

> **Status:** This document describes the **planned** pluggable strategy interface (Phase 8 on the [roadmap](ROADMAP.md)). The interface is not implemented yet on `main` — track progress in the open PR or issue tagged `strategy-interface`.
>
> Today the signal logic lives in `backend/app/analysis/signals.py::score_signal()`. You can already fork it and edit the weights for personal experiments — the docs below describe the cleaner pluggable interface that's landing next.

## Why this exists

The repo ships with one "baseline" strategy — RSI + MACD + Bollinger + EMA confluence, weights hardcoded, threshold 55. That's fine for a demo, but the whole point of an experimentation framework is to let you try your own algorithm and measure whether it beats the baseline on the same data.

The pluggable interface gives every strategy a name, a version, and a single function to implement. Multiple strategies coexist in the database tagged with `strategy_name`. The dashboard's `/backtest/compare` page lets you overlay equity curves from any two strategies side by side.

## The interface (planned)

`backend/app/strategies/base.py`:

```python
from abc import ABC, abstractmethod
from typing import ClassVar
import pandas as pd
from app.analysis.indicators import IndicatorSet
from app.analysis.signals import SignalResult


class BaseStrategy(ABC):
    """Implement this class to add your own algorithm."""

    name: ClassVar[str]                            # unique identifier, e.g. "ma_crossover"
    version: ClassVar[str]                         # semver, e.g. "1.0.0"
    description: ClassVar[str]                     # one-line description for the UI
    required_indicators: ClassVar[list[str]] = []  # optional: indicator names you need

    @abstractmethod
    def generate_signal(self, ind: IndicatorSet) -> SignalResult:
        """Per-bar signal. Called by the scanner for live signals."""

    @abstractmethod
    def generate_entries_exits(
        self, df: pd.DataFrame
    ) -> tuple[pd.Series, pd.Series]:
        """Vectorized signals across a DataFrame. Returns (entries, exits) bool Series.
        Called by the backtest engine — must be the same math as generate_signal."""
```

Two methods (per-bar + vectorized) because:
1. The scanner already has an `IndicatorSet` in hand — re-running indicator computation per bar would waste work
2. `vectorbt` wants two boolean Series, not a categorical column

## End-to-end: adding a simple MA crossover

`backend/app/strategies/ma_crossover.py`:

```python
import pandas as pd
import pandas_ta_classic as ta
from app.analysis.indicators import IndicatorSet
from app.analysis.signals import SignalResult
from app.strategies import register_strategy
from app.strategies.base import BaseStrategy


@register_strategy
class MACrossoverStrategy(BaseStrategy):
    name = "ma_crossover"
    version = "1.0.0"
    description = "Golden cross / death cross on EMA-50 vs EMA-200"

    def generate_signal(self, ind: IndicatorSet) -> SignalResult:
        if ind.ema_50 is None or ind.ema_200 is None:
            return SignalResult(direction="HOLD", confidence=0, reasons=[])

        if ind.ema_50 > ind.ema_200:
            return SignalResult(
                direction="BUY",
                confidence=70,
                entry_price=ind.close,
                stop_loss=ind.close * 0.97,
                target_price=ind.close * 1.05,
                reasons=["EMA-50 above EMA-200 (golden cross territory)"],
            )
        return SignalResult(
            direction="SELL",
            confidence=70,
            entry_price=ind.close,
            stop_loss=ind.close * 1.03,
            target_price=ind.close * 0.95,
            reasons=["EMA-50 below EMA-200 (death cross territory)"],
        )

    def generate_entries_exits(
        self, df: pd.DataFrame
    ) -> tuple[pd.Series, pd.Series]:
        fast = ta.ema(df["close"], length=50)
        slow = ta.ema(df["close"], length=200)
        crossed_up = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        crossed_down = (fast < slow) & (fast.shift(1) >= slow.shift(1))
        return crossed_up.fillna(False), crossed_down.fillna(False)
```

Register the module so the decorator runs at import time. Edit `backend/app/strategies/__init__.py`:

```python
from app.strategies import baseline, ma_crossover  # noqa: F401
```

## Testing

`backend/tests/test_strategies.py` checks:

- The registry discovers your strategy by name
- `generate_signal()` returns a valid `SignalResult`
- `generate_entries_exits()` returns two boolean Series of the same length as the input DataFrame
- A full backtest round-trip produces a different result from the baseline (sanity check that you actually wrote a different algorithm)

```bash
PYTHONPATH=backend uv --project backend run pytest tests/test_strategies.py -v
```

## Running it

```bash
# Apply the schema migration that adds strategy_name to signals and backtest_runs
cd backend && uv run alembic upgrade head

# Run a backtest tagged with your strategy
curl -X POST http://localhost:8000/api/backtest \
  -H 'Content-Type: application/json' \
  -b "access_token=<your-jwt>" \
  -d '{"symbol": "AAPL", "interval": "1d", "strategy_name": "ma_crossover"}'

# List all registered strategies
curl http://localhost:8000/api/strategies -b "access_token=<your-jwt>"

# Compare runs
curl 'http://localhost:8000/api/backtest/runs?symbol=AAPL' -b "access_token=<your-jwt>"
```

In the dashboard, navigate to `/backtest/compare`, pick `baseline` and `ma_crossover`, and see the equity curves overlaid plus the metrics side by side.

## Conventions

- **One strategy per file.** Filename matches `name` (snake_case).
- **Pure functions.** No DB, no FastAPI imports. Take data in, return data out. This is enforced by the test fixtures.
- **No look-ahead bias.** In `generate_entries_exits`, never use future bars. The backtest engine applies `shift(1)` automatically, but stay deliberate.
- **Version your strategy.** Bumping `version` lets you re-run backtests under a new name without overwriting prior results.

## When to open a PR vs keep it on your fork

- **Personal experiment / proprietary edge:** stay on your fork. The MIT license lets you keep your strategy private. Pull updates from `main` as the platform improves.
- **General-interest strategy with public reasoning:** open a PR. We'll review, run the parity tests, and ship it as a community example under `backend/app/strategies/community/`.

## Common pitfalls

- **Forgetting to register.** The decorator only runs if your module is imported. The `__init__.py` import is what triggers it.
- **Different math in scalar vs. vectorized paths.** The parity test in `test_strategies.py` would catch it — run the test before pushing.
- **Indicator NaN at the start of the series.** Always `.fillna(False)` your boolean Series before returning.
- **MIN_CANDLES.** EMA-200 needs ≥200 bars; the scanner silently skips assets with less data. Don't assume your strategy will run on tiny histories.

## Roadmap for the interface itself

See the open PR / issue tagged `strategy-interface` for status. The interface ships in Phase 8 of the [roadmap](ROADMAP.md). Until then, treat the example above as the design contract, not the running code.
