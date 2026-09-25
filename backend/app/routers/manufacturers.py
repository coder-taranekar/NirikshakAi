"""
Manufacturers router — CRUD endpoints for the manufacturer registry,
including the cross-state violation history and bulk CSV import.

Endpoints:
  POST  /manufacturers                — create a manufacturer (admin)
  GET   /manufacturers                — paginated list with optional search
  GET   /manufacturers/{id}           — full detail with violation history + offence tier
  PATCH /manufacturers/{id}           — partial update (admin)
  DELETE /manufacturers/{id}          — delete manufacturer (admin)
  POST  /manufacturers/bulk-import    — CSV upload (admin)
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.deps import require_admin, require_inspector
from app.schemas.manufacturer import (
    BulkImportResult,
    ManufacturerCreateRequest,
    ManufacturerDetailResponse,
    ManufacturerListResponse,
    ManufacturerResponse,
    ManufacturerUpdateRequest,
)
from app.services.manufacturer_service import (
    bulk_import_manufacturers,
    create_manufacturer,
    delete_manufacturer,
    get_manufacturer_detail,
    list_manufacturers,
    update_manufacturer,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/manufacturers", tags=["Manufacturers"])


# ── POST /manufacturers ────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ManufacturerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manufacturer (admin only)",
)
def create(
    body: ManufacturerCreateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ManufacturerResponse:
    """
    Register a new manufacturer in the national registry.
    Returns 409 if the registration_number is already in use.
    """
    try:
        manufacturer = create_manufacturer(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    logger.info(
        "manufacturer_created",
        manufacturer_id=str(manufacturer.id),
        name=manufacturer.name,
        created_by=str(_admin.id),
    )
    return ManufacturerResponse.model_validate(manufacturer)


# ── GET /manufacturers ─────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ManufacturerListResponse,
    summary="List manufacturers",
)
def list_all(
    search: str | None = Query(None, description="Search by name or registration number"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_inspector),
) -> ManufacturerListResponse:
    """
    Return a paginated list of manufacturers.
    Optionally filter by name or registration number (case-insensitive partial match).
    Accessible to all authenticated users (inspectors and admins).
    """
    return list_manufacturers(db, search=search, page=page, page_size=page_size)


# ── POST /manufacturers/bulk-import ───────────────────────────────────────────
# NOTE: must be registered BEFORE /{manufacturer_id} so FastAPI doesn't try to
# parse the literal string "bulk-import" as a UUID path parameter.

@router.post(
    "/bulk-import",
    response_model=BulkImportResult,
    summary="Bulk import manufacturers from CSV (admin only)",
)
async def bulk_import(
    file: UploadFile = File(
        ...,
        description=(
            "UTF-8 CSV file. Required columns: name, registered_address. "
            "Optional: registration_number, states_operating (pipe-separated), "
            "contact_phone, contact_email."
        ),
    ),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> BulkImportResult:
    """
    Upload a CSV file to bulk-register manufacturers.

    - Rows with a duplicate registration_number are skipped (not overwritten).
    - Rows missing required fields are skipped and reported in `errors`.
    - All valid rows are committed in a single transaction.

    CSV format example:
    ```
    name,registered_address,registration_number,states_operating,contact_phone,contact_email
    Amul Dairy,Anand Gujarat,LM-GJ-001,Gujarat|Maharashtra,02692-258506,info@amul.com
    ```
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a .csv file",
        )

    csv_bytes = await file.read()
    result = bulk_import_manufacturers(db, csv_bytes)

    logger.info(
        "manufacturers_bulk_imported",
        total_rows=result.total_rows,
        created=result.created,
        skipped=result.skipped,
        imported_by=str(admin.id),
    )
    return result


# ── GET /manufacturers/{id} ────────────────────────────────────────────────────

@router.get(
    "/{manufacturer_id}",
    response_model=ManufacturerDetailResponse,
    summary="Get manufacturer detail with violation history",
)
def get_detail(
    manufacturer_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_inspector),
) -> ManufacturerDetailResponse:
    """
    Return the full manufacturer profile, including:
      - Complete cross-state violation history (newest first)
      - Computed next-offence penalty tier
    """
    detail = get_manufacturer_detail(db, manufacturer_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer '{manufacturer_id}' not found",
        )
    return detail


# ── PATCH /manufacturers/{id} ──────────────────────────────────────────────────

@router.patch(
    "/{manufacturer_id}",
    response_model=ManufacturerResponse,
    summary="Update a manufacturer (admin only)",
)
def update(
    manufacturer_id: uuid.UUID,
    body: ManufacturerUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ManufacturerResponse:
    """
    Partially update a manufacturer record.
    Only fields included in the request body are changed.
    Returns 409 if the new registration_number conflicts with another record.
    """
    try:
        manufacturer = update_manufacturer(db, manufacturer_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    if manufacturer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer '{manufacturer_id}' not found",
        )

    logger.info(
        "manufacturer_updated",
        manufacturer_id=str(manufacturer.id),
        updated_by=str(admin.id),
    )
    return ManufacturerResponse.model_validate(manufacturer)


# ── DELETE /manufacturers/{id} ─────────────────────────────────────────────────

@router.delete(
    "/{manufacturer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a manufacturer (admin only)",
)
def delete(
    manufacturer_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    """
    Delete a manufacturer and cascade-delete their violation records.
    Products linked to this manufacturer will have their manufacturer_id set to NULL.
    Returns 204 No Content on success.
    """
    deleted = delete_manufacturer(db, manufacturer_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manufacturer '{manufacturer_id}' not found",
        )
    logger.info(
        "manufacturer_deleted",
        manufacturer_id=str(manufacturer_id),
        deleted_by=str(admin.id),
    )
