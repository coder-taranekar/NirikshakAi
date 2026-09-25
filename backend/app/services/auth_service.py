"""
Auth service — password hashing and JWT encode/decode utilities.

Two token types:
  - access  : short-lived (default 60 min), used for API calls
  - refresh : long-lived (default 7 days), used only to obtain a new access token

Token payload structure:
  {
    "sub"  : "<user_id as str>",
    "type" : "access" | "refresh",
    "exp"  : <unix timestamp>
  }
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ── Password Hashing ───────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored *hashed* password."""
    return _pwd_context.verify(plain, hashed)


# ── JWT ────────────────────────────────────────────────────────────────────────

TokenType = Literal["access", "refresh"]


def _create_token(user_id: str, token_type: TokenType, expires_delta: timedelta) -> str:
    """Internal helper — build and sign a JWT."""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str) -> str:
    """Create a short-lived access token for *user_id*."""
    delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    return _create_token(user_id, "access", delta)


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token for *user_id*."""
    delta = timedelta(days=settings.jwt_refresh_token_expire_days)
    return _create_token(user_id, "refresh", delta)


def decode_token(token: str, expected_type: TokenType) -> str:
    """
    Decode and validate *token*.

    Returns the user_id (``sub`` claim) on success.
    Raises ``ValueError`` with a human-readable message on any failure:
      - expired token
      - wrong token type (e.g. refresh token used where access is expected)
      - invalid signature / malformed token
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc

    if payload.get("type") != expected_type:
        raise ValueError(
            f"Wrong token type: expected '{expected_type}', got '{payload.get('type')}'"
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise ValueError("Token is missing 'sub' claim")

    return user_id
