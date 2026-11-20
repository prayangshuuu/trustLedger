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
    DEEPSEEK_CHAT_MODEL: str = "deepseek-chat"
    # OpenAI-compatible server hosting DeepSeek-OCR (e.g. vLLM), base URL without /chat/completions
    DEEPSEEK_OCR_URL: str | None = None
    DEEPSEEK_OCR_MODEL: str = "deepseek-ai/DeepSeek-OCR"
    DEEPSEEK_OCR_API_KEY: str | None = None
    LLM_MODE: str = "mock"

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
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    )
    RATE_LIMIT_PER_MINUTE: int = 300
    MAX_BODY_BYTES: int = 1_000_000  # JSON bodies (2,000 SMS fit comfortably)
    MAX_UPLOAD_BYTES: int = 8_000_000  # document photos

    # Application & Workflow Settings
    DEMO_MODE: bool = False
    TEMPORAL_HOST: str = "localhost:7233"
    MODEL_DIR: str = "models"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
