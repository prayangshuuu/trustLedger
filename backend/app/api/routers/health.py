"""Health, readiness, and version introspection endpoints."""

import os
import subprocess
from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.config import get_settings
from app.core.model import get_model_version

router = APIRouter(tags=["System"])


def get_git_sha() -> str:
    """Extract current git commit SHA with fallback."""
    env_sha = os.getenv("GIT_SHA")
    if env_sha:
        return env_sha[:12]
    try:
        res = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2.0,
        )
        return res.strip()[:12]
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def redis_status() -> str:
    """connected | unavailable | not_configured (Redis is optional for the API)."""
    url = get_settings().REDIS_URL
    if not url:
        return "not_configured"
    try:
        import redis

        client = redis.Redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=0.5)
        try:
            return "connected" if client.ping() else "unavailable"
        finally:
            client.close()
    except Exception:  # noqa: BLE001 - health must never raise
        return "unavailable"


@router.get("/health", summary="Service Health Check")
def health(db: DbSession) -> dict[str, str]:
    """Return application and database health status."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db_status = "disconnected"

    return {
        "status": "ok",
        "app": "trustledger",
        "database": db_status,
        "redis": redis_status(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/version", summary="Model and API Version")
def version() -> dict[str, str]:
    """Return model version hash, git commit SHA, and core version."""
    return {
        "app_version": "1.0.0",
        "model_version": get_model_version(),
        "git_sha": get_git_sha(),
    }
