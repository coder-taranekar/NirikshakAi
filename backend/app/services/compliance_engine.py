"""
Core Compliance Engine — Rule 6 declaration checks with scoring and citations.

Processing flow:
  1. Load YAML rule definitions from app/rules/declarations.yaml
  2. For each rule, search the OCR raw_text for presence (regex match)
  3. Apply format validation where a second pattern is required
  4. Calculate weighted score (0–100)
  5. Flag hard_fail fields — any hard fail → NON_COMPLIANT regardless of score
  6. Return structured compliance_result dict

compliance_result JSON structure:
{
  "overall_score": 72.5,
  "status": "non_compliant",
  "hard_fail_triggered": true,
  "declarations": [
    {
      "field": "mrp",
      "label": "Maximum Retail Price (MRP)",
      "status": "fail",
      "hard_fail": true,
      "extracted_value": null,
      "rule_reference": "Rule 6(c)",
      "violation_description": "...",
      "plain_language_explanation": "...",
      "weight": 5,
      "score_contribution": 0
    }
  ],
  "advanced_checks": {},   // populated by advanced_checks service (Task 7)
  "penalty": {}            // populated by inspection workflow (Task 8)
}
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# ── Rule Loading ───────────────────────────────────────────────────────────────

_RULES_PATH = Path(__file__).parent.parent / "rules" / "declarations.yaml"


@lru_cache(maxsize=1)
def _load_rules() -> list[dict[str, Any]]:
    """Load and cache the YAML rule definitions. Cached for process lifetime."""
    with open(_RULES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Status Thresholds (matches README spec) ────────────────────────────────────

def _score_to_status(score: float, hard_fail: bool) -> str:
    if hard_fail:
        return "non_compliant"
    if score >= 90:
        return "compliant"
    if score >= 70:
        return "partial"
    if score >= 50:
        return "non_compliant"
    return "non_compliant"


# ── Declaration Check ──────────────────────────────────────────────────────────

def _check_declaration(
    rule: dict[str, Any],
    raw_text: str,
) -> dict[str, Any]:
    """
    Check a single Rule 6 declaration field against the OCR raw_text.

    Returns a declaration result dict.
    """
    patterns: list[str] = rule.get("patterns", [])
    hard_fail: bool = rule.get("hard_fail", False)
    weight: int = rule.get("weight", 1)

    matched_value: str | None = None
    found = False

    for pattern in patterns:
        match = re.search(pattern, raw_text)
        if match:
            found = True
            # Extract a short snippet around the match for the report
            start = max(0, match.start() - 5)
            end = min(len(raw_text), match.end() + 30)
            matched_value = raw_text[start:end].strip().replace("\n", " ")
            break

    field_status = "pass" if found else "fail"
    score_contribution = weight if found else 0

    return {
        "field": rule["field"],
        "label": rule["label"],
        "status": field_status,
        "hard_fail": hard_fail,
        "extracted_value": matched_value,
        "rule_reference": rule["rule_reference"],
        "violation_description": rule["violation_description"],
        "plain_language_explanation": rule.get("plain_language_explanation", ""),
        "weight": weight,
        "score_contribution": score_contribution,
    }


# ── MRP Format Detail Check ────────────────────────────────────────────────────

def _check_mrp_format(raw_text: str) -> dict[str, Any]:
    """
    Extended MRP validation beyond simple presence:
      1. Currency symbol present (₹, Rs., INR)
      2. Price to 2 decimal places (XX.XX)
      3. 'Inclusive of all taxes' phrase present

    Returns a supplementary result dict (merged into the mrp declaration).
    """
    issues: list[str] = []

    if not re.search(r"[₹]|Rs\.?|INR", raw_text):
        issues.append("Currency symbol missing (expected ₹, Rs., or INR)")

    if not re.search(r"\d+\.\d{2}", raw_text):
        issues.append("Price not in XX.XX format (2 decimal places required)")

    if not re.search(r"(?i)inclusive\s+of\s+all\s+tax", raw_text):
        issues.append("'Inclusive of all taxes' text missing")

    return {
        "mrp_format_issues": issues,
        "mrp_format_valid": len(issues) == 0,
    }


# ── Net Quantity SI Unit Check ─────────────────────────────────────────────────

def _check_net_quantity_si(raw_text: str) -> dict[str, Any]:
    """
    Verify net quantity is expressed in an SI unit.
    Non-SI units (oz, lb, fl oz) trigger a warning (not hard fail).
    """
    non_si_pattern = r"(?i)\b(\d+\.?\d*)\s*(oz|ounce|lb|lbs|pound|fl\.?\s*oz)\b"
    si_pattern = r"(?i)\b(\d+\.?\d*)\s*(g|gm|gms|kg|kgs|ml|l|ltr|litre|litres|mg)\b"

    has_non_si = bool(re.search(non_si_pattern, raw_text))
    has_si = bool(re.search(si_pattern, raw_text))

    issues: list[str] = []
    if has_non_si and not has_si:
        issues.append("Net quantity declared in non-SI units (oz/lb); SI units required")
    elif has_non_si and has_si:
        issues.append("Non-SI units present alongside SI units — SI should be primary")

    return {
        "si_unit_issues": issues,
        "si_unit_valid": len(issues) == 0,
    }


# ── Date Format Check ──────────────────────────────────────────────────────────

def _check_date_format(raw_text: str) -> dict[str, Any]:
    """
    Verify the manufacture/expiry date is in an acceptable format.
    Acceptable: MM/YYYY, MMM YYYY, DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    """
    valid_date_patterns = [
        r"\b(0?[1-9]|1[0-2])[/\-\.](20\d{2}|19\d{2})\b",   # MM/YYYY
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(20\d{2}|19\d{2})\b",  # MMM YYYY
        r"\b(0?[1-9]|[12]\d|3[01])[/\-\.](0?[1-9]|1[0-2])[/\-\.](20\d{2}|19\d{2})\b",  # DD/MM/YYYY
    ]
    issues: list[str] = []
    found_valid = any(re.search(p, raw_text, re.IGNORECASE) for p in valid_date_patterns)

    # Check for 2-digit year (non-compliant)
    two_digit_year = re.search(r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{2}\b", raw_text)
    if two_digit_year and not found_valid:
        issues.append("Date uses 2-digit year; 4-digit year (YYYY) is required")

    return {
        "date_format_issues": issues,
        "date_format_valid": found_valid or len(issues) == 0,
    }


# ── Main Engine ────────────────────────────────────────────────────────────────

def run_compliance_check(ocr_result: dict[str, Any]) -> dict[str, Any]:
    """
    Run the core Rule 6 compliance checks against an OCR result.

    Args:
        ocr_result: The dict returned by ocr_service.run_ocr()

    Returns:
        compliance_result dict (stored in Inspection.compliance_result).
        The 'advanced_checks' and 'penalty' keys are empty dicts — they are
        filled in by the advanced_checks service and inspection workflow.
    """
    raw_text: str = ocr_result.get("raw_text", "")
    rules = _load_rules()

    declarations: list[dict[str, Any]] = []
    total_weight = 0
    earned_weight = 0
    hard_fail_triggered = False

    for rule in rules:
        result = _check_declaration(rule, raw_text)
        declarations.append(result)
        total_weight += result["weight"]
        earned_weight += result["score_contribution"]
        if result["hard_fail"] and result["status"] == "fail":
            hard_fail_triggered = True

    # Weighted score 0–100
    overall_score = round((earned_weight / total_weight) * 100, 1) if total_weight > 0 else 0.0
    status = _score_to_status(overall_score, hard_fail_triggered)

    # Supplementary format checks (do not affect score — informational)
    supplementary: dict[str, Any] = {}
    supplementary.update(_check_mrp_format(raw_text))
    supplementary.update(_check_net_quantity_si(raw_text))
    supplementary.update(_check_date_format(raw_text))

    return {
        "overall_score": overall_score,
        "status": status,
        "hard_fail_triggered": hard_fail_triggered,
        "declarations": declarations,
        "supplementary_format_checks": supplementary,
        "advanced_checks": {},   # populated by Task 7
        "penalty": {},           # populated by Task 8
    }
