"""
Shared pytest fixtures for the trading bot test suite.
"""
import time
from datetime import datetime, timezone

import pandas as pd
import pytest


@pytest.fixture
def sample_yfinance_df():
    """
    Minimal pd.DataFrame mimicking yfinance output:
    DatetimeIndex (UTC) with Open, High, Low, Close, Volume columns.
    """
    now = datetime.now(tz=timezone.utc)
    timestamps = [
        pd.Timestamp("2024-01-02 14:30:00", tz="UTC"),
        pd.Timestamp("2024-01-03 14:30:00", tz="UTC"),
        pd.Timestamp("2024-01-04 14:30:00", tz="UTC"),
    ]
    data = {
        "Open":   [150.0, 151.0, 152.0],
        "High":   [155.0, 156.0, 157.0],
        "Low":    [149.0, 150.0, 151.0],
        "Close":  [153.0, 154.0, 155.0],
        "Volume": [1000000.0, 1100000.0, 1200000.0],
    }
    df = pd.DataFrame(data, index=pd.DatetimeIndex(timestamps))
    df.index.name = "Date"
    return df


@pytest.fixture
def sample_coingecko_raw():
    """
    CoinGecko OHLC endpoint returns [[timestamp_ms, open, high, low, close], ...].
    Volume is NOT included (known limitation of CoinGecko OHLC endpoint).
    """
    now_ms = int(time.time() * 1000)
    interval_ms = 4 * 60 * 60 * 1000  # 4 hours in ms
    return [
        [now_ms - 2 * interval_ms, 42000.0, 43000.0, 41000.0, 42500.0],
        [now_ms - 1 * interval_ms, 42500.0, 44000.0, 42000.0, 43500.0],
        [now_ms,                   43500.0, 45000.0, 43000.0, 44000.0],
    ]
