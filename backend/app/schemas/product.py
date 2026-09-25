"""
Pydantic schemas for the product catalog.

Covers:
  - Product create / update / response
  - Product detail response (with inspection summary)
  - Paginated product list
  - Bulk CSV import result
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Product Schemas ────────────────────────────────────────────────────────────

class ProductCreateRequest(BaseModel):
    """Body for POST /products."""

    name: str = Field(..., min_length=2, max_length=500)
    generic_name: str = Field(..., min_length=2, max_length=255)
    brand: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=255)
    barcode: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=1000)
    is_schedule_ii_commodity: bool = False
    standard_pack_sizes: list[str] = Field(default_factory=list)
    extra_metadata: Optional[dict[str, Any]] = None
    manufacturer_id: Optional[uuid.UUID] = None


class ProductUpdateRequest(BaseModel):
    """
    Body for PATCH /products/{id}.
    All fields optional — only provided fields are updated.
    """

    name: Optional[str] = Field(None, min_length=2, max_length=500)
    generic_name: Optional[str] = Field(None, min_length=2, max_length=255)
    brand: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=255)
    barcode: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=1000)
    is_schedule_ii_commodity: Optional[bool] = None
    standard_pack_sizes: Optional[list[str]] = None
    extra_metadata: Optional[dict[str, Any]] = None
    manufacturer_id: Optional[uuid.UUID] = None


class ProductResponse(BaseModel):
    """Product summary — used in list responses."""

    id: uuid.UUID
    name: str
    generic_name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    is_schedule_ii_commodity: bool
    standard_pack_sizes: list[str] = []
    manufacturer_id: Optional[uuid.UUID] = None
    registered_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductResponse):
    """
    Full product profile — returned by GET /products/{id}.
    Adds recent inspection summary stats.
    """

    total_inspections: int = 0
    last_inspection_status: Optional[str] = None
    last_inspection_score: Optional[float] = None


# ── List ───────────────────────────────────────────────────────────────────────

class ProductListResponse(BaseModel):
    """Paginated product list."""

    total: int
    page: int
    page_size: int
    items: list[ProductResponse]


# ── Bulk Import ────────────────────────────────────────────────────────────────

class ProductBulkImportResult(BaseModel):
    """Result of POST /products/bulk-import."""

    total_rows: int
    created: int
    skipped: int
    errors: list[str] = []
