"""
WebSocket endpoint: /ws/live

Broadcasts real-time price ticks and signal updates to all connected clients.
Scheduler jobs call manager.broadcast() after each market scan.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

__all__ = ["router", "manager"]

log = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self) -> None:
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)
        log.info("WS client connected. Active: %d", len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)
        log.info("WS client disconnected. Active: %d", len(self.active))

    async def broadcast(self, data: dict) -> None:
        """Send JSON data to all connected clients; remove dead connections."""
        message = json.dumps(data)
        dead: set[WebSocket] = set()
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active.discard(ws)


# Module-level singleton — imported by scheduler jobs
manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket) -> None:
    """
    Live WebSocket endpoint for real-time price ticks and signal updates.

    Sends a keepalive ping every 30 seconds to maintain connection.
    Scheduler jobs call manager.broadcast() to push updates.
    """
    await manager.connect(ws)
    try:
        while True:
            await asyncio.sleep(30)
            await manager.broadcast({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
