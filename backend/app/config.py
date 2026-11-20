"""Application configuration loaded from environment variables using pydantic-settings."""

import os
from functools import lru_cache

from pydantic import model_validator
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
    DEEPSEEK_CHAT_MODEL: str = "deepseek-chat"
    DEEPSEEK_REASONER_MODEL: str = "deepseek-reasoner"
    # OpenAI-compatible server hosting DeepSeek-OCR (e.g. vLLM), base URL without /chat/completions
    DEEPSEEK_OCR_URL: str | None = None
    DEEPSEEK_OCR_MODEL: str = "deepseek-ai/DeepSeek-OCR"
    DEEPSEEK_OCR_API_KEY: str | None = None
    OCR_BACKEND: str = "auto"  # auto | deepseek-ocr-local | tesseract | mock
    LLM_MODE: str = "mock"
    LLM_SESSION_TOKEN_BUDGET: int = 50_000

    @model_validator(mode="after")
    def _apply_live_default(self) -> "Settings":
        if "LLM_MODE" not in os.environ and self.DEEPSEEK_API_KEY and self.DEEPSEEK_API_KEY.strip():
            self.LLM_MODE = "live"
        return self

    # Object Storage (Cloudflare R2 / S3 API)
    R2_ENDPOINT: str | None = None
    R2_ACCESS_KEY: str | None = None
    R2_SECRET_KEY: str | None = None
    R2_BUCKET: str = "trustledger"
    STORAGE_ENCRYPTION_KEY: str | None = None

    # RAG
    EMBEDDINGS_MODE: str = "hash"  # hash | bge-m3
    RERANKER_MODE: str = "lexical"  # lexical | bge
    RAG_COMPRESSION: bool = False

    # Security & Authentication
    API_KEYS: str = ""
    # HMAC secret for borrower session tokens (POST /auth/session)
    SESSION_SECRET: str | None = None
    # Allowed browser origins (comma separated); "*" only for local development
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,"
        "http://localhost:8080,http://127.0.0.1:8080,http://localhost:8000,http://127.0.0.1:8000,"
        "https://app.trustledger.com,https://dashboard.trustledger.com"
    )
    RATE_LIMIT_PER_MINUTE: int = 300
    MAX_BODY_BYTES: int = 1_000_000  # JSON bodies (2,000 SMS fit comfortably)
    MAX_UPLOAD_BYTES: int = 8_000_000  # document photos

    # Application & Workflow Settings
    DEMO_MODE: bool = False
    # Built dashboard served at / (relative to the repo root); ignored if no build exists
    DASHBOARD_DIR: str = "apps/dashboard/dist"
    # Flutter web build of the borrower app, served at /app (flutter build web --base-href /app/)
    BORROWER_WEB_DIR: str = "apps/mobile/build/web"
    TEMPORAL_HOST: str = "localhost:7233"
    MODEL_DIR: str = "models"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
