"""
Inspections router — end-to-end scan pipeline, history, and report downloads.

Endpoints:
  POST /inspections              — image upload scan (camera/upload)
  POST /inspections/url-scan     — e-commerce URL scan (delegates to url_scanner)
  GET  /inspections              — paginated list with filters
  GET  /inspections/{id}         — full inspection detail (OCR + compliance + penalty)
  PATCH /inspections/{id}/notes  — add/update inspector notes
  GET  /inspections/{id}/report  — download PDF/Excel/DOCX report
"""

import uuid
from typing import Annotated

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inspection import Inspection
from app.models.user import User
from app.routers.deps import get_current_user, require_inspector
from app.schemas.inspection import (
    InspectionCreateRequest,
    InspectionDetailResponse,
    InspectionListResponse,
    InspectionResponse,
    UrlScanRequest,
)
from app.services.inspection_service import (
    list_inspections,
    run_inspection_pipeline,
    run_url_inspection_pipeline,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/inspections", tags=["Inspections"])

# Maximum image upload size (10 MB)
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


# ── POST /inspections ──────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=InspectionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a label image for compliance inspection",
)
async def create_inspection(
    file: UploadFile = File(..., description="Label image (JPEG or PNG, max 10 MB)"),
    source: str = Form(default="upload"),
    state: str | None = Form(default=None),
    district: str | None = Form(default=None),
    product_id: str | None = Form(default=None),
    inspector_notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspector),
) -> InspectionDetailResponse:
    """
    Upload a label image and run the full compliance pipeline:
      OCR → Rule 6 checks → Advanced checks → Penalty calculation →
      Annotated image → Persist to database

    Returns the complete inspection result including compliance score,
    per-field declaration results, and estimated penalty.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image type. Upload JPEG, PNG, or WebP.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds 10 MB limit.",
        )

    from app.models.inspection import InspectionSource
    try:
        src = InspectionSource(source)
    except ValueError:
        src = InspectionSource.UPLOAD

    pid: uuid.UUID | None = None
    if product_id:
        try:
            pid = uuid.UUID(product_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid product_id UUID: '{product_id}'",
            )

    meta = InspectionCreateRequest(
        source=src,
        state=state,
        district=district,
        product_id=pid,
        inspector_notes=inspector_notes,
    )

    inspection = run_inspection_pipeline(
        db,
        image_bytes,
        meta,
        inspector_id=current_user.id,
        filename=file.filename or "label.jpg",
    )

    logger.info(
        "inspection_created",
        inspection_id=str(inspection.id),
        score=inspection.score,
        status=inspection.status,
        by=str(current_user.id),
    )
    return InspectionDetailResponse.model_validate(inspection)


# ── POST /inspections/url-scan — before /{id} ──────────────────────────────────

@router.post(
    "/url-scan",
    response_model=InspectionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Scan a product listing URL for compliance",
)
async def url_scan(
    body: UrlScanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspector),
) -> InspectionDetailResponse:
    """
    Fetch a product image from an e-commerce URL (Amazon/Flipkart) and run
    the full compliance pipeline on it.
    """
    from app.services.url_scanner import fetch_product_image_from_url

    image_bytes = await fetch_product_image_from_url(body.source_url)
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not extract a product image from the provided URL. "
                "Ensure the URL is a valid Amazon or Flipkart product listing."
            ),
        )

    inspection = run_url_inspection_pipeline(
        db,
        image_bytes=image_bytes,
        source_url=body.source_url,
        state=body.state,
        district=body.district,
        product_id=body.product_id,
        inspector_id=current_user.id,
    )

    logger.info(
        "url_inspection_created",
        inspection_id=str(inspection.id),
        url=body.source_url,
        score=inspection.score,
        by=str(current_user.id),
    )
    return InspectionDetailResponse.model_validate(inspection)


# ── GET /inspections ───────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=InspectionListResponse,
    summary="List inspections with filters",
)
def list_all(
    product_id: uuid.UUID | None = Query(None),
    inspector_id: uuid.UUID | None = Query(None),
    state: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    score_min: float | None = Query(None, ge=0, le=100),
    score_max: float | None = Query(None, ge=0, le=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspector),
) -> InspectionListResponse:
    """
    Paginated inspection history. Inspectors see only their own inspections
    unless they are an admin.
    """
    from app.models.user import UserRole

    # Inspectors can only see their own inspections
    effective_inspector_id = inspector_id
    if current_user.role != UserRole.ADMIN:
        effective_inspector_id = current_user.id

    total, items = list_inspections(
        db,
        inspector_id=effective_inspector_id,
        product_id=product_id,
        state=state,
        status=status_filter,
        score_min=score_min,
        score_max=score_max,
        page=page,
        page_size=page_size,
    )

    return InspectionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[InspectionResponse.model_validate(i) for i in items],
    )


# ── GET /inspections/{id} ──────────────────────────────────────────────────────

@router.get(
    "/{inspection_id}",
    response_model=InspectionDetailResponse,
    summary="Get full inspection detail",
)
def get_detail(
    inspection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspector),
) -> InspectionDetailResponse:
    """
    Return full inspection record including OCR result and compliance result.
    Inspectors can only access their own inspections; admins can access any.
    """
    from app.models.user import UserRole

    inspection: Inspection | None = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found",
        )

    if (
        current_user.role != UserRole.ADMIN
        and inspection.inspector_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return InspectionDetailResponse.model_validate(inspection)


# ── PATCH /inspections/{id}/notes ──────────────────────────────────────────────

@router.patch(
    "/{inspection_id}/notes",
    response_model=InspectionResponse,
    summary="Update inspector notes on an inspection",
)
def update_notes(
    inspection_id: uuid.UUID,
    notes: str = Form(..., description="Inspector notes to attach"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspector),
) -> InspectionResponse:
    """Update or replace the inspector_notes field on an existing inspection."""
    from app.models.user import UserRole

    inspection: Inspection | None = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found",
        )

    if (
        current_user.role != UserRole.ADMIN
        and inspection.inspector_id != current_user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    inspection.inspector_notes = notes
    db.commit()
    db.refresh(inspection)
    return InspectionResponse.model_validate(inspection)


# ── GET /inspections/{id}/report ───────────────────────────────────────────────

@router.get(
    "/{inspection_id}/report",
    summary="Download compliance report (PDF, Excel, or DOCX)",
)
def download_report(
    inspection_id: uuid.UUID,
    fmt: str = Query("pdf", alias="format", description="Report format: pdf | xlsx | docx"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspector),
) -> Response:
    """
    Generate and stream a compliance report for the given inspection.
    Supported formats: pdf, xlsx, docx.
    """
    from app.models.user import UserRole
    from app.services.report_service import generate_report

    inspection: Inspection | None = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found",
        )

    if (
        current_user.role != UserRole.ADMIN
        and inspection.inspector_id != current_user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    fmt = fmt.lower()
    if fmt not in ("pdf", "xlsx", "docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Use: pdf, xlsx, or docx",
        )

    report_bytes, content_type, filename = generate_report(inspection, fmt)

    return Response(
        content=report_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
