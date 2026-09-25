"""
FastAPI dependencies for authentication and role-based access control.

Usage in a router:
    # Any authenticated user
    current_user: User = Depends(get_current_user)

    # Admin only
    current_user: User = Depends(require_admin)

    # Inspector or Admin
    current_user: User = Depends(require_inspector)
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import decode_token

# ── Bearer token extractor ─────────────────────────────────────────────────────
# auto_error=False so we can return a clean 401 instead of FastAPI's default 403
_bearer = HTTPBearer(auto_error=False)


# ── Core dependency ────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate the Bearer access token.
    Returns the authenticated User ORM object.

    Raises HTTP 401 for:
      - Missing / malformed Authorization header
      - Expired or invalid token
      - User not found or deactivated
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = decode_token(credentials.credentials, expected_type="access")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: User | None = db.get(User, uid)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ── Role guards ────────────────────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that restricts a route to admin users only.
    Raises HTTP 403 for authenticated non-admin users.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_inspector(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that allows both inspectors and admins.
    (All authenticated active users pass this check.)
    Kept as a named dependency for explicitness in route signatures.
    """
    return current_user
