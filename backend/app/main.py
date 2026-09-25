"""
LabelGuard — FastAPI Application Entry Point

Legal Metrology (Packaged Commodities) Rules, 2011
Automated compliance checking system.
"""

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import auth, health, inspections, manufacturers, products, users

# ── Structured Logging Setup ─────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.basicConfig(
    format="%(message)s",
    level=logging.DEBUG if settings.is_development else logging.INFO,
)

logger = structlog.get_logger(__name__)

# ── FastAPI Application ───────────────────────────────────────────────────────
app = FastAPI(
    title="LabelGuard API",
    description=(
        "Automated compliance checking system for packaged commodities "
        "under the Legal Metrology (Packaged Commodities) Rules, 2011. "
        "Department of Consumer Affairs, Government of India."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)

# ── Middleware ────────────────────────────────────────────────────────────────

# CORS — allow web and mobile clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host protection (guards against Host header injection)
if not settings.is_development:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["labelguard.gov.in", "*.labelguard.gov.in", "localhost"],
    )

# ── Startup / Shutdown Events ─────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info(
        "LabelGuard API starting",
        environment=settings.app_env,
        version="1.0.0",
    )


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("LabelGuard API shutting down")


# ── Routers ───────────────────────────────────────────────────────────────────
# Health check — no prefix, no auth
app.include_router(health.router)

# Auth & user management
app.include_router(auth.router)          # prefix="/auth"
app.include_router(users.router)         # prefix="/users"

# Manufacturer registry
app.include_router(manufacturers.router) # prefix="/manufacturers"

# Product catalog
app.include_router(products.router)      # prefix="/products"

# Inspections pipeline
app.include_router(inspections.router)   # prefix="/inspections"

# Remaining API routers — registered as tasks progress:
# app.include_router(dashboard_router,     prefix="/dashboard",     tags=["Dashboard"])

# ── Root ─────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return JSONResponse(
        content={
            "message": "LabelGuard API",
            "docs": "/docs",
            "health": "/health",
        }
    )
