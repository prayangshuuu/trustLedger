"""Signed borrower session tokens: ``tl1.<user_id>.<expiry>.<hmac>``.

The app gets a token from ``POST /auth/session`` (lender/partner API key required; in production
that call sits behind phone OTP). The token is then the only way to act as that borrower.
"""

import base64
import hashlib
import hmac
import time

from app.config import get_settings

PREFIX = "tl1"
DEFAULT_TTL_SECONDS = 12 * 3600


def _secret() -> bytes:
    secret = get_settings().SESSION_SECRET
    return (secret or "trustledger-dev-session-secret").encode()


def _sign(payload: str) -> str:
    digest = hmac.new(_secret(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def issue_token(user_id: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> tuple[str, int]:
    expires = int(time.time()) + ttl_seconds
    payload = f"{PREFIX}.{user_id}.{expires}"
    return f"{payload}.{_sign(payload)}", expires


def verify_token(token: str) -> str | None:
    """Return the user id for a valid, unexpired token, else None."""
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != PREFIX:
        return None
    payload = ".".join(parts[:3])
    if not hmac.compare_digest(_sign(payload), parts[3]):
        return None
    try:
        if int(parts[2]) < time.time():
            return None
    except ValueError:
        return None
    return parts[1]
