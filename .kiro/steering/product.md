# NirikshakAI / LabelGuard — Product Overview

**NirikshakAI** (branded as **LabelGuard** in the codebase) is an automated compliance-checking system for packaged commodities under India's **Legal Metrology (Packaged Commodities) Rules, 2011**, administered by the Department of Consumer Affairs, Government of India.

## What It Does

Scans packaged product labels via camera (mobile), image upload (web/mobile), or e-commerce URL, then:

1. Extracts mandatory declarations using OCR (Google Cloud Vision primary, EasyOCR fallback)
2. Validates them against the Legal Metrology rules with exact rule citations
3. Generates a compliance score (0–100) and a structured result with per-field pass/fail status
4. Produces legally-referenceable reports (PDF, Excel, DOCX)
5. Maintains a **cross-state manufacturer violation registry** to enforce correct penalty tiers nationally

## Target Users

- **Field Inspectors** — scan labels in the field via mobile camera; view results immediately
- **Admins** — manage users, manufacturers, products; view dashboard analytics and reports

## Key Differentiators

| Gap | How it's solved |
|---|---|
| Cross-state offence tracking absent | Central `ViolationRecord` registry; penalty tier (first/second/subsequent) calculated nationally |
| MRP sticker fraud | Multi-MRP detection on same label |
| Font size never checked at scale | Pixel bounding box → physical mm estimation from image DPI (Rules 7/8) |
| Whitespace/clearance zones ignored | Clearance zone validator (Rule 8) |
| Standard pack sizes ignored | Schedule II validator against permitted sizes |
| E-commerce labels unchecked | URL scanner (httpx + BeautifulSoup) extracts listing images |
| Penalty calculated manually/wrongly | Automated penalty calculator referencing national violation history |

## Compliance Scoring

- **90–100**: Compliant
- **70–89**: Partially Compliant (minor violations)
- **50–69**: Non-Compliant (significant violations)
- **< 50**: Severely Non-Compliant
- Any **hard fail** (missing MRP, missing manufacturer address, missing net quantity, missing manufacture date) → Non-Compliant regardless of score

## Governing Law

- Legal Metrology Act, 2009 (in force from 1 April 2011)
- Legal Metrology (Packaged Commodities) Rules, 2011
- Mandatory declarations: Rule 6 | Font sizes: Rules 7(3) and 8 | Penalties: Section 36
