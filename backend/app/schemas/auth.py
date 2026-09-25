"""
Pydantic schemas for authentication and user management.

Covers:
  - Login request / token responses
  - Current user profile response
  - User creation (admin-only registration)
  - User update (admin: deactivate, change role)
  - Paginated user list
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


# ── Login ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Credentials submitted to POST /auth/login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """JWT token pair returned on successful login or token refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    """New access token returned by POST /auth/refresh."""

    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh token submitted to POST /auth/refresh."""

    refresh_token: str


# ── User Profile ───────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """User profile returned from GET /auth/me and user list endpoints."""

    id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole
    state: Optional[str] = None
    district: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── User Creation (Admin only) ─────────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    """
    Body for POST /auth/register (admin-only).
    Creates a new inspector or admin account.
    """

    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="Minimum 8 characters",
    )
    role: UserRole = UserRole.INSPECTOR
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)


# ── User Update (Admin only) ───────────────────────────────────────────────────

class UserUpdateRequest(BaseModel):
    """
    Body for PATCH /users/{id} (admin-only).
    All fields are optional — only provided fields are updated.
    """

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    role: Optional[UserRole] = None
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


# ── User List ──────────────────────────────────────────────────────────────────

class UserListResponse(BaseModel):
    """Paginated list of users returned from GET /users."""

    total: int
    page: int
    page_size: int
    items: list[UserResponse]
