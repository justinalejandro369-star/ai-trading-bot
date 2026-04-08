"""Send alert messages via Discord webhook."""
import logging

import httpx

from app.core.config import settings

__all__ = ["send_discord"]

log = logging.getLogger(__name__)


async def send_discord(message: str) -> bool:
    """POST message to Discord webhook. Returns True on success."""
    webhook_url = settings.discord_webhook_url
    if not webhook_url:
        log.debug("send_discord: DISCORD_WEBHOOK_URL not set, skipping")
        return False
    payload = {"content": message, "username": "TradingBot"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        log.error("send_discord: failed: %s", exc)
        return False
