"""
Strategy registry.

Strategies register themselves at import time via the @register_strategy
decorator. The bottom of this file imports the bundled strategy modules
so their @register_strategy decorators run.

To add a new strategy, do BOTH of these:
    1. Subclass BaseStrategy in a new file under app/strategies/ and decorate
       the class with @register_strategy.
    2. Import the module at the bottom of this file (so the decorator runs
       and the class lands in STRATEGY_REGISTRY).

API:
    register_strategy(cls)     decorator — registers a BaseStrategy subclass
    get_strategy(name)         -> BaseStrategy instance — raises KeyError on miss
    list_strategies()          -> list[dict] — metadata for every registered strategy
    STRATEGY_REGISTRY          -> dict[str, type[BaseStrategy]] — read-only inspection
"""
from __future__ import annotations

from typing import Type

from app.strategies.base import BaseStrategy

__all__ = [
    "BaseStrategy",
    "STRATEGY_REGISTRY",
    "register_strategy",
    "get_strategy",
    "list_strategies",
]

#: Maps strategy.name -> strategy class. Populated by @register_strategy.
STRATEGY_REGISTRY: dict[str, Type[BaseStrategy]] = {}


def register_strategy(cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
    """Class decorator that adds a BaseStrategy subclass to the registry.

    Raises ValueError on duplicate name. Returns the class unchanged so
    it remains usable as a normal type.
    """
    if not issubclass(cls, BaseStrategy):
        raise TypeError(f"{cls.__name__} must subclass BaseStrategy")
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError(f"{cls.__name__} must define class attribute 'name'")
    if name in STRATEGY_REGISTRY:
        existing = STRATEGY_REGISTRY[name]
        if existing is cls:
            return cls  # idempotent re-import — safe
        raise ValueError(
            f"Strategy name '{name}' is already registered by "
            f"{existing.__module__}.{existing.__name__}"
        )
    STRATEGY_REGISTRY[name] = cls
    return cls


def get_strategy(name: str) -> BaseStrategy:
    """Look up a strategy by name and return a fresh instance.

    Raises KeyError if no strategy is registered under that name.
    """
    if name not in STRATEGY_REGISTRY:
        raise KeyError(f"Unknown strategy: {name!r}. Known: {sorted(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name]()


def list_strategies() -> list[dict]:
    """Return metadata for every registered strategy (sorted by name)."""
    return [cls().to_metadata() for _, cls in sorted(STRATEGY_REGISTRY.items())]


# ---------------------------------------------------------------------------
# Auto-import bundled strategies so their @register_strategy decorators run.
# Add new strategies here.
# ---------------------------------------------------------------------------
from app.strategies import baseline as _baseline  # noqa: E402, F401
from app.strategies import example_ma_crossover as _example  # noqa: E402, F401
