"""
Application configuration.
All settings are loaded from environment variables (via .env file).
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "LabelGuard"
    app_env: str = "development"
    app_port: int = 8000
    secret_key: str = "change_this_in_production"

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = "postgresql://labelguard:labelguard_pass@db:5432/labelguard"

    # ── MinIO ────────────────────────────────────────────────────────
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket_images: str = "label-images"
    minio_bucket_reports: str = "reports"
    minio_secure: bool = False

    # ── Redis ────────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── JWT ──────────────────────────────────────────────────────────
    jwt_secret_key: str = "change_this_jwt_secret_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # ── Google Cloud Vision ──────────────────────────────────────────
    google_cloud_vision_api_key: str = ""

    # ── Seed Admin ───────────────────────────────────────────────────
    admin_name: str = "Admin"
    admin_email: str = "admin@labelguard.gov.in"
    admin_password: str = "Admin@1234"

    # ── CORS ─────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Use as a FastAPI dependency: settings = Depends(get_settings)
    """
    return Settings()


# Module-level singleton for non-DI usage
settings = get_settings()
