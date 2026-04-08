"""Send alert messages via Telegram Bot API."""
import logging

import httpx

from app.core.config import settings

__all__ = ["send_telegram"]

log = logging.getLogger(__name__)


async def send_telegram(message: str) -> bool:
    """POST message to Telegram Bot API. Returns True on success."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if not token or not chat_id:
        log.debug("send_telegram: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set, skipping")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        log.error("send_telegram: failed: %s", exc)
        return False
