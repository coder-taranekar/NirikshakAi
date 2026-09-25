"""
Inspection service — end-to-end compliance pipeline.

Pipeline for image upload:
  1. Upload original image to MinIO (label-images bucket)
  2. Run OCR (ocr_service.run_ocr)
  3. Run core compliance engine (compliance_engine.run_compliance_check)
  4. Run advanced checks (advanced_checks.run_advanced_checks)
  5. Calculate penalty tier (manufacturer violation history)
  6. Generate annotated image (bounding boxes + violation markers via Pillow)
  7. Upload annotated image to MinIO
  8. Persist Inspection record to PostgreSQL
  9. Persist ViolationRecords for non-compliant manufacturers

The URL scanner (Task 9) calls a subset of this pipeline after fetching
the product image from the listing page.
"""

import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from minio import Minio
from minio.error import S3Error
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from app.config import settings
from app.models.inspection import Inspection, InspectionSource, InspectionStatus
from app.models.manufacturer import PenaltyTier, ViolationRecord
from app.models.product import Product
from app.schemas.inspection import InspectionCreateRequest
from app.services.advanced_checks import run_advanced_checks
from app.services.compliance_engine import run_compliance_check
from app.services.ocr_service import run_ocr

logger = logging.getLogger(__name__)


# ── MinIO Client ───────────────────────────────────────────────────────────────

