"""Application configuration loaded from environment variables using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """TrustLedger runtime application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database & Cache
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/trustledger"
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM & AI Services (DeepSeek)
    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_OCR_URL: str = "https://api.deepseek.com/ocr"
    LLM_MODE: str = "mock"

    # Object Storage (Cloudflare R2 / S3 API)
    R2_ENDPOINT: str | None = None
    R2_ACCESS_KEY: str | None = None
    R2_SECRET_KEY: str | None = None
    R2_BUCKET: str = "trustledger"

    # Security & Authentication
    API_KEYS: str = ""

    # Application & Workflow Settings
    DEMO_MODE: bool = False
    TEMPORAL_HOST: str = "localhost:7233"
    MODEL_DIR: str = "models"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
