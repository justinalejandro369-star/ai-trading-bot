"""
Watchlist and interval constants shared across scheduler and scanner modules.

Defined here (not in scheduler.py) to avoid a circular import:
  scanner.py imports these constants AND analysis_scan_job is imported by scheduler.py.

Both scheduler.py and scanner.py import from this module.
"""

__all__ = [
    "STOCK_WATCHLIST",
    "STOCK_INTERVALS",
    "CCXT_CRYPTO_SYMBOLS",
    "CCXT_INTERVALS",
]

#: Top-5 US stocks by market cap -- primary watchlist for MVP
STOCK_WATCHLIST: list[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

#: yfinance intervals -- must be lowercase to match YFINANCE_MAX_HISTORY keys.
#: Note: yfinance uses "1h"/"1d" (lowercase), not "1H"/"1D".
#: 4H is intentionally omitted -- yfinance 4h support is unreliable on free tier.
STOCK_INTERVALS: list[str] = ["1m", "5m", "15m", "1h", "1d"]

#: Top-3 crypto pairs on Binance (CCXT format: "BASE/QUOTE")
CCXT_CRYPTO_SYMBOLS: list[str] = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

#: All 6 canonical app intervals -- CCXT_INTERVAL_MAP supports all of these
CCXT_INTERVALS: list[str] = ["1m", "5m", "15m", "1H", "4H", "1D"]
