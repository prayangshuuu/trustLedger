"""Integration tests for API Key and borrower authentication mechanisms."""

from collections.abc import Generator

import pytest
from app.config import Settings
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


def test_api_key_enforcement(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify X-API-Key requirement when API_KEYS setting is populated."""
    # Mock settings with configured API key
    test_settings = Settings(API_KEYS="secret-key-1,secret-key-2")
    monkeypatch.setattr("app.api.deps.get_settings", lambda: test_settings)

    app_instance = create_app()
    app_instance.dependency_overrides[get_db] = lambda: db_session

    with TestClient(app_instance) as client:
        payload = {
            "group": "F_urban",
            "features": {"monthly_inflow_bdt": 14000.0, "bills_on_time": 0.95},
        }

        # 1. Missing API key returns 401
        resp_missing = client.post("/score", json=payload)
        assert resp_missing.status_code == 401
        assert "Invalid or missing X-API-Key" in resp_missing.json()["detail"]

        # 2. Invalid API key returns 401
        resp_invalid = client.post("/score", json=payload, headers={"X-API-Key": "wrong-key"})
        assert resp_invalid.status_code == 401

        # 3. Valid API key returns 200
        resp_valid = client.post("/score", json=payload, headers={"X-API-Key": "secret-key-1"})
        assert resp_valid.status_code == 200
        assert resp_valid.json()["approved"] is True


def test_borrower_auth_headers_on_delete_me(db_session: Session) -> None:
    """Verify /me requires either Authorization Bearer token or X-User-ID header."""
    user = User(
        phone_hash="hash_auth_test",
        gender="F",
        region="urban",
        division="Dhaka",
    )
    db_session.add(user)
    db_session.commit()

    app_instance = create_app()
    app_instance.dependency_overrides[get_db] = lambda: db_session

    with TestClient(app_instance) as client:
        # 1. No auth headers returns 401
        resp = client.delete("/me")
        assert resp.status_code == 401

        # 2. A raw user id is not a credential
        assert (
            client.delete("/me", headers={"Authorization": f"Bearer {user.id}"}).status_code == 401
        )
        assert client.delete("/me", headers={"X-User-ID": user.id}).status_code == 401

        # 3. A signed session token succeeds
        token = client.post("/auth/session", json={"user_id": user.id}).json()["token"]
        resp2 = client.delete("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "deleted"


def test_session_tokens_profile_and_tampering(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Signed tokens identify the borrower; tampered, foreign or expired tokens are rejected."""
    from app.security import issue_token

    users = []
    for i in range(2):
        u = User(phone_hash=f"tok{i}", gender="F", region="rural", division="Khulna")
        db_session.add(u)
        users.append(u)
    db_session.commit()
    app_instance = create_app()
    app_instance.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app_instance) as client:
        token = client.post("/auth/session", json={"user_id": users[0].id}).json()["token"]
        me = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200 and me.json()["group"] == "F_rural"

        tampered = token.replace(users[0].id, users[1].id)
        assert client.get("/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401
        expired, _ = issue_token(users[0].id, ttl_seconds=-1)
        assert client.get("/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

        # A borrower cannot grant consent for someone else
        resp = client.post(
            "/consent",
            json={"user_id": users[1].id, "source": "sms"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        ok = client.post(
            "/consent",
            json={"user_id": users[0].id, "source": "sms"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert ok.status_code == 201
        assert (
            client.delete("/consent/sms", headers={"Authorization": f"Bearer {token}"}).json()[
                "status"
            ]
            == "revoked"
        )

        # With API keys configured, an anonymous consent call is refused
        monkeypatch.setattr("app.api.deps.get_settings", lambda: Settings(API_KEYS="k1"))
        assert (
            client.post("/consent", json={"user_id": users[0].id, "source": "sms"}).status_code
            == 401
        )
        assert (
            client.post(
                "/consent",
                json={"user_id": users[0].id, "source": "sms"},
                headers={"X-API-Key": "k1"},
            ).status_code
            == 201
        )
