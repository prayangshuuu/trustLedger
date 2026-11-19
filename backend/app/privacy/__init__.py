"""Privacy and consent management package."""

from app.privacy.consent import (
    VALID_CONSENT_SOURCES,
    ConsentMissingError,
    InvalidConsentSourceError,
    get_active_consents,
    grant_consent,
    has_consent,
    require_consent,
    revoke_consent,
)
from app.privacy.deletion import delete_user_data

__all__ = [
    "VALID_CONSENT_SOURCES",
    "ConsentMissingError",
    "InvalidConsentSourceError",
    "delete_user_data",
    "get_active_consents",
    "grant_consent",
    "has_consent",
    "require_consent",
    "revoke_consent",
]
