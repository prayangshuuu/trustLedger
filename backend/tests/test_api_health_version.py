"""Integration tests for system health, version, and middleware headers."""

from collections.abc import Generator

import pytest
from app.db.base import Base
from app.db.session import create_app_engine, get_db
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Test client bound to isolated SQLite database."""
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        sess = session_factory()
        try:
            yield sess
        finally:
            sess.close()

    app_instance = create_app()
    app_instance.dependency_overrides[get_db] = override_get_db
    with TestClient(app_instance) as tc:
        yield tc


def test_get_health(client: TestClient) -> None:
    """Verify health endpoint returns status ok, database connected, and X-Request-ID header."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "trustledger"
    assert data["database"] == "connected"
    assert "timestamp" in data
    assert "X-Request-ID" in resp.headers


def test_get_version(client: TestClient) -> None:
    """Verify version endpoint exposes model version hash and git sha."""
    resp = client.get("/version")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app_version"] == "1.0.0"
    assert len(data["model_version"]) == 16
    assert len(data["git_sha"]) >= 6
