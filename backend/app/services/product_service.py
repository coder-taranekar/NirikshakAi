"""
Product service — CRUD, search, barcode lookup, and bulk CSV import
for the packaged commodity product catalog.
"""

import csv
import io
import uuid
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.manufacturer import Manufacturer
from app.models.product import Product
from app.schemas.product import (
    ProductBulkImportResult,
    ProductCreateRequest,
    ProductDetailResponse,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_response(product: Product) -> ProductResponse:
    return ProductResponse.model_validate(product)


def _to_detail(product: Product) -> ProductDetailResponse:
    inspections = product.inspections
    total = inspections.count()
    last = inspections.order_by(None).order_by(  # type: ignore[attr-defined]
        # dynamic query — order by created_at desc
        product.inspections.property.mapper.class_.created_at.desc()
    ).first() if total > 0 else None

    base = ProductResponse.model_validate(product).model_dump()
    return ProductDetailResponse(
        **base,
        total_inspections=total,
        last_inspection_status=last.status.value if last else None,
        last_inspection_score=last.score if last else None,
    )


# ── CRUD ───────────────────────────────────────────────────────────────────────

def create_product(
    db: Session,
    body: ProductCreateRequest,
    registered_by_user_id: uuid.UUID,
) -> Product:
    """
    Create a new product.
    Raises ValueError if barcode is already registered.
    Raises ValueError if manufacturer_id is provided but not found.
    """
    if body.barcode:
        existing = db.query(Product).filter(Product.barcode == body.barcode).first()
        if existing:
            raise ValueError(
                f"Barcode '{body.barcode}' is already registered to product '{existing.name}'"
            )

    if body.manufacturer_id:
        mfr = db.get(Manufacturer, body.manufacturer_id)
        if mfr is None:
            raise ValueError(f"Manufacturer '{body.manufacturer_id}' not found")

    product = Product(
        name=body.name,
        generic_name=body.generic_name,
        brand=body.brand,
        category=body.category,
        barcode=body.barcode,
        image_url=body.image_url,
        is_schedule_ii_commodity=body.is_schedule_ii_commodity,
        standard_pack_sizes=body.standard_pack_sizes or [],
        extra_metadata=body.extra_metadata or {},
        manufacturer_id=body.manufacturer_id,
        registered_by=registered_by_user_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product_by_id(db: Session, product_id: uuid.UUID) -> Optional[Product]:
    return db.get(Product, product_id)


def get_product_by_barcode(db: Session, barcode: str) -> Optional[Product]:
    return db.query(Product).filter(Product.barcode == barcode).first()


def list_products(
    db: Session,
    search: Optional[str],
    category: Optional[str],
    brand: Optional[str],
    is_schedule_ii: Optional[bool],
    manufacturer_id: Optional[uuid.UUID],
    page: int,
    page_size: int,
) -> ProductListResponse:
    """Paginated product list with optional multi-field filtering."""
    query = db.query(Product)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(pattern),
                Product.generic_name.ilike(pattern),
                Product.brand.ilike(pattern),
                Product.barcode.ilike(pattern),
            )
        )
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    if is_schedule_ii is not None:
        query = query.filter(Product.is_schedule_ii_commodity == is_schedule_ii)
    if manufacturer_id:
        query = query.filter(Product.manufacturer_id == manufacturer_id)

    total = query.count()
    offset = (page - 1) * page_size
    products = (
        query
        .order_by(Product.name.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return ProductListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_to_response(p) for p in products],
    )


def get_product_detail(
    db: Session,
    product_id: uuid.UUID,
) -> Optional[ProductDetailResponse]:
    """Return full product profile with inspection summary."""
    product = get_product_by_id(db, product_id)
    if product is None:
        return None

    inspections_query = product.inspections
    total = inspections_query.count()

    # Fetch last inspection using the dynamic relationship
    from app.models.inspection import Inspection
    last = (
        db.query(Inspection)
        .filter(Inspection.product_id == product_id)
        .order_by(Inspection.created_at.desc())
        .first()
    )

    base = ProductResponse.model_validate(product).model_dump()
    return ProductDetailResponse(
        **base,
        total_inspections=total,
        last_inspection_status=last.status.value if last else None,
        last_inspection_score=last.score if last else None,
    )


