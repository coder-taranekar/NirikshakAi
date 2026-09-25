"""
Advanced compliance checks — beyond basic Rule 6 presence/format validation.

Checks implemented here:
  1. Font size estimator    — Rule 7(3) & Rule 8: minimum physical height in mm
  2. Whitespace clearance   — Rule 8: blank zones around quantity numerals
  3. MRP sticker fraud      — multiple distinct MRP values on same label
  4. Schedule II pack size  — declared quantity vs permitted pack sizes
  5. Multilingual checker   — detect presence of Hindi/Devanagari text

Each check returns a structured result dict. All results are merged into the
compliance_result["advanced_checks"] key by the inspection workflow (Task 8).
"""

import re
from typing import Any, Optional

from app.services.ocr_service import pixels_to_mm


# ── 1. Font Size Estimator (Rules 7(3) & 8) ───────────────────────────────────

# Minimum font heights per Rule 7(3) and Rule 8 (in mm)
# Keys are net quantity thresholds in grams/ml

_GENERAL_DECLARATION_MIN_MM = 1.0      # All declarations: min 1mm
_GENERAL_MOLDED_MIN_MM = 2.0           # Molded/embossed/perforated: min 2mm

# Quantity numeral minimum heights by net quantity (normal / molded)
_QUANTITY_FONT_TABLE = [
    # (max_quantity_gml, normal_mm, molded_mm)
    (200,  1.0, 2.0),
    (500,  2.0, 4.0),
    (float("inf"), 4.0, 6.0),
]

# Panel area minimum heights (cm²)
_PANEL_FONT_TABLE = [
    # (max_area_cm2, normal_mm, molded_mm)
    (100,   1.0, 2.0),
    (500,   2.0, 4.0),
    (2500,  4.0, 6.0),
    (float("inf"), 6.0, 6.0),
]


def _required_quantity_font_height(net_quantity_gml: float, molded: bool = False) -> float:
    for max_qty, normal_mm, molded_mm in _QUANTITY_FONT_TABLE:
        if net_quantity_gml <= max_qty:
            return molded_mm if molded else normal_mm
    return 4.0


def check_font_sizes(
    ocr_result: dict[str, Any],
    net_quantity_gml: Optional[float] = None,
) -> dict[str, Any]:
    """
    Check whether OCR block heights satisfy minimum physical font height
    requirements (Rules 7(3) and 8).

    For each text block the OCR engine detected:
      - All declaration text must be ≥ 1mm
      - Quantity numerals must meet the net-quantity-based threshold

    Args:
        ocr_result: dict from ocr_service.run_ocr()
        net_quantity_gml: declared net quantity in g or ml (used for threshold lookup)

    Returns dict with:
        violations: list of blocks that fail the minimum height
        passed: int — blocks that meet requirements
        failed: int — blocks that don't
    """
    blocks: list[dict] = ocr_result.get("blocks", [])
    dpi: int = ocr_result.get("image_dpi", 150)

    required_general_mm = _GENERAL_DECLARATION_MIN_MM
    required_quantity_mm = (
        _required_quantity_font_height(net_quantity_gml)
        if net_quantity_gml is not None
        else _GENERAL_DECLARATION_MIN_MM
    )

    # Regex to identify blocks likely containing quantity numerals
    quantity_pattern = re.compile(
        r"(?i)\b\d+\.?\d*\s*(g|gm|kg|ml|l|ltr|litre)\b"
    )

    violations: list[dict] = []
    passed = 0

    for block in blocks:
        bb = block.get("bounding_box", {})
        height_px = bb.get("height", 0)
        height_mm = pixels_to_mm(height_px, dpi)
        text = block.get("text", "")

        is_quantity_block = bool(quantity_pattern.search(text))
        required_mm = required_quantity_mm if is_quantity_block else required_general_mm

        if height_mm < required_mm:
            violations.append({
                "text": text,
                "measured_mm": height_mm,
                "required_mm": required_mm,
                "bounding_box": bb,
                "is_quantity_block": is_quantity_block,
                "rule_reference": "Rule 7(3)" if is_quantity_block else "Rule 8",
            })
        else:
            passed += 1

    return {
        "font_size_violations": violations,
        "font_size_passed": passed,
        "font_size_failed": len(violations),
        "font_size_compliant": len(violations) == 0,
    }


# ── 2. Whitespace Clearance (Rule 8) ──────────────────────────────────────────

