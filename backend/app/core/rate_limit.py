"""
Shared slowapi rate limiter singleton.

Import this in both app/main.py and auth routes to ensure
there is a single limiter instance whose storage can be reset in tests.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

__all__ = ["limiter"]

limiter = Limiter(key_func=get_remote_address)
