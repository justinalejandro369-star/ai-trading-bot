"""
FinnhubProvider: real-time stock tick data via Finnhub WebSocket.

Design constraints (from RESEARCH.md Pattern 4, Pitfall 4, Pitfall 6):
- Free tier: 50 simultaneous subscriptions, 60 calls/min.
- WebSocket connection must have ping_interval=20, ping_timeout=10 to detect dead
  connections before the server silently drops them.
- The reconnect loop sleeps 5 seconds between attempts to prevent CPU spinning.
- fetch_historical() and fetch_latest() are NOT supported — use YfinanceProvider
  for historical stock data.

Thread safety:
- last_prices dict is updated from a background daemon thread (WebSocketApp thread).
- For MVP single-writer / single-reader use, dict operations in CPython are
  GIL-protected at the bytecode level — no explicit lock is needed.
  For production multi-reader scenarios, use threading.Lock.
"""
import json
import logging
import threading
import time
from datetime import datetime

import websocket

from app.ingestion.base_provider import OHLCVCandle, OHLCVProvider
from app.core.config import settings

__all__ = ["FinnhubProvider"]

logger = logging.getLogger(__name__)

_FINNHUB_WS_URL = "wss://ws.finnhub.io"
_MAX_SUBSCRIPTIONS = 50
_RECONNECT_SLEEP_SECONDS = 5


class FinnhubProvider(OHLCVProvider):
    """
    Receives real-time price ticks from Finnhub via WebSocket.

    Usage:
        provider = FinnhubProvider()
        provider.connect_websocket(["AAPL", "MSFT", "GOOGL"])
        # In async polling loop:
        price = provider.last_prices.get("AAPL")
    """

    def __init__(self) -> None:
        self.last_prices: dict[str, float] = {}
        self._api_key: str = settings.FINNHUB_API_KEY
        self._subscribed_symbols: list[str] = []
        self._ws: websocket.WebSocketApp | None = None

    # ------------------------------------------------------------------
    # WebSocket lifecycle
    # ------------------------------------------------------------------

    def connect_websocket(self, symbols: list[str]) -> None:
        """
        Start the Finnhub WebSocket in a background daemon thread.

        Subscribes to the given symbols on_open and enters a reconnect loop
        that sleeps _RECONNECT_SLEEP_SECONDS between reconnection attempts.

        Args:
            symbols: List of stock tickers to subscribe (max 50).
        """
        self.subscribe(symbols)  # Validates count; stores list
        url = f"{_FINNHUB_WS_URL}?token={self._api_key}"

        def on_open(ws: websocket.WebSocketApp) -> None:
            logger.info("Finnhub WebSocket connected; subscribing to %d symbols", len(self._subscribed_symbols))
            for sym in self._subscribed_symbols:
                ws.send(json.dumps({"type": "subscribe", "symbol": sym}))

        ws_app = websocket.WebSocketApp(
            url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=on_open,
        )
        self._ws = ws_app

        def _run_forever() -> None:
            while True:
                try:
                    ws_app.run_forever(
                        ping_interval=20,
                        ping_timeout=10,
                    )
                except Exception as exc:
                    logger.error("Finnhub WebSocket exception: %s", exc)
                logger.warning(
                    "Finnhub WebSocket disconnected — reconnecting in %ds",
                    _RECONNECT_SLEEP_SECONDS,
                )
                time.sleep(_RECONNECT_SLEEP_SECONDS)

        thread = threading.Thread(target=_run_forever, daemon=True, name="finnhub-ws")
        thread.start()
        logger.info("Finnhub WebSocket thread started (daemon=True)")

    def subscribe(self, symbols: list[str]) -> None:
        """
        Validate and store the subscription list.

        Args:
            symbols: List of stock tickers to subscribe.

        Raises:
            ValueError: If more than 50 symbols are requested (Finnhub free tier limit).
        """
        if len(symbols) > _MAX_SUBSCRIPTIONS:
            raise ValueError(
                f"Finnhub free tier supports a maximum of {_MAX_SUBSCRIPTIONS} "
                f"simultaneous subscriptions; {len(symbols)} requested."
            )
        self._subscribed_symbols = list(symbols)

    # ------------------------------------------------------------------
    # WebSocket callbacks
    # ------------------------------------------------------------------

    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Parse incoming trade messages and update last_prices."""
        try:
            payload = json.loads(message)
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode Finnhub message: %s", exc)
            return

        if payload.get("type") != "trade":
            return

        for trade in payload.get("data", []):
            symbol = trade.get("s")
            price = trade.get("p")
            if symbol is not None and price is not None:
                self.last_prices[symbol] = float(price)
                logger.debug("Tick: %s = %.4f", symbol, price)

    def _on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        logger.error("Finnhub WebSocket error: %s", error)

    def _on_close(
        self,
        ws: websocket.WebSocketApp,
        close_status_code: int | None,
        close_msg: str | None,
    ) -> None:
        logger.warning(
            "Finnhub WebSocket closed (code=%s, msg=%s)",
            close_status_code,
            close_msg,
        )

    # ------------------------------------------------------------------
    # OHLCVProvider interface — not supported for tick provider
    # ------------------------------------------------------------------

    async def fetch_historical(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVCandle]:
        raise NotImplementedError(
            "Use YfinanceProvider for historical stock data; FinnhubProvider is tick-only"
        )

    async def fetch_latest(
        self,
        symbol: str,
        interval: str,
    ) -> list[OHLCVCandle]:
        raise NotImplementedError(
            "Use YfinanceProvider for historical stock data; FinnhubProvider is tick-only"
        )
