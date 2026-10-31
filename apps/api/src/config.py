"""ResearchOS API — Configuration module."""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "EquitIQ"
    app_env: str = "development"
    data_mode: str = "demo"  # demo | official | licensed
    secret_key: str = "change-me-in-production"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://researchos:researchos_dev@localhost:5432/researchos"
    database_url_sync: str = "postgresql://researchos:researchos_dev@localhost:5432/researchos"

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_async_database_url(cls, v: str) -> str:
        if not v:
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("database_url_sync", mode="before")
    @classmethod
    def assemble_sync_database_url(cls, v: str) -> str:
        if not v:
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        if v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql+asyncpg://", "postgresql://", 1)
        return v

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # S3 / MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "researchos-documents"
    s3_region: str = "us-east-1"

    # Auth
    jwt_secret_key: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    demo_user_email: str = "demo@researchos.dev"
    demo_user_password: str = "demo123456"

    # AI
    ai_provider: str = "gemini"  # mock | openai | gemini
    ai_provider_api_key: Optional[str] = None
    ai_provider_base_url: Optional[str] = None
    ai_default_model: str = "gemini-1.5-flash"
    ai_embedding_model: str = "text-embedding-004"
    gemini_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    sec_user_agent: str = "EquitIQResearch research@equitiq.com"

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_search_per_minute: int = 30

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
