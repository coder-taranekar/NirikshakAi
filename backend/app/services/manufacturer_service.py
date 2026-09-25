"""
Manufacturer service — CRUD operations, search, offence tier calculator,
and bulk CSV import for the cross-state manufacturer registry.

Offence tier logic (Section 36, Legal Metrology Act 2009):
  0 prior violations  → next offence is FIRST
  1 prior violation   → next offence is SECOND
  2+ prior violations → next offence is SUBSEQUENT
"""

import csv
import io
import uuid
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.manufacturer import Manufacturer, PenaltyTier, ViolationRecord
from app.schemas.manufacturer import (
    BulkImportResult,
    ManufacturerCreateRequest,
    ManufacturerDetailResponse,
    ManufacturerListResponse,
    ManufacturerResponse,
    ManufacturerUpdateRequest,
    OffenceTierSummary,
    ViolationRecordResponse,
)


# ── Offence Tier Calculator ────────────────────────────────────────────────────

def calculate_next_offence_tier(manufacturer: Manufacturer) -> OffenceTierSummary:
    """
    Determine the penalty tier that will apply to the *next* violation
    for this manufacturer, based on their national violation history.

    This is the core cross-state differentiator: a manufacturer who has
    been caught in Maharashtra and Tamil Nadu cannot claim "first offence"
    in Karnataka — the registry is national.
    """
    total = manufacturer.violations.count()

    if total == 0:
        tier = PenaltyTier.FIRST
        note = "No prior violations on record. Next offence: first offence (up to ₹25,000)."
    elif total == 1:
        tier = PenaltyTier.SECOND
        note = f"1 prior violation on record. Next offence: second offence (up to ₹50,000)."
    else:
        tier = PenaltyTier.SUBSEQUENT
        note = (
            f"{total} prior violations on record. "
            "Next offence: subsequent offence (₹50,000–₹1,00,000 or imprisonment)."
        )

    # Collect distinct states where violations were recorded
    states_with_violations = list(
        {v.state for v in manufacturer.violations.all()}
    )

    return OffenceTierSummary(
        total_violations=total,
        next_tier=tier,
        states_with_violations=sorted(states_with_violations),
        note=note,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_response(manufacturer: Manufacturer) -> ManufacturerResponse:
    return ManufacturerResponse.model_validate(manufacturer)


def _to_detail(manufacturer: Manufacturer) -> ManufacturerDetailResponse:
    violations = [
        ViolationRecordResponse.model_validate(v)
        for v in manufacturer.violations.order_by(ViolationRecord.created_at.desc()).all()
    ]
    offence_tier = calculate_next_offence_tier(manufacturer)
    data = ManufacturerResponse.model_validate(manufacturer).model_dump()
    return ManufacturerDetailResponse(
        **data,
        violations=violations,
        offence_tier=offence_tier,
    )


# ── CRUD ───────────────────────────────────────────────────────────────────────

def create_manufacturer(
    db: Session,
    body: ManufacturerCreateRequest,
) -> Manufacturer:
    """
    Create a new manufacturer record.
    Raises ValueError if registration_number is already in use.
    """
    if body.registration_number:
        existing = (
            db.query(Manufacturer)
            .filter(Manufacturer.registration_number == body.registration_number)
            .first()
        )
        if existing:
            raise ValueError(
                f"Registration number '{body.registration_number}' is already registered "
                f"to manufacturer '{existing.name}' (id={existing.id})"
            )

    manufacturer = Manufacturer(
        name=body.name,
        registered_address=body.registered_address,
        registration_number=body.registration_number,
        states_operating=body.states_operating or [],
        contact_phone=body.contact_phone,
        contact_email=body.contact_email,
    )
    db.add(manufacturer)
    db.commit()
    db.refresh(manufacturer)
    return manufacturer


def get_manufacturer_by_id(db: Session, manufacturer_id: uuid.UUID) -> Optional[Manufacturer]:
    """Return a Manufacturer by primary key, or None if not found."""
    return db.get(Manufacturer, manufacturer_id)


def list_manufacturers(
    db: Session,
    search: Optional[str],
    page: int,
    page_size: int,
) -> ManufacturerListResponse:
    """
    Return a paginated list of manufacturers.
    If *search* is provided, filters by name or registration_number (case-insensitive).
    """
    query = db.query(Manufacturer)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Manufacturer.name.ilike(pattern),
                Manufacturer.registration_number.ilike(pattern),
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    manufacturers = (
        query
        .order_by(Manufacturer.name.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return ManufacturerListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_to_response(m) for m in manufacturers],
    )


def get_manufacturer_detail(
    db: Session,
    manufacturer_id: uuid.UUID,
) -> Optional[ManufacturerDetailResponse]:
    """
    Return full manufacturer profile with violation history and offence tier.
    Returns None if not found.
    """
    manufacturer = get_manufacturer_by_id(db, manufacturer_id)
    if manufacturer is None:
        return None
    return _to_detail(manufacturer)


def update_manufacturer(
    db: Session,
    manufacturer_id: uuid.UUID,
    body: ManufacturerUpdateRequest,
) -> Optional[Manufacturer]:
    """
    Partial update — only fields present in the request are applied.
    Returns None if the manufacturer does not exist.
    Raises ValueError if the new registration_number conflicts with another record.
    """
    manufacturer = get_manufacturer_by_id(db, manufacturer_id)
    if manufacturer is None:
        return None

    update_data = body.model_dump(exclude_unset=True)

    # Check registration_number uniqueness if it's being changed
    new_reg = update_data.get("registration_number")
    if new_reg and new_reg != manufacturer.registration_number:
        conflict = (
            db.query(Manufacturer)
            .filter(
                Manufacturer.registration_number == new_reg,
                Manufacturer.id != manufacturer_id,
            )
            .first()
        )
        if conflict:
            raise ValueError(
                f"Registration number '{new_reg}' is already registered "
                f"to manufacturer '{conflict.name}' (id={conflict.id})"
            )

    for field, value in update_data.items():
        setattr(manufacturer, field, value)

    db.commit()
    db.refresh(manufacturer)
    return manufacturer


def delete_manufacturer(db: Session, manufacturer_id: uuid.UUID) -> bool:
    """
    Delete a manufacturer by ID.
    Returns True if deleted, False if not found.

    Note: cascades to ViolationRecords (ondelete=CASCADE on FK).
    Products with this manufacturer are SET NULL (handled by Product FK).
    """
    manufacturer = get_manufacturer_by_id(db, manufacturer_id)
    if manufacturer is None:
        return False
    db.delete(manufacturer)
    db.commit()
    return True


# ── Bulk CSV Import ────────────────────────────────────────────────────────────

# Expected CSV columns (case-insensitive headers):
#   name, registered_address, registration_number,
#   states_operating, contact_phone, contact_email
#
# states_operating: pipe-separated list, e.g. "Maharashtra|Tamil Nadu|Karnataka"

_REQUIRED_CSV_COLUMNS = {"name", "registered_address"}


def bulk_import_manufacturers(
    db: Session,
    csv_bytes: bytes,
) -> BulkImportResult:
    """
    Parse a UTF-8 CSV file and upsert manufacturer records.

    Rows with a registration_number that already exists are skipped
    (not updated) — use PATCH /manufacturers/{id} for individual updates.
    Rows missing required fields or with invalid data are recorded in errors[].

    Returns a BulkImportResult with counts and any per-row error messages.
    """
    try:
        text = csv_bytes.decode("utf-8-sig")  # handle BOM from Excel exports
    except UnicodeDecodeError:
        return BulkImportResult(
            total_rows=0,
            created=0,
            skipped=0,
            errors=["File is not valid UTF-8. Please save the CSV with UTF-8 encoding."],
        )

    reader = csv.DictReader(io.StringIO(text))

    # Normalise header names to lowercase stripped
    if reader.fieldnames is None:
        return BulkImportResult(
            total_rows=0,
            created=0,
            skipped=0,
            errors=["CSV file appears to be empty or has no header row."],
        )

    headers = {h.strip().lower() for h in reader.fieldnames}
    missing_required = _REQUIRED_CSV_COLUMNS - headers
    if missing_required:
        return BulkImportResult(
            total_rows=0,
            created=0,
            skipped=0,
            errors=[
                f"Missing required CSV columns: {', '.join(sorted(missing_required))}. "
                f"Required: {', '.join(sorted(_REQUIRED_CSV_COLUMNS))}"
            ],
        )

    created = 0
    skipped = 0
    errors: list[str] = []

    rows = list(reader)
    total_rows = len(rows)

    for row_num, raw_row in enumerate(rows, start=2):  # start=2 because row 1 is header
        # Normalise keys
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items()}

        name = row.get("name", "")
        registered_address = row.get("registered_address", "")
        registration_number = row.get("registration_number") or None
        states_raw = row.get("states_operating", "")
        contact_phone = row.get("contact_phone") or None
        contact_email = row.get("contact_email") or None

        # Validate required fields
        if not name:
            errors.append(f"Row {row_num}: 'name' is required — row skipped.")
            skipped += 1
            continue
        if not registered_address:
            errors.append(f"Row {row_num}: 'registered_address' is required — row skipped.")
            skipped += 1
            continue

        # Parse pipe-separated states
        states_operating = (
            [s.strip() for s in states_raw.split("|") if s.strip()]
            if states_raw
            else []
        )

        # Skip if registration_number already exists
        if registration_number:
            existing = (
                db.query(Manufacturer)
                .filter(Manufacturer.registration_number == registration_number)
                .first()
            )
            if existing:
                errors.append(
                    f"Row {row_num}: registration_number '{registration_number}' "
                    f"already exists (id={existing.id}) — row skipped."
                )
                skipped += 1
                continue

        manufacturer = Manufacturer(
            name=name,
            registered_address=registered_address,
            registration_number=registration_number,
            states_operating=states_operating,
            contact_phone=contact_phone,
            contact_email=contact_email,
        )
        db.add(manufacturer)
        created += 1

    # Commit all new records in one transaction
    if created > 0:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            return BulkImportResult(
                total_rows=total_rows,
                created=0,
                skipped=skipped,
                errors=[f"Database error during import: {exc}"],
            )

    return BulkImportResult(
        total_rows=total_rows,
        created=created,
        skipped=skipped,
        errors=errors,
    )