def check_whitespace_clearance(ocr_result: dict[str, Any]) -> dict[str, Any]:
    """
    Rule 8 requires blank clearance zones around quantity numerals:
      - Top and bottom: blank space ≥ numeral height
      - Left and right: blank space ≥ 2 × numeral height

    This implementation identifies quantity blocks and checks whether any
    other text block's bounding box intrudes into the required clearance zone.

    Returns dict with:
        whitespace_violations: list of intrusions detected
        whitespace_compliant: bool
    """
    blocks: list[dict] = ocr_result.get("blocks", [])
    dpi: int = ocr_result.get("image_dpi", 150)

    quantity_pattern = re.compile(
        r"(?i)\b\d+\.?\d*\s*(g|gm|kg|ml|l|ltr|litre)\b"
    )

    quantity_blocks = [b for b in blocks if quantity_pattern.search(b.get("text", ""))]
    other_blocks = [b for b in blocks if not quantity_pattern.search(b.get("text", ""))]

    violations: list[dict] = []

    for qblock in quantity_blocks:
        bb = qblock.get("bounding_box", {})
        qx = bb.get("x", 0)
        qy = bb.get("y", 0)
        qw = bb.get("width", 0)
        qh = bb.get("height", 0)
        h_mm = pixels_to_mm(qh, dpi)

        # Convert required clearance from mm back to pixels for comparison
        # pixels = mm × dpi / 25.4
        from app.services.ocr_service import _MM_PER_INCH
        v_clear_px = (h_mm / _MM_PER_INCH) * dpi         # vertical: 1× height
        h_clear_px = (h_mm * 2 / _MM_PER_INCH) * dpi     # horizontal: 2× height

        # Required clear zone
        clear_x1 = qx - h_clear_px
        clear_x2 = qx + qw + h_clear_px
        clear_y1 = qy - v_clear_px
        clear_y2 = qy + qh + v_clear_px

        for other in other_blocks:
            obb = other.get("bounding_box", {})
            ox = obb.get("x", 0)
            oy = obb.get("y", 0)
            ow = obb.get("width", 0)
            oh = obb.get("height", 0)

            # Check for overlap with clear zone
            overlaps_x = ox < clear_x2 and (ox + ow) > clear_x1
            overlaps_y = oy < clear_y2 and (oy + oh) > clear_y1

            if overlaps_x and overlaps_y:
                violations.append({
                    "quantity_text": qblock.get("text", ""),
                    "intruding_text": other.get("text", ""),
                    "rule_reference": "Rule 8",
                    "description": (
                        f"Text '{other.get('text', '')}' intrudes into the "
                        f"mandatory clearance zone around quantity numeral "
                        f"'{qblock.get('text', '')}'"
                    ),
                })

    return {
        "whitespace_violations": violations,
        "whitespace_compliant": len(violations) == 0,
    }


# ── 3. MRP Sticker Fraud Detector ─────────────────────────────────────────────

def check_mrp_sticker_fraud(ocr_result: dict[str, Any]) -> dict[str, Any]:
    """
    Detect MRP sticker fraud: more than one distinct MRP value found on the label.

    Method: extract all numeric values following MRP/price markers and flag if
    more than one distinct value is present (indicating a sticker may be covering
    a lower printed MRP).

    Returns dict with:
        mrp_values_found: list of distinct MRP strings extracted
        sticker_fraud_detected: bool
        sticker_fraud_note: str
    """
    raw_text: str = ocr_result.get("raw_text", "")

    # Match all MRP declarations with their numeric values
    mrp_pattern = re.compile(
        r"(?i)(mrp|maximum\s+retail\s+price)\s*[₹Rs\.INR]*\s*(\d+[.,]\d{2}|\d+)"
    )
    matches = mrp_pattern.findall(raw_text)
    values = list({m[1].replace(",", ".") for m in matches})

    fraud_detected = len(values) > 1
    note = ""
    if fraud_detected:
        note = (
            f"Multiple MRP values found: {', '.join(values)}. "
            "This may indicate a price sticker covering the original printed MRP. "
            "Verify the label physically for Rule 6(c) sticker compliance."
        )
    elif len(values) == 1:
        note = f"Single MRP value found: ₹{values[0]}. No sticker fraud detected."
    else:
        note = "No MRP value could be extracted from OCR text."

    return {
        "mrp_values_found": values,
        "sticker_fraud_detected": fraud_detected,
        "sticker_fraud_note": note,
    }


# ── 4. Schedule II Pack Size Validator ────────────────────────────────────────

