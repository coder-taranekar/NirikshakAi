# ─────────────────────────────────────────────────────────────────
# LabelGuard Backend — Dockerfile
#
# Multi-stage build:
#   Stage 1 (builder): installs all Python dependencies
#   Stage 2 (runtime): lean image with only what's needed to run
#
# Usage:
#   docker build -t labelguard-backend .
#   docker run -p 8000:8000 --env-file .env labelguard-backend
# ─────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

# System dependencies required to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install WeasyPrint system dependencies (for PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /install

# Copy and install Python dependencies into /install/packages
# so the runtime stage can copy only this folder
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install/packages --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="LabelGuard Team"
LABEL description="LabelGuard API — Legal Metrology Compliance Checker"
LABEL version="1.0.0"

# Runtime system libraries (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /install/packages /usr/local

# Create non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home --shell /bin/false appuser

# Set working directory
WORKDIR /app

# Copy application source code
COPY --chown=appuser:appgroup . .

# Create directory for temporary file processing
RUN mkdir -p /app/tmp && chown appuser:appgroup /app/tmp

# Switch to non-root user
USER appuser

# Expose the API port
EXPOSE 8000

# Health check (mirrors the docker-compose healthcheck)
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Entrypoint ────────────────────────────────────────────────────
# 1. Run Alembic migrations
# 2. Run the database seeder
# 3. Start the Uvicorn server
#
# --host 0.0.0.0 required to accept connections from outside the container
# --workers 1 for MVP (increase for production)
CMD ["sh", "-c", \
     "alembic upgrade head && \
      python -m app.utils.seed && \
      uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
