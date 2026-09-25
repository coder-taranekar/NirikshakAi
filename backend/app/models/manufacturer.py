"""
Manufacturer model and cross-state violation registry.

This is the core differentiator: tracks violations nationally so the
correct penalty tier (first / second / subsequent) is always calculated
regardless of which state the offence occurred in.
"""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class PenaltyTier(str, enum.Enum):
    FIRST = "first"
    SECOND = "second"
    SUBSEQUENT = "subsequent"


class Manufacturer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Represents a manufacturer, packer, or importer of packaged commodities.

    The registration_number maps to the Legal Metrology registration
    required under Rule 27 of the Packaged Commodities Rules, 2011.

    states_operating is stored as a PostgreSQL text array listing all
    Indian states where this entity operates — used for cross-state reporting.
    """

    __tablename__ = "manufacturers"

    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    registered_address: Mapped[str] = mapped_column(Text, nullable=False)

    # Legal Metrology registration number (Rule 27)
    registration_number: Mapped[str] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )

    # Array of state names where this manufacturer operates
    states_operating: Mapped[list] = mapped_column(
        ARRAY(String(100)), nullable=True, default=list
    )

    # Contact info
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────
    products: Mapped[list["Product"]] = relationship(  # noqa: F821
        "Product",
        back_populates="manufacturer",
        lazy="dynamic",
    )
    violations: Mapped[list["ViolationRecord"]] = relationship(
        "ViolationRecord",
        back_populates="manufacturer",
        lazy="dynamic",
        order_by="ViolationRecord.created_at",
    )

    @property
    def total_violation_count(self) -> int:
        return self.violations.count()

    def __repr__(self) -> str:
        return f"<Manufacturer id={self.id} name={self.name}>"


class ViolationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Records a single compliance violation against a manufacturer.

    Stored separately from Inspection so we can:
      1. Query all violations for a manufacturer across all states
      2. Determine the correct penalty tier nationally
      3. Build the cross-state offender leaderboard

    penalty_tier is calculated at the time of recording based on
    the manufacturer's existing violation count across all states.
    """

    __tablename__ = "violation_records"

    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manufacturers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
    )

    # State where this specific offence was detected
    state: Mapped[str] = mapped_column(String(100), nullable=False)

    # Type of violation (e.g. "missing_mrp", "wrong_font_size", "missing_manufacturer_address")
    offence_type: Mapped[str] = mapped_column(String(255), nullable=False)

    # Penalty tier at the time this violation was recorded
    penalty_tier: Mapped[PenaltyTier] = mapped_column(
        Enum(PenaltyTier, name="penalty_tier"),
        nullable=False,
    )

    # Human-readable description referencing the rule
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────
    manufacturer: Mapped["Manufacturer"] = relationship(
        "Manufacturer",
        back_populates="violations",
    )
    inspection: Mapped["Inspection"] = relationship(  # noqa: F821
        "Inspection",
        back_populates="violation_records",
    )

    def __repr__(self) -> str:
        return (
            f"<ViolationRecord id={self.id} "
            f"manufacturer={self.manufacturer_id} "
            f"tier={self.penalty_tier}>"
        )
