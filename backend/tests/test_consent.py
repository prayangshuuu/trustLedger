"""Unit tests for consent management, granting, revocation, and gating."""

import pytest
from app.db.base import Base
from app.db.models import User
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
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def session() -> Session:
    """Provide an isolated in-memory SQLite session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    sess = session_factory()
    try:
        yield sess
    finally:
        sess.close()


@pytest.fixture
def test_user(session: Session) -> User:
    """Create a persistent test user."""
    user = User(
        phone_hash="user_consent_test_hash",
        gender="F",
        region="urban",
        division="Dhaka",
    )
    session.add(user)
    session.commit()
    return user


def test_grant_and_has_consent(session: Session, test_user: User) -> None:
    """Verify granting consent and checking active state."""
    assert not has_consent(session, test_user.id, "sms")

    consent = grant_consent(session, test_user.id, "sms")
    assert consent.source == "sms"
    assert consent.revoked_at is None
    assert has_consent(session, test_user.id, "sms")
    assert "sms" in get_active_consents(session, test_user.id)


def test_revoke_consent(session: Session, test_user: User) -> None:
    """Verify revoking consent marks it revoked and disables active status."""
    grant_consent(session, test_user.id, "bills")
    assert has_consent(session, test_user.id, "bills")

    revoked = revoke_consent(session, test_user.id, "bills")
    assert revoked is True
    assert not has_consent(session, test_user.id, "bills")
    assert "bills" not in get_active_consents(session, test_user.id)

    # Second revoke returns False
    assert revoke_consent(session, test_user.id, "bills") is False


def test_regrant_consent(session: Session, test_user: User) -> None:
    """Verify re-granting an already-revoked consent reactivates it."""
    grant_consent(session, test_user.id, "recharge")
    revoke_consent(session, test_user.id, "recharge")
    assert not has_consent(session, test_user.id, "recharge")

    # Re-grant
    grant_consent(session, test_user.id, "recharge")
    assert has_consent(session, test_user.id, "recharge")


def test_require_consent_success_and_failure(session: Session, test_user: User) -> None:
    """Verify require_consent permits when active and raises ConsentMissingError when absent."""
    grant_consent(session, test_user.id, "sms")
    grant_consent(session, test_user.id, "bills")

    # Multiple active consents pass
    require_consent(session, test_user.id, ["sms", "bills"])
    require_consent(session, test_user.id, "sms")

    # Missing consent raises ConsentMissingError
    with pytest.raises(ConsentMissingError, match="lacks active consent for required source 'ocr'"):
        require_consent(session, test_user.id, ["sms", "ocr"])

    # Revoked consent raises ConsentMissingError
    revoke_consent(session, test_user.id, "bills")
    with pytest.raises(
        ConsentMissingError, match="lacks active consent for required source 'bills'"
    ):
        require_consent(session, test_user.id, "bills")


def test_invalid_consent_source(session: Session, test_user: User) -> None:
    """Verify unrecognized consent source raises InvalidConsentSourceError."""
    with pytest.raises(InvalidConsentSourceError, match="Invalid consent source 'invalid_src'"):
        grant_consent(session, test_user.id, "invalid_src")

    with pytest.raises(InvalidConsentSourceError):
        has_consent(session, test_user.id, "invalid_src")

    with pytest.raises(InvalidConsentSourceError):
        revoke_consent(session, test_user.id, "invalid_src")


def test_all_valid_sources(session: Session, test_user: User) -> None:
    """Verify all valid consent sources from PLAN_CONTEXT can be granted."""
    for src in VALID_CONSENT_SOURCES:
        grant_consent(session, test_user.id, src)
        assert has_consent(session, test_user.id, src)

    active = get_active_consents(session, test_user.id)
    assert set(active) == set(VALID_CONSENT_SOURCES)
