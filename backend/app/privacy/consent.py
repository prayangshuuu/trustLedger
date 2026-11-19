"""Consent management and verification services.

Implements strict consent checks:
- Tracks consent per source: sms | bills | recharge | ocr | bhorsha
- Enforces consent verification before scoring or data processing
- Supports granting, revoking, and querying active consents
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Consent, get_utc_now

VALID_CONSENT_SOURCES: tuple[str, ...] = ("sms", "bills", "recharge", "ocr", "bhorsha")


class ConsentMissingError(PermissionError):
    """Raised when an applicant has not granted or has revoked mandatory data consent."""


class InvalidConsentSourceError(ValueError):
    """Raised when an unrecognized consent source is specified."""


def validate_source(source: str) -> None:
    """Validate that the consent source is one of the approved sources."""
    if source not in VALID_CONSENT_SOURCES:
        raise InvalidConsentSourceError(
            f"Invalid consent source '{source}'. Expected one of: {', '.join(VALID_CONSENT_SOURCES)}"
        )


def grant_consent(session: Session, user_id: str, source: str) -> Consent:
    """Grant or reactivate consent for a given user and data source."""
    validate_source(source)

    stmt = (
        select(Consent)
        .where(Consent.user_id == user_id, Consent.source == source)
        .order_by(Consent.granted_at.desc())
    )
    existing = session.scalars(stmt).first()

    now = get_utc_now()
    if existing:
        existing.granted_at = now
        existing.revoked_at = None
        consent = existing
    else:
        consent = Consent(
            user_id=user_id,
            source=source,
            granted_at=now,
            revoked_at=None,
        )
        session.add(consent)

    session.commit()
    session.refresh(consent)
    return consent


def revoke_consent(session: Session, user_id: str, source: str) -> bool:
    """Revoke active consent for a given user and data source."""
    validate_source(source)

    stmt = select(Consent).where(
        Consent.user_id == user_id,
        Consent.source == source,
        Consent.revoked_at.is_(None),
    )
    consents = list(session.scalars(stmt).all())
    if not consents:
        return False

    now = get_utc_now()
    for consent in consents:
        consent.revoked_at = now

    session.commit()
    return True


def has_consent(session: Session, user_id: str, source: str) -> bool:
    """Check whether a user has active, unrevoked consent for a specific source."""
    validate_source(source)

    stmt = select(Consent.id).where(
        Consent.user_id == user_id,
        Consent.source == source,
        Consent.revoked_at.is_(None),
    )
    result = session.scalars(stmt).first()
    return result is not None


def get_active_consents(session: Session, user_id: str) -> list[str]:
    """Retrieve all active consent sources for a user."""
    stmt = (
        select(Consent.source)
        .where(
            Consent.user_id == user_id,
            Consent.revoked_at.is_(None),
        )
        .distinct()
    )
    return list(session.scalars(stmt).all())


def require_consent(
    session: Session,
    user_id: str,
    sources: str | Sequence[str],
) -> None:
    """Assert that a user has active consent for all specified sources.

    Raises:
        ConsentMissingError: If any required consent is missing or revoked.
    """
    required_list = [sources] if isinstance(sources, str) else list(sources)
    for src in required_list:
        if not has_consent(session, user_id, src):
            raise ConsentMissingError(
                f"Applicant '{user_id}' lacks active consent for required source '{src}'."
            )
