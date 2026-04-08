"""
Data normalizers: map provider-specific formats to the canonical OHLCVCandle schema.

All data sources pass through these functions before touching the database.
This ensures provider-specific field names (e.g., yfinance "Adj Close") never
appear in analysis code or the storage layer.
"""
from datetime import datetime, timezone

import pandas as pd

from app.ingestion.base_provider import OHLCVCandle

__all__ = ["normalize_yfinance", "normalize_coingecko"]


def normalize_yfinance(
    df: pd.DataFrame,
    symbol: str,
    interval: str,
) -> list[OHLCVCandle]:
    """
    Normalize a yfinance DataFrame into a list of OHLCVCandle instances.

    yfinance returns a DataFrame with a DatetimeIndex and columns:
    Open, High, Low, Close, Volume.

    Args:
        df: DataFrame from yfinance (ticker.history() or yf.download())
        symbol: Stock ticker (e.g., "AAPL")
        interval: Candle size (e.g., "1D", "1H", "5m")

    Returns:
        List of OHLCVCandle instances with market == "stock"

    Raises:
        ValueError: If df is empty or any candle would have a tz-naive timestamp
    """
    if df is None or df.empty:
        raise ValueError(f"yfinance DataFrame for {symbol} is empty — no candles to normalize")

    candles: list[OHLCVCandle] = []
    for ts, row in df.iterrows():
        # Convert index timestamp to timezone-aware UTC datetime
        if isinstance(ts, pd.Timestamp):
            if ts.tzinfo is None:
                # Localize naive timestamps to UTC (yfinance sometimes returns naive)
                ts = ts.tz_localize("UTC")
            dt: datetime = ts.to_pydatetime()
        else:
            raise ValueError(f"Unexpected timestamp type from yfinance: {type(ts)}")

        if dt.tzinfo is None:
            raise ValueError(
                f"Timestamp {dt} for {symbol} has no timezone info — "
                "all candles must be timezone-aware"
            )

        candle = OHLCVCandle(
            symbol=symbol,
            market="stock",
            interval=interval,
            timestamp=dt,
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=float(row["Volume"]),
        )
        candles.append(candle)

    return candles


def normalize_coingecko(
    raw_list: list[list],
    coin_id: str,
) -> list[OHLCVCandle]:
    """
    Normalize CoinGecko OHLC data into a list of OHLCVCandle instances.

    CoinGecko's /coins/{id}/ohlc endpoint returns:
        [[timestamp_ms, open, high, low, close], ...]  (5-element rows)

    Candle granularity is auto-determined by the 'days' parameter:
        - 1-2 days  -> 30-minute candles
        - 3-30 days -> 4-hour candles (most common for historical data)
        - 31+ days  -> 4-day candles

    IMPORTANT: CoinGecko OHLC endpoint does NOT include volume.
    Volume is set to 0.0 here as a known limitation.

    Args:
        raw_list: Raw CoinGecko OHLC response [[ts_ms, o, h, l, c], ...]
        coin_id: CoinGecko coin ID (e.g., "bitcoin", "ethereum")

    Returns:
        List of OHLCVCandle instances with market == "crypto" and interval == "4H"

    Raises:
        ValueError: If raw_list is empty or any candle would have a tz-naive timestamp
    """
    if not raw_list:
        raise ValueError(f"CoinGecko raw list for {coin_id} is empty — no candles to normalize")

    candles: list[OHLCVCandle] = []
    for entry in raw_list:
        timestamp_ms, open_price, high_price, low_price, close_price = entry

        # Convert millisecond Unix timestamp to UTC datetime
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)

        if dt.tzinfo is None:
            raise ValueError(
                f"Timestamp {dt} for {coin_id} has no timezone info — "
                "all candles must be timezone-aware"
            )

        candle = OHLCVCandle(
            symbol=coin_id,
            market="crypto",
            interval="4H",  # CoinGecko 3-30 day response auto-granularity
            timestamp=dt,
            open=float(open_price),
            high=float(high_price),
            low=float(low_price),
            close=float(close_price),
            volume=0.0,  # Known limitation: CoinGecko OHLC endpoint returns no volume field.
            # Future enhancement: join with market_chart endpoint.
        )
        candles.append(candle)

    return candles
