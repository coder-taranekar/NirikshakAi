"""
Products router — catalog CRUD, barcode search, and bulk CSV import.

Endpoints:
  POST   /products               — create product (any authenticated user)
  GET    /products               — paginated list with filters
  GET    /products/barcode/{code} — lookup by barcode
  GET    /products/{id}          — full detail with inspection summary
  PATCH  /products/{id}          — partial update (admin)
  DELETE /products/{id}          — delete (admin)
  POST   /products/bulk-import   — CSV upload (admin)
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.deps import get_current_user, require_admin, require_inspector
from app.schemas.product import (
    ProductBulkImportResult,
    ProductCreateRequest,
    ProductDetailResponse,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
)
from app.services.product_service import (
    bulk_import_products,
    create_product,
    delete_product,
    get_product_by_barcode,
    get_product_detail,
    list_products,
    update_product,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])


# ── POST /products ─────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
def create(
    body: ProductCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductResponse:
    """Register a new product in the catalog. Open to all authenticated users."""
    try:
        product = create_product(db, body, registered_by_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    logger.info("product_created", product_id=str(product.id), by=str(current_user.id))
    return ProductResponse.model_validate(product)


# ── POST /products/bulk-import — must be before /{id} ─────────────────────────

@router.post(
    "/bulk-import",
    response_model=ProductBulkImportResult,
    summary="Bulk import products from CSV (admin only)",
)
async def bulk_import(
    file: UploadFile = File(
        ...,
        description=(
            "UTF-8 CSV. Required columns: name, generic_name. "
            "Optional: brand, category, barcode, is_schedule_ii_commodity, "
            "standard_pack_sizes (pipe-separated), manufacturer_id (UUID)."
        ),
    ),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ProductBulkImportResult:
    """Bulk-create products from a CSV file. Duplicate barcodes are skipped."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a .csv file",
        )
    csv_bytes = await file.read()
    result = bulk_import_products(db, csv_bytes, registered_by_user_id=admin.id)
    logger.info(
        "products_bulk_imported",
        created=result.created,
        skipped=result.skipped,
        by=str(admin.id),
    )
    return result


# ── GET /products/barcode/{code} — must be before /{id} ───────────────────────

@router.get(
    "/barcode/{barcode}",
    response_model=ProductResponse,
    summary="Lookup product by barcode",
)
def get_by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_inspector),
) -> ProductResponse:
    """Find a product by its barcode (EAN-13, UPC, QR value, etc.)."""
    product = get_product_by_barcode(db, barcode)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No product found with barcode '{barcode}'",
        )
    return ProductResponse.model_validate(product)


# ── GET /products ──────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products",
)
def list_all(
    search: str | None = Query(None, description="Search name, generic name, brand, barcode"),
    category: str | None = Query(None),
    brand: str | None = Query(None),
    is_schedule_ii: bool | None = Query(None, description="Filter Schedule II commodities"),
    manufacturer_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_inspector),
) -> ProductListResponse:
    """Return a paginated, filterable list of products."""
    return list_products(
        db,
        search=search,
        category=category,
        brand=brand,
        is_schedule_ii=is_schedule_ii,
        manufacturer_id=manufacturer_id,
        page=page,
        page_size=page_size,
    )


# ── GET /products/{id} ─────────────────────────────────────────────────────────

@router.get(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get product detail with inspection summary",
)
def get_detail(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_inspector),
) -> ProductDetailResponse:
    """Return a product's full profile plus a summary of its inspection history."""
    detail = get_product_detail(db, product_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found",
        )
    return detail


# ── PATCH /products/{id} ───────────────────────────────────────────────────────

@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product (admin only)",
)
def update(
    product_id: uuid.UUID,
    body: ProductUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ProductResponse:
    """Partially update a product. Only supplied fields are changed."""
    try:
        product = update_product(db, product_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found",
        )
    logger.info("product_updated", product_id=str(product_id), by=str(admin.id))
    return ProductResponse.model_validate(product)


# ── DELETE /products/{id} ──────────────────────────────────────────────────────

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product (admin only)",
)
def delete(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    """Delete a product. Associated inspections will have product_id set to NULL."""
    if not delete_product(db, product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found",
        )
    logger.info("product_deleted", product_id=str(product_id), by=str(admin.id))
