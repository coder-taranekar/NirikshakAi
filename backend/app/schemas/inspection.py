"""
Pydantic schemas for inspections.

Covers:
  - Inspection create (image upload or URL)
  - Inspection response (summary and full detail)
  - Paginated list
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.inspection import InspectionSource, InspectionStatus


# ── Create ─────────────────────────────────────────────────────────────────────

class InspectionCreateRequest(BaseModel):
    """
    Metadata submitted alongside the image upload for POST /inspections.
    The actual image file is received as a separate UploadFile parameter.
    """

    source: InspectionSource = InspectionSource.UPLOAD
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    product_id: Optional[uuid.UUID] = None
    inspector_notes: Optional[str] = None


class UrlScanRequest(BaseModel):
    """Body for POST /inspections/url-scan."""

    source_url: str = Field(..., min_length=10, max_length=2000)
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    product_id: Optional[uuid.UUID] = None


# ── Response ───────────────────────────────────────────────────────────────────

class InspectionResponse(BaseModel):
    """Summary inspection record — used in list responses."""

    id: uuid.UUID
    source: InspectionSource
    source_url: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    image_url: Optional[str] = None
    annotated_image_url: Optional[str] = None
    score: Optional[float] = None
    status: InspectionStatus
    hard_fail_triggered: bool
    penalty_tier: Optional[str] = None
    estimated_penalty_min: Optional[int] = None
    estimated_penalty_max: Optional[int] = None
    product_id: Optional[uuid.UUID] = None
    inspector_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InspectionDetailResponse(InspectionResponse):
    """
    Full inspection record — returned by GET /inspections/{id}.
    Includes raw OCR output and full compliance result.
    """

    ocr_result: Optional[dict[str, Any]] = None
    compliance_result: Optional[dict[str, Any]] = None
    inspector_notes: Optional[str] = None


# ── List ───────────────────────────────────────────────────────────────────────

class InspectionListResponse(BaseModel):
    """Paginated inspection list."""

    total: int
    page: int
    page_size: int
    items: list[InspectionResponse]
