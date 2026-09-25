"""
Health check router.
GET /health — returns status of app, database, MinIO, and Redis.
Used by Docker healthcheck and monitoring.
"""

import time

import redis as redis_lib
from fastapi import APIRouter
from minio import Minio
from minio.error import S3Error

from app.config import settings
from app.database import check_db_connection

router = APIRouter(tags=["Health"])

# Record when the app started (for uptime reporting)
_start_time = time.time()


def _check_redis() -> bool:
    try:
        # Strip redis:// prefix for the redis-py client
        url = settings.redis_url
        client = redis_lib.from_url(url, socket_connect_timeout=2)
        client.ping()
        return True
    except Exception:
        return False


def _check_minio() -> bool:
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        # list_buckets is a lightweight operation to verify connectivity
        client.list_buckets()
        return True
    except (S3Error, Exception):
        return False


@router.get("/health", summary="System health check")
def health_check():
    """
    Returns the health status of all backend services.
    Overall status is 'healthy' only if all services are up.
    """
    db_ok = check_db_connection()
    redis_ok = _check_redis()
    minio_ok = _check_minio()

    all_ok = db_ok and redis_ok and minio_ok
    uptime_seconds = round(time.time() - _start_time, 1)

    return {
        "status": "healthy" if all_ok else "degraded",
        "app": settings.app_name,
        "environment": settings.app_env,
        "uptime_seconds": uptime_seconds,
        "services": {
            "database": "up" if db_ok else "down",
            "redis": "up" if redis_ok else "down",
            "minio": "up" if minio_ok else "down",
        },
    }
