"""
Users router — admin-only user management.

Endpoints:
  GET   /users        — paginated list of all users (admin only)
  GET   /users/{id}   — get a single user by ID (admin only)
  PATCH /users/{id}   — update user fields: name, role, state, district, is_active (admin only)
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.deps import require_admin
from app.schemas.auth import UserListResponse, UserResponse, UserUpdateRequest

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


# ── GET /users ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=UserListResponse,
    summary="List all users (admin only)",
)
def list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    role: str | None = Query(None, description="Filter by role: inspector | admin"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserListResponse:
    """
    Return a paginated list of all users.
    Supports optional filtering by role and active status.
    """
    query = db.query(User)

    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    offset = (page - 1) * page_size
    users = (
        query
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[UserResponse.model_validate(u) for u in users],
    )


# ── GET /users/{id} ────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a single user by ID (admin only)",
)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """Return a single user record. Raises 404 if not found."""
    user: User | None = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    return UserResponse.model_validate(user)


# ── PATCH /users/{id} ─────────────────────────────────────────────────────────

@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user (admin only)",
)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserResponse:
    """
    Partial update — only the fields present in the request body are changed.

    Supported updates:
      - name         : rename the user
      - role         : promote/demote between inspector and admin
      - state        : reassign geographic context
      - district     : reassign geographic context
      - is_active    : deactivate (false) or reactivate (true) the account

    Guards:
      - Admins cannot deactivate their own account (prevents lockout).
    """
    user: User | None = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    # Prevent self-lockout
    if body.is_active is False and user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot deactivate their own account",
        )

    # Apply only the fields that were explicitly set in the request
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    logger.info(
        "user_updated",
        target_user_id=str(user.id),
        updated_by=str(admin.id),
        fields=list(update_data.keys()),
    )

    return UserResponse.model_validate(user)
