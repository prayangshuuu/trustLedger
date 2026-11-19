"""FastAPI dependencies for database access and authentication."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db


def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str | None:
    """Validate lender/partner API key header."""
    settings = get_settings()
    configured_keys = [k.strip() for k in settings.API_KEYS.split(",") if k.strip()]

    if not configured_keys:
        # Development mode without mandatory API key restrictions
        return x_api_key

    if not x_api_key or x_api_key not in configured_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return x_api_key


def get_current_user_id(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
) -> str:
    """Extract authenticated borrower user ID from Bearer token or X-User-ID header."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token:
            return token

    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication credentials (Bearer token or X-User-ID required)",
    )


# Type aliases for clean router signatures
DbSession = Annotated[Session, Depends(get_db)]
ApiKeyAuth = Annotated[str | None, Depends(verify_api_key)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