def update_product(
    db: Session,
    product_id: uuid.UUID,
    body: ProductUpdateRequest,
) -> Optional[Product]:
    """
    Partial update.
    Returns None if not found.
    Raises ValueError on barcode conflict or invalid manufacturer_id.
    """
    product = get_product_by_id(db, product_id)
    if product is None:
        return None

    update_data = body.model_dump(exclude_unset=True)

    # Check barcode uniqueness if changing
    new_barcode = update_data.get("barcode")
    if new_barcode and new_barcode != product.barcode:
        conflict = db.query(Product).filter(
            Product.barcode == new_barcode,
            Product.id != product_id,
        ).first()
        if conflict:
            raise ValueError(
                f"Barcode '{new_barcode}' is already registered to product '{conflict.name}'"
            )

    # Validate manufacturer if changing
    new_mfr_id = update_data.get("manufacturer_id")
    if new_mfr_id and new_mfr_id != product.manufacturer_id:
        if db.get(Manufacturer, new_mfr_id) is None:
            raise ValueError(f"Manufacturer '{new_mfr_id}' not found")

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: uuid.UUID) -> bool:
    """Delete a product. Returns True if deleted, False if not found."""
    product = get_product_by_id(db, product_id)
    if product is None:
        return False
    db.delete(product)
    db.commit()
    return True


# ── Bulk CSV Import ────────────────────────────────────────────────────────────
# Required columns: name, generic_name
# Optional: brand, category, barcode, is_schedule_ii_commodity,
#            standard_pack_sizes (pipe-separated), manufacturer_id

_REQUIRED_CSV_COLUMNS = {"name", "generic_name"}


def bulk_import_products(
    db: Session,
    csv_bytes: bytes,
    registered_by_user_id: uuid.UUID,
) -> ProductBulkImportResult:
    """
    Parse a UTF-8 CSV and insert product records.
    Rows with duplicate barcodes or invalid manufacturer_ids are skipped.
    """
    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ProductBulkImportResult(
            total_rows=0, created=0, skipped=0,
            errors=["File is not valid UTF-8."],
        )

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return ProductBulkImportResult(
            total_rows=0, created=0, skipped=0,
            errors=["CSV file is empty or has no header row."],
        )

    headers = {h.strip().lower() for h in reader.fieldnames}
    missing = _REQUIRED_CSV_COLUMNS - headers
    if missing:
        return ProductBulkImportResult(
            total_rows=0, created=0, skipped=0,
            errors=[f"Missing required columns: {', '.join(sorted(missing))}"],
        )

    rows = list(reader)
    total_rows = len(rows)
    created = skipped = 0
    errors: list[str] = []

    for row_num, raw_row in enumerate(rows, start=2):
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items()}

        name = row.get("name", "")
        generic_name = row.get("generic_name", "")

        if not name:
            errors.append(f"Row {row_num}: 'name' is required — skipped.")
            skipped += 1
            continue
        if not generic_name:
            errors.append(f"Row {row_num}: 'generic_name' is required — skipped.")
            skipped += 1
            continue

        barcode = row.get("barcode") or None
        if barcode:
            if db.query(Product).filter(Product.barcode == barcode).first():
                errors.append(f"Row {row_num}: barcode '{barcode}' already exists — skipped.")
                skipped += 1
                continue

        # Parse manufacturer_id
        mfr_id_str = row.get("manufacturer_id") or None
        manufacturer_id: Optional[uuid.UUID] = None
        if mfr_id_str:
            try:
                manufacturer_id = uuid.UUID(mfr_id_str)
                if db.get(Manufacturer, manufacturer_id) is None:
                    errors.append(
                        f"Row {row_num}: manufacturer_id '{mfr_id_str}' not found — skipped."
                    )
                    skipped += 1
                    continue
            except ValueError:
                errors.append(
                    f"Row {row_num}: manufacturer_id '{mfr_id_str}' is not a valid UUID — skipped."
                )
                skipped += 1
                continue

        # Parse standard_pack_sizes (pipe-separated)
        sizes_raw = row.get("standard_pack_sizes", "")
        standard_pack_sizes = (
            [s.strip() for s in sizes_raw.split("|") if s.strip()] if sizes_raw else []
        )

        is_schedule_ii_str = row.get("is_schedule_ii_commodity", "").lower()
        is_schedule_ii = is_schedule_ii_str in ("true", "1", "yes")

        product = Product(
            name=name,
            generic_name=generic_name,
            brand=row.get("brand") or None,
            category=row.get("category") or None,
            barcode=barcode,
            is_schedule_ii_commodity=is_schedule_ii,
            standard_pack_sizes=standard_pack_sizes,
            manufacturer_id=manufacturer_id,
            registered_by=registered_by_user_id,
        )
        db.add(product)
        created += 1

    if created > 0:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            return ProductBulkImportResult(
                total_rows=total_rows, created=0, skipped=skipped,
                errors=[f"Database error during import: {exc}"],
            )

    return ProductBulkImportResult(
        total_rows=total_rows,
        created=created,
        skipped=skipped,
        errors=errors,
    )
