"""
Data provider implementations.

Each provider implements the OHLCVProvider ABC defined in
app.ingestion.base_provider.

Available providers:
- YfinanceProvider: yfinance batch historical data for US stocks
- FinnhubProvider: Finnhub WebSocket real-time tick data for US stocks
- CoinGeckoProvider: CoinGecko OHLCV data for crypto (daily/4H)
- CCXTProvider: CCXT/Binance intraday OHLCV for crypto
"""
from app.ingestion.providers.yfinance_provider import YfinanceProvider
from app.ingestion.providers.finnhub_provider import FinnhubProvider
from app.ingestion.providers.coingecko_provider import CoinGeckoProvider, COINGECKO_COINS
from app.ingestion.providers.ccxt_provider import CCXTProvider

__all__ = [
    "YfinanceProvider",
    "FinnhubProvider",
    "CoinGeckoProvider",
    "CCXTProvider",
    "COINGECKO_COINS",
]
