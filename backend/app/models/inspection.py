"""
Inspection model — the core record of a compliance check event.

Every time an inspector scans a label (via camera, image upload, or URL),
an Inspection record is created. It stores:
  - The original and annotated images (MinIO URLs)
  - Raw OCR output (JSON)
  - Full compliance result (JSON) — per-field results, score, violations
  - Overall status and penalty assessment
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class InspectionStatus(str, enum.Enum):
    PENDING = "pending"           # OCR/compliance still processing
    COMPLIANT = "compliant"       # All checks passed, score >= 90
    PARTIAL = "partial"           # Score 50–89, no hard fails
    NON_COMPLIANT = "non_compliant"  # Hard fail triggered OR score < 50


class InspectionSource(str, enum.Enum):
    CAMERA = "camera"             # Mobile camera scan
    UPLOAD = "upload"             # Image file upload (web or mobile gallery)
    URL = "url"                   # E-commerce URL scan


class Inspection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single compliance inspection event.

    ocr_result JSON structure:
    {
      "raw_text": "...",
      "blocks": [
        {
          "text": "MRP ₹45.00",
          "bounding_box": {"x": 10, "y": 200, "width": 80, "height": 12},
          "confidence": 0.98,
          "estimated_font_height_mm": 2.3
        }
      ],
      "image_dpi": 150,
      "image_width_px": 1200,
      "image_height_px": 800
    }

    compliance_result JSON structure:
    {
      "overall_score": 72,
      "status": "non_compliant",
      "hard_fail_triggered": true,
      "declarations": [ { field, status, extracted_value, rule_reference, ... } ],
      "advanced_checks": { font_size_violations, whitespace_violations, ... },
      "penalty": { tier, applicable_section, estimated_range, note }
    }
    """

    __tablename__ = "inspections"

    # ── Source ────────────────────────────────────────────────────────
    source: Mapped[InspectionSource] = mapped_column(
        Enum(InspectionSource, name="inspection_source"),
        nullable=False,
        default=InspectionSource.UPLOAD,
    )
    # Only populated for URL scans
    source_url: Mapped[str] = mapped_column(String(2000), nullable=True)

    # Geographic context — used for cross-state violation tracking
    state: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=True)

    # ── Images ────────────────────────────────────────────────────────
    # MinIO object URLs
    image_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    annotated_image_url: Mapped[str] = mapped_column(String(1000), nullable=True)

    # ── OCR Output ────────────────────────────────────────────────────
    ocr_result: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # ── Compliance Result ─────────────────────────────────────────────
    compliance_result: Mapped[dict] = mapped_column(JSONB, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[InspectionStatus] = mapped_column(
        Enum(InspectionStatus, name="inspection_status"),
        nullable=False,
        default=InspectionStatus.PENDING,
        index=True,
    )
    hard_fail_triggered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # ── Penalty Assessment ────────────────────────────────────────────
    penalty_tier: Mapped[str] = mapped_column(String(50), nullable=True)
    estimated_penalty_min: Mapped[int] = mapped_column(Integer, nullable=True)
    estimated_penalty_max: Mapped[int] = mapped_column(Integer, nullable=True)

    # Inspector notes (added via DOCX report or dashboard)
    inspector_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # ── Foreign Keys ──────────────────────────────────────────────────
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    inspector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────────
    product: Mapped["Product"] = relationship(  # noqa: F821
        "Product",
        back_populates="inspections",
    )
    inspector: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="inspections",
    )
    violation_records: Mapped[list["ViolationRecord"]] = relationship(  # noqa: F821
        "ViolationRecord",
        back_populates="inspection",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return (
            f"<Inspection id={self.id} "
            f"status={self.status} "
            f"score={self.score}>"
        )
