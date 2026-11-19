"""Health check endpoint tests."""

from fastapi.testclient import TestClient

try:
    from app.main import app
except ModuleNotFoundError:
    from backend.app.main import app  # type: ignore[no-redef]


def test_health_endpoint() -> None:
    """Verify that GET /health returns 200 with status ok and app name."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "trustledger"
