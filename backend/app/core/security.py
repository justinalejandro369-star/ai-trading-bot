"""
Security utilities: Argon2 password hashing and JWT token creation/decoding.

Exports:
  hash_password, verify_password, create_access_token, decode_access_token
"""
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
]

pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return Argon2 hash of plain-text password."""
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain-text password against Argon2 hash."""
    return pwd_ctx.verify(plain, hashed)


def create_access_token(data: dict, expires_minutes: int = 30) -> str:
    """
    Encode a JWT token with an expiry.

    Args:
        data: Payload dict (must include 'sub' key).
        expires_minutes: Token TTL in minutes.

    Returns:
        Signed JWT string.
    """
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Raises:
        jwt.PyJWTError: If token is invalid, expired, or tampered.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
