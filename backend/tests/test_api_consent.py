"""Integration tests for consent management and Right-to-be-Forgotten endpoints."""

from collections.abc import Generator

import pytest
from app.db.base import Base
from app.db.models import User
from app.db.session import create_app_engine, get_db
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide isolated SQLite session."""
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client using db_session fixture."""
    app_instance = create_app()
    app_instance.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app_instance) as tc:
        yield tc


@pytest.fixture
def sample_user(db_session: Session) -> User:
    """Create a test user in DB."""
    user = User(
        phone_hash="hash_consent_api_test",
        gender="F",
        region="urban",
        division="Dhaka",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_grant_consent_success(client: TestClient, sample_user: User) -> None:
    """Verify POST /consent successfully grants consent."""
    payload = {"user_id": sample_user.id, "source": "sms"}
    resp = client.post("/consent", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "granted"
    assert data["user_id"] == sample_user.id
    assert data["source"] == "sms"


def test_grant_consent_invalid_source(client: TestClient, sample_user: User) -> None:
    """Verify POST /consent rejects invalid source with 400 Bad Request."""
    payload = {"user_id": sample_user.id, "source": "invalid_source"}
    resp = client.post("/consent", json=payload)
    assert resp.status_code == 400
    assert "Invalid consent source" in resp.json()["detail"]


def test_revoke_consent(client: TestClient, sample_user: User) -> None:
    """Verify DELETE /consent/{source} revokes active consent."""
    client.post("/consent", json={"user_id": sample_user.id, "source": "bills"})

    resp = client.delete(f"/consent/bills?user_id={sample_user.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "revoked"
    assert data["source"] == "bills"


def test_delete_me(client: TestClient, sample_user: User) -> None:
    """Verify DELETE /me purges user data with 200 OK."""
    headers = {"Authorization": f"Bearer {sample_user.id}"}
    resp = client.delete("/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # Subsequent deletion returns 404
    resp2 = client.delete("/me", headers=headers)
    assert resp2.status_code == 404