def check_pack_size(
    ocr_result: dict[str, Any],
    permitted_sizes: list[str],
    generic_name: str,
) -> dict[str, Any]:
    """
    Validate that the declared net quantity matches one of the permitted
    pack sizes for this Schedule II commodity.

    Args:
        ocr_result: dict from ocr_service.run_ocr()
        permitted_sizes: list of allowed sizes as strings (e.g. ["200", "500", "1000"])
        generic_name: the commodity name (for the violation message)

    Returns dict with:
        declared_quantity: str | None
        permitted_sizes: list[str]
        pack_size_violation: bool
        pack_size_note: str
    """
    raw_text: str = ocr_result.get("raw_text", "")

    # Extract net quantity value + unit
    qty_pattern = re.compile(
        r"(?i)\bnet\s*(wt\.?|weight|qty\.?|vol\.?)?\s*[:\-]?\s*(\d+\.?\d*)\s*(g|gm|gms|kg|ml|l|ltr)\b"
    )
    match = qty_pattern.search(raw_text)

    declared_str: str | None = None
    violation = False
    note = ""

    if match:
        value_str = match.group(2)
        unit = match.group(3).lower()
        # Normalise to base unit (g or ml)
        try:
            value = float(value_str)
            if unit in ("kg", "kgs"):
                value *= 1000
            elif unit in ("l", "ltr", "litre", "litres"):
                value *= 1000
            declared_str = str(int(value)) if value == int(value) else str(value)
        except ValueError:
            declared_str = value_str

        if declared_str and declared_str not in permitted_sizes:
            violation = True
            note = (
                f"Declared quantity '{declared_str}' is not a permitted pack size for "
                f"'{generic_name}' under Schedule II. "
                f"Permitted sizes: {', '.join(permitted_sizes)} (g or ml)."
            )
        else:
            note = f"Declared quantity '{declared_str}' is a valid Schedule II pack size."
    else:
        note = "Net quantity could not be extracted; pack size check skipped."

    return {
        "declared_quantity": declared_str,
        "permitted_sizes": permitted_sizes,
        "pack_size_violation": violation,
        "pack_size_note": note,
    }


# ── 5. Multilingual / Hindi Checker ───────────────────────────────────────────

# Devanagari Unicode block: U+0900–U+097F
_DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")

# Common Hindi characters that indicate Hindi text presence
_HINDI_KEYWORDS = re.compile(
    r"(?:अधिकतम|खुदरा|मूल्य|निर्माता|नेट|वज़न|मात्रा|समाप्ति|उत्पादन)"
)


def check_multilingual(ocr_result: dict[str, Any]) -> dict[str, Any]:
    """
    Check for presence of Hindi/Devanagari text on the label.

    This is an informational check (not a hard fail) — multilingual labelling
    is encouraged under consumer protection guidelines but not strictly mandated
    for all commodities under the 2011 Rules.

    Returns dict with:
        devanagari_detected: bool
        hindi_keywords_found: list[str]
        multilingual_note: str
    """
    blocks: list[dict] = ocr_result.get("blocks", [])
    all_text = " ".join(b.get("text", "") for b in blocks)

    devanagari_present = bool(_DEVANAGARI_PATTERN.search(all_text))
    hindi_kw_matches = _HINDI_KEYWORDS.findall(all_text)

    note = ""
    if devanagari_present:
        note = "Hindi/Devanagari text detected on label. Multilingual compliance present."
    else:
        note = (
            "No Hindi/Devanagari text detected. "
            "Multilingual labelling is encouraged but not mandatory for all commodities."
        )

    return {
        "devanagari_detected": devanagari_present,
        "hindi_keywords_found": list(set(hindi_kw_matches)),
        "multilingual_note": note,
    }


# ── Composite Runner ───────────────────────────────────────────────────────────

def run_advanced_checks(
    ocr_result: dict[str, Any],
    net_quantity_gml: Optional[float] = None,
    is_schedule_ii: bool = False,
    permitted_sizes: Optional[list[str]] = None,
    generic_name: str = "",
) -> dict[str, Any]:
    """
    Run all advanced checks and return a combined result dict.
    This is merged into compliance_result["advanced_checks"] by the inspection workflow.
    """
    result: dict[str, Any] = {}

    result.update(check_font_sizes(ocr_result, net_quantity_gml=net_quantity_gml))
    result.update(check_whitespace_clearance(ocr_result))
    result.update(check_mrp_sticker_fraud(ocr_result))
    result.update(check_multilingual(ocr_result))

    if is_schedule_ii and permitted_sizes:
        result.update(check_pack_size(ocr_result, permitted_sizes, generic_name))
    else:
        result["pack_size_violation"] = False
        result["pack_size_note"] = "Not a Schedule II commodity — pack size check skipped."

    return result
