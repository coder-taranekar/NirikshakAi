"""
Pydantic schemas for manufacturers and violation records.

Covers:
  - Manufacturer create / update / response
  - ViolationRecord response (read-only from API — records are created by the inspection pipeline)
  - Manufacturer detail response (with full violation history)
  - Paginated manufacturer list
  - Offence tier summary
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.manufacturer import PenaltyTier


# ── Violation Record ───────────────────────────────────────────────────────────

class ViolationRecordResponse(BaseModel):
    """A single violation entry in a manufacturer's cross-state registry."""

    id: uuid.UUID
    manufacturer_id: uuid.UUID
    inspection_id: uuid.UUID
    state: str
    offence_type: str
    penalty_tier: PenaltyTier
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Offence Tier Summary ───────────────────────────────────────────────────────

class OffenceTierSummary(BaseModel):
    """
    Computed national offence tier for a manufacturer.
    Returned as part of detail responses and used by the inspection pipeline.
    """

    total_violations: int
    next_tier: PenaltyTier
    states_with_violations: list[str]
    note: str


# ── Manufacturer Schemas ───────────────────────────────────────────────────────

class ManufacturerCreateRequest(BaseModel):
    """Body for POST /manufacturers."""

    name: str = Field(..., min_length=2, max_length=500)
    registered_address: str = Field(..., min_length=5)
    registration_number: Optional[str] = Field(None, max_length=100)
    states_operating: list[str] = Field(default_factory=list)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[EmailStr] = None


class ManufacturerUpdateRequest(BaseModel):
    """
    Body for PATCH /manufacturers/{id}.
    All fields optional — only provided fields are updated.
    """

    name: Optional[str] = Field(None, min_length=2, max_length=500)
    registered_address: Optional[str] = Field(None, min_length=5)
    registration_number: Optional[str] = Field(None, max_length=100)
    states_operating: Optional[list[str]] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[EmailStr] = None


class ManufacturerResponse(BaseModel):
    """Manufacturer summary — used in list responses."""

    id: uuid.UUID
    name: str
    registered_address: str
    registration_number: Optional[str] = None
    states_operating: list[str] = []
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    total_violation_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ManufacturerDetailResponse(ManufacturerResponse):
    """
    Full manufacturer profile — returned by GET /manufacturers/{id}.
    Includes full violation history and computed offence tier.
    """

    violations: list[ViolationRecordResponse] = []
    offence_tier: OffenceTierSummary


# ── List ───────────────────────────────────────────────────────────────────────

class ManufacturerListResponse(BaseModel):
    """Paginated manufacturer list."""

    total: int
    page: int
    page_size: int
    items: list[ManufacturerResponse]


# ── Bulk Import ────────────────────────────────────────────────────────────────

class BulkImportResult(BaseModel):
    """
    Result of POST /manufacturers/bulk-import.
    Reports how many records were created vs skipped due to duplicates/errors.
    """

    total_rows: int
    created: int
    skipped: int
    errors: list[str] = []
