"""
Shared pytest fixtures for Phase 2 analysis engine tests and Phase 5 auth.
"""
import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Auth bypass helper for existing API tests
# ---------------------------------------------------------------------------

def override_get_current_user():
    """
    FastAPI dependency override that returns a fake admin user dict.
    Inject via: app.dependency_overrides[get_current_user] = override_get_current_user
    This allows pre-auth API tests to continue passing after auth was added.
    """
    return {"sub": "admin"}


# ---------------------------------------------------------------------------
# Auto-reset rate limiter before every test (prevents bleed between tests)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_rate_limiter_global():
    """Reset the shared rate limiter storage bucket before every test."""
    from app.core.rate_limit import limiter
    limiter._storage.reset()
    yield


def make_ohlcv_df(n_rows: int, seed: int = 42) -> pd.DataFrame:
    """
    Generate a synthetic OHLCV DataFrame with a DatetimeIndex.

    Prices follow a random walk. Volume is random positive integers.
    Suitable for indicator computation tests — indicators will return
    numeric values for n_rows >= 200.

    Args:
        n_rows: Number of candle rows to generate.
        seed: Random seed for reproducibility.
    """
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0, 1, n_rows))
    # Ensure price is always positive
    close = np.maximum(close, 1.0)
    high = close + rng.uniform(0, 2, n_rows)
    low = close - rng.uniform(0, 2, n_rows)
    low = np.maximum(low, 0.5)
    open_ = close + rng.normal(0, 0.5, n_rows)
    volume = rng.integers(1_000_000, 5_000_000, n_rows).astype(float)

    index = pd.date_range("2020-01-01", periods=n_rows, freq="D", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=index,
    )


def make_zero_volume_df(n_rows: int = 250) -> pd.DataFrame:
    """Synthetic OHLCV where volume=0.0, simulating CoinGecko assets."""
    df = make_ohlcv_df(n_rows)
    df["volume"] = 0.0
    return df


@pytest.fixture
def df_200():
    """200-row OHLCV DataFrame — exactly at the minimum candle threshold."""
    return make_ohlcv_df(200)


@pytest.fixture
def df_250():
    """250-row OHLCV DataFrame — well above minimum threshold."""
    return make_ohlcv_df(250)


@pytest.fixture
def df_199():
    """199-row OHLCV DataFrame — one below minimum threshold."""
    return make_ohlcv_df(199)
