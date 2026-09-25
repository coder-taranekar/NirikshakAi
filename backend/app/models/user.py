"""
User model — field inspectors and admin officials.
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    INSPECTOR = "inspector"
    ADMIN = "admin"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Represents a system user — either a field inspector or an admin official.

    Field inspectors:
      - Scan product labels in the field (mobile app)
      - View their own inspection history
      - Download reports for their own inspections

    Admins:
      - Full access to all inspections, reports, and dashboards
      - Manage users, products, and manufacturers
      - View cross-state violation analytics
    """

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.INSPECTOR,
    )

    # Geographic context for the inspector (used in cross-state tracking)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────
    inspections: Mapped[list["Inspection"]] = relationship(  # noqa: F821
        "Inspection",
        back_populates="inspector",
        lazy="dynamic",
    )
    registered_products: Mapped[list["Product"]] = relationship(  # noqa: F821
        "Product",
        back_populates="registered_by_user",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
