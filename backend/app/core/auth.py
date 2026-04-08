"""
FastAPI dependency for JWT authentication via httpOnly cookies.

Exports:
  get_current_user — use as Depends(get_current_user) on protected routes
"""
import jwt
from fastapi import Depends, HTTPException, Request

from app.core.security import decode_access_token

__all__ = ["get_current_user"]


async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency that reads the access_token httpOnly cookie and
    returns the decoded JWT payload.

    Raises:
        HTTPException(401): If cookie is missing or token is invalid/expired.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload
