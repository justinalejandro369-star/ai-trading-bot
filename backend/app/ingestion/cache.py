"""
In-memory TTL cache for protecting rate-limited external API calls.

This cache is designed for single-process async use only. It is NOT thread-safe
and does not require locking — appropriate for a single-worker FastAPI + asyncio process.

Usage:
    cache = TTLCache()
    cache.set("key", value, ttl_seconds=60)
    result = cache.get("key")  # returns None if expired or absent
    cache.invalidate("key")
"""
import time
from typing import Any

__all__ = ["TTLCache"]


class TTLCache:
    """
    Simple in-memory cache with per-key TTL expiration.

    Keys expire after their configured TTL (time-to-live). Expired entries are
    lazily evicted on get(). No background cleanup thread is needed for MVP.
    """

    def __init__(self) -> None:
        # Maps key -> (value, expiry_monotonic)
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        """
        Return cached value if present and not expired; else return None.

        Expired entries are removed lazily on access.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        """
        Store value with expiry = now + ttl_seconds.

        A ttl_seconds of 0 means the entry expires immediately (will be stale
        on the very next get() call after monotonic time advances).
        """
        self._store[key] = (value, time.monotonic() + ttl_seconds)

    def invalidate(self, key: str) -> None:
        """Remove a cached entry immediately, if it exists."""
        self._store.pop(key, None)
