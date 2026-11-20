"""FastAPI dependencies for database access and authentication."""

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.security import verify_token


def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str | None:
    """Validate lender/partner API key header."""
    settings = get_settings()
    configured_keys = [k.strip() for k in settings.API_KEYS.split(",") if k.strip()]

    if not configured_keys:
        # Development mode without mandatory API key restrictions
        return x_api_key

    if not x_api_key or not any(hmac.compare_digest(x_api_key, k) for k in configured_keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return x_api_key


def get_current_user_id(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    """Borrower identity from a signed session token (``Authorization: Bearer tl1...``)."""
    if authorization and authorization.startswith("Bearer "):
        user_id = verify_token(authorization[7:].strip())
        if user_id:
            return user_id
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing, invalid or expired borrower session token",
    )


def authorize_user_access(
    user_id: str,
    authorization: str | None,
    x_api_key: str | None,
) -> None:
    """Allow the borrower themself (session token) or a lender/partner with a valid API key."""
    if authorization and authorization.startswith("Bearer "):
        if verify_token(authorization[7:].strip()) == user_id:
            return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Session token does not match this user")
    verify_api_key(x_api_key)
    if not x_api_key and get_settings().API_KEYS.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session token or X-API-Key required")


# Type aliases for clean router signatures
DbSession = Annotated[Session, Depends(get_db)]
ApiKeyAuth = Annotated[str | None, Depends(verify_api_key)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
