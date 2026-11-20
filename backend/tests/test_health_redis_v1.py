"""Health reports Redis, and the /api/v1 alias scores like /score."""

from app.api.routers import health
from app.main import create_app
from fastapi.testclient import TestClient


def test_health_reports_redis(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(health, "redis_status", lambda: "connected")
    body = TestClient(create_app()).get("/health").json()
    assert body["redis"] == "connected"


def test_redis_unavailable_never_raises(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.config import Settings

    monkeypatch.setattr(health, "get_settings", lambda: Settings(REDIS_URL="redis://127.0.0.1:1/0"))
    assert health.redis_status() == "unavailable"


def test_api_v1_score_alias() -> None:
    from app.db.base import Base
    from app.db.session import create_app_engine, get_db
    from sqlalchemy.orm import sessionmaker

    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    r = c.post(
        "/api/v1/score",
        json={"group": "F_urban", "features": {"bills_on_time": 0.97, "monthly_inflow_bdt": 14000}},
    )
    assert r.status_code == 200 and 300 <= r.json()["score"] <= 900 and r.json()["reasons"]
    assert "/api/v1/score" not in app.openapi()["paths"]