def _get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _upload_to_minio(
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str = "image/jpeg",
) -> str:
    """
    Upload bytes to MinIO and return the public object URL.
    Returns a best-effort URL; does not raise — logs errors instead.
    """
    try:
        client = _get_minio_client()
        client.put_object(
            bucket,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        # Build URL: http(s)://endpoint/bucket/object_name
        scheme = "https" if settings.minio_secure else "http"
        return f"{scheme}://{settings.minio_endpoint}/{bucket}/{object_name}"
    except (S3Error, Exception) as exc:
        logger.error("minio_upload_failed", bucket=bucket, object=object_name, error=str(exc))
        return ""


# ── Annotated Image Generator ──────────────────────────────────────────────────

_PASS_COLOR = (0, 200, 0)       # green
_FAIL_COLOR = (220, 38, 38)     # red
_WARN_COLOR = (255, 165, 0)     # orange


def _generate_annotated_image(
    original_bytes: bytes,
    ocr_result: dict[str, Any],
    compliance_result: dict[str, Any],
) -> bytes:
    """
    Draw bounding boxes on the original image:
      - Green  : text blocks that matched a required declaration
      - Red    : hard-fail violations
      - Orange : soft violations / warnings

    Returns the annotated image as JPEG bytes.
    """
    try:
        img = Image.open(io.BytesIO(original_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Build a set of violation text snippets for quick lookup
        violations = {
            d["extracted_value"]: d["hard_fail"]
            for d in compliance_result.get("declarations", [])
            if d["status"] == "fail" and d.get("extracted_value")
        }
        passes = {
            d["extracted_value"]
            for d in compliance_result.get("declarations", [])
            if d["status"] == "pass" and d.get("extracted_value")
        }

        for block in ocr_result.get("blocks", []):
            text = block.get("text", "")
            bb = block.get("bounding_box", {})
            x = bb.get("x", 0)
            y = bb.get("y", 0)
            w = bb.get("width", 0)
            h = bb.get("height", 0)

            # Determine colour
            color = None
            if any(text in snippet for snippet in passes):
                color = _PASS_COLOR
            elif text in violations:
                color = _FAIL_COLOR if violations[text] else _WARN_COLOR

            if color:
                draw.rectangle(
                    [x, y, x + w, y + h],
                    outline=color,
                    width=2,
                )

        # Add legend
        legend_y = 10
        legend_items = [
            (_PASS_COLOR, "Pass"),
            (_FAIL_COLOR, "Hard Fail"),
            (_WARN_COLOR, "Warning"),
        ]
        for color, label in legend_items:
            draw.rectangle([10, legend_y, 22, legend_y + 12], fill=color)
            draw.text((27, legend_y), label, fill=(0, 0, 0))
            legend_y += 18

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()

    except Exception as exc:
        logger.error("annotated_image_generation_failed", error=str(exc))
        return original_bytes  # fall back to original


# ── Penalty Calculator ─────────────────────────────────────────────────────────

def _calculate_penalty(
    compliance_result: dict[str, Any],
    manufacturer: Optional[Any],
) -> dict[str, Any]:
    """
    Determine the penalty tier and estimated range based on:
      - The compliance result (status, hard_fail_triggered)
      - The manufacturer's national violation history

    Penalty ranges from Section 36, Legal Metrology Act 2009:
      First offence:      up to ₹25,000
      Second offence:     up to ₹50,000
      Subsequent:         ₹50,000–₹1,00,000 or imprisonment
    """
    status = compliance_result.get("status", "pending")
    if status == "compliant":
        return {
            "tier": None,
            "applicable_section": "Section 36, Legal Metrology Act 2009",
            "estimated_min": 0,
            "estimated_max": 0,
            "note": "Product is compliant — no penalty applicable.",
        }

    # Determine tier from manufacturer history
    prior_count = 0
    if manufacturer is not None:
        prior_count = manufacturer.violations.count()

    if prior_count == 0:
        tier = PenaltyTier.FIRST
        min_penalty = 0
        max_penalty = 25000
        note = "First offence. Penalty up to ₹25,000."
    elif prior_count == 1:
        tier = PenaltyTier.SECOND
        min_penalty = 0
        max_penalty = 50000
        note = f"Second offence ({prior_count} prior violation). Penalty up to ₹50,000."
    else:
        tier = PenaltyTier.SUBSEQUENT
        min_penalty = 50000
        max_penalty = 100000
        note = (
            f"Subsequent offence ({prior_count} prior violations). "
            "Penalty ₹50,000–₹1,00,000 or imprisonment up to 1 year or both."
        )

    return {
        "tier": tier.value,
        "applicable_section": "Section 36(1), Legal Metrology Act 2009",
        "estimated_min": min_penalty,
        "estimated_max": max_penalty,
        "note": note,
    }


# ── Inspection Status from Score ───────────────────────────────────────────────

def _derive_status(score: float, hard_fail: bool) -> InspectionStatus:
    if hard_fail or score < 50:
        return InspectionStatus.NON_COMPLIANT
    if score >= 90:
        return InspectionStatus.COMPLIANT
    return InspectionStatus.PARTIAL


# ── Persist Violation Records ──────────────────────────────────────────────────

def _persist_violation_records(
    db: Session,
    inspection: Inspection,
    compliance_result: dict[str, Any],
    manufacturer_id: Optional[uuid.UUID],
    state: Optional[str],
    penalty_tier: Optional[str],
) -> None:
    """
    For each failed hard-fail declaration, create a ViolationRecord
    linked to both the inspection and the manufacturer.
    """
    if manufacturer_id is None:
        return

    for decl in compliance_result.get("declarations", []):
        if decl["status"] == "fail" and decl["hard_fail"]:
            tier_enum = PenaltyTier(penalty_tier) if penalty_tier else PenaltyTier.FIRST
            vr = ViolationRecord(
                manufacturer_id=manufacturer_id,
                inspection_id=inspection.id,
                state=state or "Unknown",
                offence_type=decl["field"],
                penalty_tier=tier_enum,
                description=(
                    f"{decl['violation_description']} ({decl['rule_reference']})"
                ),
            )
            db.add(vr)

    db.commit()


# ── Main Pipeline ──────────────────────────────────────────────────────────────

def run_inspection_pipeline(
    db: Session,
    image_bytes: bytes,
    meta: InspectionCreateRequest,
    inspector_id: uuid.UUID,
    filename: str = "label.jpg",
) -> Inspection:
    """
    Full end-to-end inspection pipeline for an uploaded image.

    Steps:
      1. Upload original image to MinIO
      2. OCR
      3. Core compliance check
      4. Advanced checks
      5. Penalty calculation
      6. Annotate image + upload to MinIO
      7. Persist inspection + violation records

    Returns the persisted Inspection ORM object.
    """
    # ── Step 1: Upload original image ──────────────────────────────────────────
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    object_name = f"inspections/{ts}_{uuid.uuid4().hex[:8]}_{filename}"
    image_url = _upload_to_minio(settings.minio_bucket_images, object_name, image_bytes)

    # ── Step 2: OCR ────────────────────────────────────────────────────────────
    ocr_result = run_ocr(image_bytes)

    # ── Step 3: Core compliance ────────────────────────────────────────────────
    compliance_result = run_compliance_check(ocr_result)

    # ── Step 4: Advanced checks ────────────────────────────────────────────────
    product: Optional[Product] = None
    if meta.product_id:
        product = db.get(Product, meta.product_id)

    net_qty: Optional[float] = None
    permitted_sizes: list[str] = []
    is_schedule_ii = False
    generic_name = ""

    if product:
        is_schedule_ii = product.is_schedule_ii_commodity
        permitted_sizes = product.standard_pack_sizes or []
        generic_name = product.generic_name

    advanced = run_advanced_checks(
        ocr_result,
        net_quantity_gml=net_qty,
        is_schedule_ii=is_schedule_ii,
        permitted_sizes=permitted_sizes,
        generic_name=generic_name,
    )
    compliance_result["advanced_checks"] = advanced

    # ── Step 5: Penalty ────────────────────────────────────────────────────────
    manufacturer = None
    if product and product.manufacturer_id:
        from app.models.manufacturer import Manufacturer
        manufacturer = db.get(Manufacturer, product.manufacturer_id)

    penalty = _calculate_penalty(compliance_result, manufacturer)
    compliance_result["penalty"] = penalty

    score = compliance_result["overall_score"]
    hard_fail = compliance_result["hard_fail_triggered"]
    insp_status = _derive_status(score, hard_fail)

    # ── Step 6: Annotated image ────────────────────────────────────────────────
    annotated_bytes = _generate_annotated_image(image_bytes, ocr_result, compliance_result)
    annotated_name = object_name.replace("inspections/", "inspections/annotated_")
    annotated_url = _upload_to_minio(
        settings.minio_bucket_images, annotated_name, annotated_bytes
    )

    # ── Step 7: Persist inspection ─────────────────────────────────────────────
    inspection = Inspection(
        source=meta.source,
        source_url=None,
        state=meta.state,
        district=meta.district,
        image_url=image_url,
        annotated_image_url=annotated_url,
        ocr_result=ocr_result,
        compliance_result=compliance_result,
        score=score,
        status=insp_status,
        hard_fail_triggered=hard_fail,
        penalty_tier=penalty.get("tier"),
        estimated_penalty_min=penalty.get("estimated_min"),
        estimated_penalty_max=penalty.get("estimated_max"),
        inspector_notes=meta.inspector_notes,
        product_id=meta.product_id,
        inspector_id=inspector_id,
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    # ── Persist violation records ──────────────────────────────────────────────
    if insp_status == InspectionStatus.NON_COMPLIANT and manufacturer:
        _persist_violation_records(
            db,
            inspection,
            compliance_result,
            product.manufacturer_id if product else None,
            meta.state,
            penalty.get("tier"),
        )

    logger.info(
        "inspection_complete",
        inspection_id=str(inspection.id),
        score=score,
        status=insp_status.value,
        engine=ocr_result.get("ocr_engine"),
    )
    return inspection


def run_url_inspection_pipeline(
    db: Session,
    image_bytes: bytes,
    source_url: str,
    state: Optional[str],
    district: Optional[str],
    product_id: Optional[uuid.UUID],
    inspector_id: uuid.UUID,
) -> Inspection:
    """
    Inspection pipeline variant for URL-scanned images (Task 9).
    Same as run_inspection_pipeline but source=URL and source_url is stored.
    """
    from app.schemas.inspection import InspectionCreateRequest as Req
    meta = Req(
        source=InspectionSource.URL,
        state=state,
        district=district,
        product_id=product_id,
    )
    inspection = run_inspection_pipeline(
        db, image_bytes, meta, inspector_id, filename="url_scan.jpg"
    )
    # Update source_url (not on InspectionCreateRequest to keep schema clean)
    inspection.source_url = source_url
    db.commit()
    db.refresh(inspection)
    return inspection


# ── List / Get helpers ─────────────────────────────────────────────────────────

def list_inspections(
    db: Session,
    inspector_id: Optional[uuid.UUID],
    product_id: Optional[uuid.UUID],
    state: Optional[str],
    status: Optional[str],
    score_min: Optional[float],
    score_max: Optional[float],
    page: int,
    page_size: int,
) -> tuple[int, list[Inspection]]:
    query = db.query(Inspection)
    if inspector_id:
        query = query.filter(Inspection.inspector_id == inspector_id)
    if product_id:
        query = query.filter(Inspection.product_id == product_id)
    if state:
        query = query.filter(Inspection.state.ilike(f"%{state}%"))
    if status:
        query = query.filter(Inspection.status == status)
    if score_min is not None:
        query = query.filter(Inspection.score >= score_min)
    if score_max is not None:
        query = query.filter(Inspection.score <= score_max)

    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(Inspection.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return total, items
