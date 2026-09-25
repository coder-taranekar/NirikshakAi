# NirikshakAI — Legal Metrology Compliance Checker
### Project Memory & Implementation Plan

> **This file is the single source of truth for the project. Read it at the start of every session.**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement & Real-World Context](#2-problem-statement--real-world-context)
3. [Real-World Loopholes We Are Solving](#3-real-world-loopholes-we-are-solving)
4. [Legal Framework Reference](#4-legal-framework-reference)
5. [Decisions Made](#5-decisions-made)
6. [Technology Stack](#6-technology-stack)
7. [System Architecture](#7-system-architecture)
8. [Data Models](#8-data-models)
9. [API Endpoint Summary](#9-api-endpoint-summary)
10. [Compliance Rule Engine Design](#10-compliance-rule-engine-design)
11. [Full Task Breakdown](#11-full-task-breakdown)
12. [Folder Structure](#12-folder-structure)
13. [Why This Solution Wins](#13-why-this-solution-wins)
14. [Progress Tracker](#14-progress-tracker)

---

## 1. Project Overview

**Product Name:** NirikshakAI

**Tagline:** Automated compliance checking for packaged commodities under India's Legal Metrology Act.

**What it does:**
NirikshakAI is a web + mobile application that scans packaged product labels using OCR, extracts mandatory declarations, validates them against the Legal Metrology (Packaged Commodities) Rules, 2011, and generates legally-referenceable compliance reports for enforcement officials.

**Event context:** This is being built for a hackathon/competition. The goal is to win by building the most complete and impactful solution — not just a basic compliance checker, but a systemic enforcement tool that addresses documented real-world gaps in how India enforces legal metrology rules.

**Governing Law:**
- Legal Metrology Act, 2009 (in force from 1 April 2011)
- Legal Metrology (Packaged Commodities) Rules, 2011
- Administered by: Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution, Government of India

---

## 2. Problem Statement & Real-World Context

Packaged commodities sold across India (retail stores, supermarkets, e-commerce) are required to carry mandatory declarations under the Legal Metrology (Packaged Commodities) Rules, 2011. These include:

- Name and address of manufacturer/packer/importer
- Net quantity (in SI units)
- Maximum Retail Price (MRP) in a specific format
- Month and year of manufacture/packing/import
- Consumer care details (name, address, phone, email)
- Generic name of the commodity
- Country of origin (for imports)

**The enforcement problem:**
- Manual inspection is time-consuming and resource-intensive
- India has a massive volume and variety of packaged products
- Legal Metrology Inspectors are often unfamiliar with the exact rules and latest case law
- Non-compliance (missing declarations, wrong font sizes, improper MRP format, sticker fraud) is widespread
- No automated, centralised system exists

---

## 3. Real-World Loopholes We Are Solving

These are documented failures in the current enforcement system that our solution directly addresses:

| # | Real-World Gap | How NirikshakAI Addresses It |
|---|---|---|
| 1 | **Cross-state offence tracking absent** — violations tracked per-state, so a manufacturer can violate rules in 5 states and each counts as a "first offence" | Central manufacturer violation registry with national offence tier calculation |
| 2 | **MRP sticker fraud** — old MRP covered with new sticker; inflated MRP over printed price | Multi-price detection: flag when two MRP values are found on the same label |
| 3 | **Font size never checked** — Rule 7(3) & 8 specify exact minimum heights in mm; impossible to check manually at scale | Pixel bounding box → physical mm estimation using image DPI |
| 4 | **Whitespace/clearance zone ignored** — Rule 8 requires blank zones around quantity numerals | Clearance zone checker: verify no text intrudes into mandatory blank areas |
| 5 | **Standard pack sizes ignored** — Schedule II restricts pack sizes for certain commodities (e.g., mineral water only in specific volumes) | Schedule II validator: compare declared quantity against permitted sizes |
| 6 | **Inspectors don't know the rules** — leads to dragged-out proceedings | Every violation includes exact rule number + plain-language explanation |
| 7 | **E-commerce labels unchecked** — product listings on Amazon/Flipkart also need compliance | URL scanner: extract product listing images and run full compliance check |
| 8 | **Penalty tier calculated manually (or wrongly)** — penalty escalates on second/subsequent offences but state tracking fails | Automated penalty calculator using cross-state offence history |
| 9 | **Multilingual declarations** — labels may need Hindi/regional language alongside English | Multilingual checker using EasyOCR with Devanagari (Hindi) support |
| 10 | **Combination pack declarations often incomplete** | Combination pack detector with specific guidance |

---

## 4. Legal Framework Reference

### Mandatory Declarations (Rule 6)

| Declaration | Rule | Hard Fail if Missing | Weight |
|---|---|---|---|
| Name + address of manufacturer/packer/importer | 6(a) | YES | 5 |
| Generic name of commodity | 6(b) | NO | 4 |
| MRP (format: `MRP ₹XX.XX Inclusive of all taxes`) | 6(c) | YES | 5 |
| Month and year of manufacture/packing/import | 6(d) | YES | 4 |
| Net quantity (SI units) | 6(e) | YES | 5 |
| Consumer care details (name + address + phone + email) | 6(f) | NO | 3 |
| Country of origin (imports only) | — | NO | 3 |

### Font Height Requirements (Rule 7(3) & Rule 8)

**All declarations:** minimum 1mm height (2mm if molded/embossed/perforated)

**Numerals in quantity declarations (by net quantity):**

| Net Quantity | Min Height (Normal) | Min Height (Molded/Embossed) |
|---|---|---|
| < 200g or ml | 1mm | 2mm |
| 200g–500g or ml | 2mm | 4mm |
| > 500g or ml | 4mm | 6mm |

**Numerals in quantity by display panel area:**

| Panel Area | Min Height (Normal) | Min Height (Molded/Embossed) |
|---|---|---|
| < 100 cm² | 1mm | 2mm |
| 100–500 cm² | 2mm | 4mm |
| 500–2500 cm² | 4mm | 6mm |
| > 2500 cm² | 6mm | 6mm |

### Whitespace Clearance (Rule 8)
- Top and bottom of quantity numeral: blank space ≥ numeral height
- Left and right of quantity numeral: blank space ≥ 2× numeral height

### Principal Display Panel (Rule 7)
- Rectangular package: one full side
- Cylindrical/pipe-shaped: 40% of surface area
- Other shapes: 40% of total surface area
- Excludes: top, bottom, flanges, shoulders, necks

### MRP Format (Rule 6(c))
Must read: `Maximum Retail Price ₹XX.XX Inclusive of all taxes`
OR: `MRP ₹XX.XX Inclusive of all taxes`
- Currency symbol must be ₹, Rs., or INR
- Price must be to 2 decimal places
- "Inclusive of all taxes" text must be present

### Standard Pack Sizes (Schedule II — examples)
- Mineral Water / Drinking Water: 100ml, 150ml, 200ml, 250ml, 300ml, 500ml, 750ml, 1L, 1.5L, 2L, 3L, 4L, 5L, then multiples of 5L
- (Full Schedule II to be seeded into database)

### Penalties (Section 36, Legal Metrology Act 2009)
| Offence | Retailer/Wholesaler | Manufacturer/Importer |
|---|---|---|
| Wrong/missing declarations — 1st | Up to ₹25,000 | Up to ₹25,000 |
| 2nd offence | Up to ₹50,000 | Up to ₹50,000 |
| Subsequent | ₹50,000–₹1,00,000 or 1 year imprisonment or both | Same |
| Error in net quantity — 1st | ₹10,000–₹50,000 | ₹10,000–₹50,000 |
| Selling above MRP | ₹2,000 | ₹5,000 |

---

## 5. Decisions Made

| Question | Decision |
|---|---|
| Deployment target | Web dashboard (admins) + Mobile app (field inspectors) |
| Scale | MVP / Pilot — 10–50 users |
| Technology constraint | Open source only; free-tier cloud services allowed |
| OCR approach | Google Cloud Vision API free tier (primary) + EasyOCR fallback |
| Mobile interaction | Real-time scan (camera → instant result) + Offline queue (sync when online) |
| Compliance model | Checklist hard fails (missing MRP = auto non-compliant) + weighted score (0–100) |
| User roles | Field Inspector + Admin (two roles for MVP) |
| Product catalog | Pre-loaded catalog (CSV import) + scan-based new product registration |
| Reports | Annotated PDF + Excel (editable) + DOCX (editable with notes) |

---

## 6. Technology Stack

### Backend
| Component | Technology | Reason |
|---|---|---|
| API Framework | **FastAPI** (Python) | Async, fast, auto OpenAPI docs, excellent OCR/ML lib support |
| Database | **PostgreSQL** | Relational, robust, open source, full-text search via tsvector |
| ORM | **SQLAlchemy** + **Alembic** | Migrations, type safety |
| Object Storage | **MinIO** | Open source S3-compatible, runs locally in Docker |
| OCR Primary | **Google Cloud Vision API** (free: 1000 units/month) | Best accuracy for dense document text |
| OCR Fallback | **EasyOCR** (en + hi) | Open source, handles Devanagari/Hindi |
| Image Processing | **Pillow** + **OpenCV** | Preprocessing, deskewing, annotation, bounding box rendering |
| PDF Generation | **WeasyPrint** | HTML/CSS to PDF, supports complex layouts |
| Excel Generation | **openpyxl** | Excel files with conditional formatting |
| DOCX Generation | **python-docx** | Editable Word documents |
| Auth | **JWT** (python-jose + passlib/bcrypt) | Stateless, role-based |
| Rate Limiting | **slowapi** | FastAPI-compatible rate limiter |
| Web Scraping | **httpx** + **BeautifulSoup4** | E-commerce URL scanner |
| Logging | **structlog** | Structured JSON logging |
| Env Management | **python-dotenv** | .env file management |

### Frontend (Web)
| Component | Technology |
|---|---|
| Framework | **React** (Vite) |
| Styling | **TailwindCSS** |
| Charts | **Recharts** |
| HTTP Client | **Axios** |
| Routing | **React Router v6** |
| State | **Zustand** (lightweight) |
| PDF Viewer | **react-pdf** |

### Mobile
| Component | Technology |
|---|---|
| Framework | **React Native** (Expo SDK) |
| Navigation | **React Navigation** (stack + tabs) |
| Camera | **expo-camera** |
| Secure Storage | **expo-secure-store** (JWT) |
| Offline Storage | **AsyncStorage** |
| Network Detection | **@react-native-community/netinfo** |
| Haptics | **expo-haptics** |

### Infrastructure
| Component | Technology |
|---|---|
| Containerisation | **Docker** + **Docker Compose** |
| Reverse Proxy | **Nginx** (production config included) |
| Cache / Queue | **Redis** (for background jobs) |
| CI/CD ready | Pre-commit hooks (black, flake8, isort, eslint) |

---

## 7. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│  ┌─────────────────────────┐    ┌──────────────────────────┐   │
│  │   Web App (React)       │    │  Mobile App (Expo RN)    │   │
│  │  - Admin Dashboard      │    │  - Camera Scan           │   │
│  │  - Inspector View       │    │  - Offline Queue         │   │
│  │  - URL Scanner          │    │  - Inspection History    │   │
│  │  - Report Downloads     │    │  - Real-time Results     │   │
│  └────────────┬────────────┘    └───────────┬──────────────┘   │
└───────────────┼─────────────────────────────┼───────────────────┘
                │ HTTPS / REST API             │ HTTPS / REST API
┌───────────────▼─────────────────────────────▼───────────────────┐
│                    BACKEND (FastAPI)                             │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Auth Layer  │  │  API Router  │  │   Rate Limiter         │ │
│  │  JWT + RBAC  │  │  (FastAPI)   │  │   (slowapi)            │ │
│  └─────────────┘  └──────┬───────┘  └────────────────────────┘ │
│                           │                                     │
│         ┌─────────────────┼──────────────────────┐             │
│         │                 │                       │             │
│  ┌──────▼──────┐  ┌───────▼───────┐  ┌──────────▼──────────┐  │
│  │ OCR Service │  │ Compliance    │  │  Report Generator   │  │
│  │             │  │ Rule Engine   │  │                     │  │
│  │ GCV API     │  │ - Presence    │  │  WeasyPrint (PDF)   │  │
│  │   ↓ fallback│  │ - Font Size   │  │  openpyxl (Excel)   │  │
│  │ EasyOCR     │  │ - Whitespace  │  │  python-docx (DOCX) │  │
│  │ (en + hi)   │  │ - Pack Size   │  │                     │  │
│  └─────────────┘  │ - MRP/Sticker │  └─────────────────────┘  │
│                   │ - Multilang   │                             │
│  ┌─────────────┐  │ - Citation    │  ┌─────────────────────┐   │
│  │  Image      │  │ - Penalty Calc│  │  E-commerce         │   │
│  │  Processing │  └───────────────┘  │  URL Scanner        │   │
│  │  (Pillow +  │                     │  (httpx + BS4)      │   │
│  │   OpenCV)   │                     └─────────────────────┘   │
│  └─────────────┘                                               │
│                                                                 │
│         ┌──────────────────────────────────────────┐           │
│         │              DATA LAYER                  │           │
│         │  ┌─────────────────┐  ┌───────────────┐  │           │
│         │  │   PostgreSQL    │  │     MinIO     │  │           │
│         │  │  - Users        │  │  - Original   │  │           │
│         │  │  - Products     │  │    Images     │  │           │
│         │  │  - Manufacturers│  │  - Annotated  │  │           │
│         │  │  - Inspections  │  │    Images     │  │           │
│         │  │  - Violations   │  │  - Reports    │  │           │
│         │  │  - OCR Results  │  │    (PDF/XLSX) │  │           │
│         │  └─────────────────┘  └───────────────┘  │           │
│         └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Data Models

### Users
```
id, name, email, hashed_password, role (inspector|admin),
state, district, is_active, created_at, updated_at
```

### Manufacturers
```
id, name, registered_address, registration_number,
states_operating (array), created_at, updated_at
```

### Violation Records (cross-state registry)
```
id, manufacturer_id, inspection_id, state, offence_type,
penalty_tier (first|second|subsequent), date, created_at
```

### Products
```
id, name, generic_name, brand, category, barcode,
manufacturer_id, standard_pack_sizes (JSON),
is_schedule_ii_commodity (bool), registered_by (user_id),
image_url, created_at, updated_at
```

### Inspections
```
id, product_id, inspector_id, state, source (camera|upload|url),
source_url (nullable), image_url, annotated_image_url,
ocr_result (JSON), compliance_result (JSON), score (0-100),
status (compliant|non_compliant|pending), hard_fail_triggered (bool),
penalty_tier, estimated_penalty_min, estimated_penalty_max,
created_at, updated_at
```

### OCR Results (stored in inspection.ocr_result JSON)
```json
{
  "raw_text": "full extracted string",
  "blocks": [
    {
      "text": "MRP ₹45.00",
      "bounding_box": {"x": 10, "y": 200, "width": 80, "height": 12},
      "confidence": 0.98,
      "estimated_font_height_mm": 2.3
    }
  ],
  "image_dpi": 150,
  "image_width_px": 1200,
  "image_height_px": 800
}
```

### Compliance Results (stored in inspection.compliance_result JSON)
```json
{
  "overall_score": 72,
  "status": "non_compliant",
  "hard_fail_triggered": true,
  "declarations": [
    {
      "field": "mrp",
      "status": "fail",
      "hard_fail": true,
      "extracted_value": "MRP 45",
      "expected_format": "MRP ₹XX.XX Inclusive of all taxes",
      "issue": "Missing currency symbol and 'Inclusive of all taxes' text",
      "rule_reference": "Rule 6(c)",
      "explanation": "The MRP must include the ₹ symbol and the phrase 'Inclusive of all taxes'. Example: MRP ₹45.00 Inclusive of all taxes",
      "weight": 5,
      "score_contribution": 0
    }
  ],
  "advanced_checks": {
    "font_size_violations": [...],
    "whitespace_violations": [...],
    "sticker_fraud_detected": false,
    "pack_size_violation": false,
    "multilingual_present": true
  },
  "penalty": {
    "tier": "second",
    "applicable_section": "Section 36(1), Legal Metrology Act 2009",
    "estimated_range": "₹50,000",
    "note": "Manufacturer has 1 prior violation on record (Maharashtra, 2024-03)"
  }
}
```

---

## 9. API Endpoint Summary

### Auth
- `POST /auth/register` — Admin only: create user
- `POST /auth/login` — Returns JWT access + refresh tokens
- `POST /auth/refresh` — Refresh access token
- `GET /auth/me` — Current user profile

### Users (Admin only)
- `GET /users` — List all users
- `PATCH /users/{id}` — Update user (deactivate, change role)

### Manufacturers
- `POST /manufacturers` — Create manufacturer
- `GET /manufacturers` — List with search
- `GET /manufacturers/{id}` — Get with full cross-state violation history
- `POST /manufacturers/bulk-import` — CSV upload

### Products
- `POST /products` — Create product
- `GET /products` — List with search (name, brand, barcode, category)
- `GET /products/{id}` — Get product with scan history
- `POST /products/bulk-import` — CSV upload (Admin)
- `PATCH /products/{id}` — Update

### Inspections
- `POST /inspections` — Create inspection (image upload → full pipeline)
- `POST /inspections/url-scan` — E-commerce URL scan
- `GET /inspections` — List with filters (product, inspector, state, date range, status, score range)
- `GET /inspections/{id}` — Get full inspection record
- `GET /inspections/{id}/report?format=pdf|xlsx|docx` — Download report
- `GET /inspections/{id}/annotated-image` — Get annotated label image

### Dashboard
- `GET /dashboard/summary` — Cards: total inspections, compliance rate, top violations
- `GET /dashboard/trends` — Compliance rate over time (by day/week/month)
- `GET /dashboard/violations` — Violation frequency by declaration type
- `GET /dashboard/top-offenders` — Manufacturers ranked by violation count

### Health
- `GET /health` — Service status

---

## 10. Compliance Rule Engine Design

### Rule Structure (YAML config)
```yaml
- field: mrp
  label: "Maximum Retail Price"
  rule_reference: "Rule 6(c)"
  patterns:
    - "(MRP|Maximum Retail Price)\\s*[₹Rs\\.INR]+\\s*\\d+\\.\\d{2}"
    - "inclusive of all taxes"
  hard_fail: true
  weight: 5
  violation_description: "MRP not declared in prescribed format"
  plain_language_explanation: >
    Every packaged product must show MRP as:
    'MRP ₹XX.XX Inclusive of all taxes'.
    The currency symbol (₹/Rs./INR) and the phrase
    'Inclusive of all taxes' are mandatory.
```

### Engine Processing Flow
```
OCR Text Blocks
      │
      ▼
1. Presence Check — Does each required field appear?
      │
      ▼
2. Format Check — Does the found value match the regex pattern?
      │
      ▼
3. Font Size Check — Is the bounding box height ≥ required mm?
      │
      ▼
4. Whitespace Check — Is the clearance zone around quantity clear?
      │
      ▼
5. Pack Size Check — Is the declared quantity in Schedule II list?
      │
      ▼
6. MRP Sticker Check — Are multiple MRP values present?
      │
      ▼
7. Multilingual Check — Is Hindi/regional text present?
      │
      ▼
8. Score Calculation
   score = (sum of weights of passing checks / total weight) × 100
   if any hard_fail == true → status = NON_COMPLIANT regardless of score
      │
      ▼
9. Penalty Calculation
   query manufacturer violation history across all states
   → determine tier (first/second/subsequent)
   → map to penalty range from Section 36
      │
      ▼
Structured Compliance Result JSON
```

### Scoring
- Score 90–100: Compliant
- Score 70–89: Partially Compliant (minor violations)
- Score 50–69: Non-Compliant (significant violations)
- Score < 50: Severely Non-Compliant
- Any hard fail: Non-Compliant regardless of score

---

## 11. Full Task Breakdown

| # | Task | Description | Status |
|---|---|---|---|
| 1 | Project Scaffold | Monorepo setup, Docker Compose, PostgreSQL, MinIO, Redis, base FastAPI, health check | ⬜ Not Started |
| 2 | Auth & Roles | JWT auth, bcrypt passwords, role-based guards (Inspector/Admin), user management | ⬜ Not Started |
| 3 | Manufacturer Registry | Manufacturer CRUD, cross-state violation registry, offence tier calculator | ⬜ Not Started |
| 4 | Product Catalog | Product CRUD, Schedule II pack sizes, bulk CSV import, barcode search | ⬜ Not Started |
| 5 | OCR Service | Image preprocessing (Pillow/OpenCV), GCV API primary, EasyOCR fallback, DPI extraction, font height estimation | ⬜ Not Started |
| 6 | Core Compliance Engine | Rule 6 declaration checks, MRP format validation, SI unit check, date format check, scoring, citations | ⬜ Not Started |
| 7 | Advanced Checks | Font size estimator (Rule 7/8), whitespace clearance (Rule 8), sticker fraud detector, pack size validator, multilingual checker | ⬜ Not Started |
| 8 | Inspection Workflow | End-to-end pipeline, annotated image generation (Pillow), penalty calculator, inspection persistence | ⬜ Not Started |
| 9 | E-commerce URL Scanner | httpx + BeautifulSoup scraper, image extraction from listings, full compliance pipeline on listing | ⬜ Not Started |
| 10 | Report Generation | Annotated PDF (WeasyPrint), Excel with conditional formatting (openpyxl), editable DOCX (python-docx) | ⬜ Not Started |
| 11 | Web Dashboard | React + Tailwind, admin dashboard (charts, tables), inspector view (upload, result, history), role-gated routing | ⬜ Not Started |
| 12 | Mobile App | Expo React Native, camera scan, offline queue, real-time results, inspection history, haptics | ⬜ Not Started |
| 13 | Search & Hardening | Full-text search (PostgreSQL tsvector), filters, pagination, rate limiting, security hardening, deployment docs | ⬜ Not Started |

---

## 12. Folder Structure

```
NIRI/
├── README.md                        ← THIS FILE (project memory)
│
├── backend/
│   ├── app/
│   │   ├── main.py                  ← FastAPI app entry point
│   │   ├── config.py                ← Settings (env vars)
│   │   ├── database.py              ← DB session, engine
│   │   ├── models/                  ← SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── manufacturer.py
│   │   │   ├── product.py
│   │   │   ├── inspection.py
│   │   │   └── violation.py
│   │   ├── schemas/                 ← Pydantic request/response schemas
│   │   ├── routers/                 ← FastAPI routers (one per domain)
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── manufacturers.py
│   │   │   ├── products.py
│   │   │   ├── inspections.py
│   │   │   └── dashboard.py
│   │   ├── services/                ← Business logic
│   │   │   ├── ocr_service.py       ← GCV + EasyOCR + preprocessing
│   │   │   ├── compliance_engine.py ← Full rule engine
│   │   │   ├── image_annotator.py   ← Pillow annotation
│   │   │   ├── report_generator.py  ← PDF/Excel/DOCX
│   │   │   ├── url_scanner.py       ← E-commerce scraper
│   │   │   └── penalty_calculator.py
│   │   ├── rules/
│   │   │   ├── declarations.yaml    ← Rule config for all declarations
│   │   │   └── schedule_ii.yaml     ← Standard pack sizes data
│   │   └── utils/
│   │       ├── auth.py              ← JWT helpers
│   │       ├── storage.py           ← MinIO client
│   │       └── font_estimator.py    ← Pixel → mm calculation
│   ├── alembic/                     ← DB migrations
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── web/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx        ← Admin dashboard
│   │   │   ├── InspectorHome.jsx
│   │   │   ├── InspectionResult.jsx
│   │   │   ├── InspectionHistory.jsx
│   │   │   ├── Products.jsx
│   │   │   ├── Manufacturers.jsx
│   │   │   └── Users.jsx
│   │   ├── components/
│   │   │   ├── ComplianceScore.jsx  ← Score gauge
│   │   │   ├── DeclarationChecklist.jsx
│   │   │   ├── AnnotatedImage.jsx
│   │   │   ├── ViolationCard.jsx
│   │   │   └── charts/
│   │   ├── store/                   ← Zustand state
│   │   ├── api/                     ← Axios API client
│   │   └── utils/
│   ├── package.json
│   └── Dockerfile
│
├── mobile/
│   ├── app/
│   │   ├── screens/
│   │   │   ├── LoginScreen.jsx
│   │   │   ├── HomeScreen.jsx
│   │   │   ├── CameraScanScreen.jsx
│   │   │   ├── ResultScreen.jsx
│   │   │   └── HistoryScreen.jsx
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   └── offlineQueue.js      ← AsyncStorage queue + sync
│   │   └── utils/
│   ├── app.json
│   └── package.json
│
├── docker-compose.yml               ← Full stack orchestration
├── docker-compose.dev.yml           ← Dev overrides
├── nginx.conf                       ← Reverse proxy config
└── .env.example                     ← Environment variable template
```

---

## 13. Why This Solution Wins

### Versus a basic compliance checker:

| Feature | Basic Checker | NirikshakAI |
|---|---|---|
| Declaration presence check | ✅ | ✅ |
| MRP format validation | Partial | ✅ Full regex + symbol + decimal check |
| Font size measurement | ❌ | ✅ Pixel → mm via DPI |
| Whitespace clearance (Rule 8) | ❌ | ✅ Bounding box clearance zone analysis |
| Cross-state offence tracking | ❌ | ✅ National manufacturer violation registry |
| MRP sticker fraud detection | ❌ | ✅ Multi-price heuristic detector |
| Standard pack size (Schedule II) | ❌ | ✅ Full Schedule II validator |
| E-commerce label scanning | ❌ | ✅ URL-based product listing scanner |
| Penalty calculation | ❌ | ✅ Automated with legal references |
| Inspector training | ❌ | ✅ Plain-language rule explanations per violation |
| Hindi/multilingual detection | ❌ | ✅ EasyOCR Devanagari support |
| Annotated label images | Basic | ✅ Colour-coded with rule references |
| Report formats | PDF only | ✅ PDF + Excel + editable DOCX |

### Key differentiators for judges:
1. **Systemic thinking** — addresses root causes of enforcement failure, not just label scanning
2. **Legal depth** — every feature maps to a specific rule clause with the exact citation
3. **Cross-state registry** — solves the documented gap where manufacturers exploit per-state tracking
4. **E-commerce enforcement** — addresses the massive online marketplace compliance gap
5. **Inspector empowerment** — plain-language explanations turn the tool into a training aid
6. **Production-ready** — Docker Compose, role-based auth, rate limiting, security hardening

---

## 14. Progress Tracker

Update this section as tasks are completed.

```
Task 1  — Project Scaffold          [x] COMPLETE
Task 2  — Auth & Roles              [ ] Not Started
Task 3  — Manufacturer Registry     [ ] Not Started
Task 4  — Product Catalog           [ ] Not Started
Task 5  — OCR Service               [ ] Not Started
Task 6  — Core Compliance Engine    [ ] Not Started
Task 7  — Advanced Checks           [ ] Not Started
Task 8  — Inspection Workflow       [ ] Not Started
Task 9  — E-commerce URL Scanner    [ ] Not Started
Task 10 — Report Generation         [ ] Not Started
Task 11 — Web Dashboard             [ ] Not Started
Task 12 — Mobile App                [ ] Not Started
Task 13 — Search & Hardening        [ ] Not Started
```

**How to update:** Change `[ ]` to `[x]` when a task is complete.

---

## Task 1 — What Was Built

All files created under `NIRI/`. Stack is bootable with a single command.

| File / Folder | What it does |
|---|---|
| `docker-compose.yml` | PostgreSQL 15, MinIO (+ bucket init), Redis 7, FastAPI backend — all networked |
| `docker-compose.dev.yml` | Dev overrides: hot reload, direct port exposure, EasyOCR model volume |
| `docker-compose.prod.yml` | Production overrides: adds Nginx reverse proxy |
| `.env.example` | All environment variables documented with safe defaults |
| `.gitignore` | Protects `.env`, `node_modules`, EasyOCR weights, pycache |
| `nginx.conf` | Reverse proxy: `/api/*` → backend, `/` → web, rate limiting, 20MB upload, SPA fallback |
| `backend/app/main.py` | FastAPI app: CORS, structlog, startup/shutdown, health router |
| `backend/app/config.py` | Pydantic-settings: all env vars with `lru_cache` singleton |
| `backend/app/database.py` | SQLAlchemy engine + `get_db` dependency + `check_db_connection` |
| `backend/app/routers/health.py` | `GET /health` — checks DB + Redis + MinIO, returns uptime |
| `backend/app/models/` | 5 ORM models: User, Manufacturer, ViolationRecord, Product, Inspection |
| `backend/alembic/` | Full Alembic setup: `env.py`, `script.py.mako`, initial migration `0001` |
| `backend/alembic/versions/0001` | Creates all 5 tables + 4 enums + all indexes in one migration |
| `backend/app/utils/seed.py` | Seeds admin user + 18 Schedule II commodity entries on first boot |
| `backend/requirements.txt` | All pinned Python dependencies |
| `backend/Dockerfile` | Multi-stage build: lean `python:3.11-slim` runtime, non-root user |
| `web/` | React 18 + Vite + TailwindCSS scaffold: routing, auth store, Axios client |
| `web/src/App.jsx` | Full route tree with `ProtectedRoute` and role-based guards |
| `web/src/store/authStore.js` | Zustand persisted auth store (token + user) |
| `web/src/api/client.js` | Axios with JWT injection + auto 401 refresh |
| `mobile/` | Expo 51 scaffold: React Navigation, SecureStore, AsyncStorage |
| `mobile/app/services/offlineQueue.js` | Full offline queue: enqueue, sync with NetInfo, retry on fail |
| `mobile/app/screens/` | LoginScreen (full), HomeScreen (full), placeholder screens for Task 12 |

**To start the full stack in development:**
```bash
cp .env.example .env
# Fill in GOOGLE_CLOUD_VISION_API_KEY in .env
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Services available:
- API + Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- MinIO console: http://localhost:9001 (user: minioadmin / minioadmin123)

---

## Environment Variables Reference

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/NirikshakAI

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_IMAGES=label-images
MINIO_BUCKET_REPORTS=reports

# Google Cloud Vision
GOOGLE_CLOUD_VISION_API_KEY=your_api_key_here

# JWT
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379

# App
APP_ENV=development
APP_PORT=8000
ADMIN_EMAIL=admin@NirikshakAI.gov.in
ADMIN_PASSWORD=changeme
```

---

*Last updated: Task 1 complete — project scaffold fully built and bootable.*
*Next: Task 2 — Authentication & Role-Based Access (JWT, bcrypt, Inspector/Admin roles)*
*Project: LabelGuard — Legal Metrology Compliance Checker*
*Event: Hackathon / Competition submission*
