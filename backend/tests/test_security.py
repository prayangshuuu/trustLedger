"""Security and observability: rate limits, size and file-type checks, CORS, metrics, PII-free logs."""

import logging
from collections.abc import Generator

import pytest
from app.config import get_settings
from app.db.base import Base
from app.db.models import User
from app.db.session import create_app_engine, get_db
from app.demo_seed import hash_phone, seed_demo_personas
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    seed_demo_personas(session)
    yield session
    session.close()


def make_client(db: Session, monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_settings() -> Generator[None, None, None]:
    yield
    get_settings.cache_clear()


def test_rate_limit_per_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(db, monkeypatch, RATE_LIMIT_PER_MINUTE="3")
    codes = [
        client.get("/fairness/report", headers={"X-API-Key": "a"}).status_code for _ in range(4)
    ]
    assert codes == [200, 200, 200, 429]
    assert (
        client.get("/fairness/report", headers={"X-API-Key": "b"}).status_code == 200
    )  # separate bucket
    assert client.get("/health").status_code == 200  # exempt


def test_body_size_limit(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(db, monkeypatch, MAX_BODY_BYTES="200")
    resp = client.post("/score", json={"features": {"bills_on_time": 0.9}, "pad": "x" * 500})
    assert resp.status_code == 413


def test_upload_rejects_non_images(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(db, monkeypatch)
    user = db.scalars(select(User).where(User.phone_hash == hash_phone("+8801711000001"))).one()
    resp = client.post(
        "/documents",
        data={"user_id": user.id},
        files={"file": ("bill.jpg", b"%PDF-1.4 not an image", "image/jpeg")},
    )
    assert resp.status_code == 415


def test_cors_allows_only_configured_origins(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(db, monkeypatch, CORS_ORIGINS="https://dash.example")
    pre = {"Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "X-API-Key"}
    ok = client.options("/stats/overview", headers={"Origin": "https://dash.example", **pre})
    assert ok.headers.get("access-control-allow-origin") == "https://dash.example"
    bad = client.options("/stats/overview", headers={"Origin": "https://evil.example", **pre})
    assert "access-control-allow-origin" not in bad.headers


def test_metrics_endpoint_counts_decisions(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(db, monkeypatch)
    client.post(
        "/score",
        json={"group": "F_urban", "features": {"bills_on_time": 0.97, "monthly_inflow_bdt": 14000}},
    )
    text = client.get("/metrics").text
    assert "trustledger_http_request_duration_seconds_bucket" in text
    assert "trustledger_decisions_total" in text
    assert "trustledger_llm_calls_total" in text or "trustledger_http_requests_total" in text


def test_logs_never_contain_pii(
    db: Session, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = make_client(db, monkeypatch, DEMO_MODE="true")
    user = db.scalars(select(User).where(User.phone_hash == hash_phone("+8801711000001"))).one()
    token = client.post("/auth/session", json={"user_id": user.id}).json()["token"]
    raw_sms = (
        "Send Money Tk 3,000.00 to 01712345678 successful on 05/11/2026 11:30. TrxID SECRET99."
    )
    with caplog.at_level(logging.DEBUG):
        client.post("/parse/sms", json={"sms_list": [raw_sms]})
        client.post("/apply", json={"user_id": user.id, "sms": [raw_sms] * 3})
        client.get("/me", headers={"Authorization": f"Bearer {token}"})
        logging.getLogger("trustledger.test").info("user phone 01712345678 email a@b.com")
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "01712345678" not in text
    assert "SECRET99" not in text
    assert "a@b.com" not in text
    assert token not in text
    assert "<PHONE>" in text


def test_sensitive_attributes_cannot_be_model_inputs() -> None:
    from app.core.features import FeatureVector
    from app.core.model import load_meta
    from pydantic import ValidationError

    for attr in ("gender", "region", "division", "age"):
        assert attr not in load_meta()["features"]
        with pytest.raises(ValidationError):
            FeatureVector(**{"bills_on_time": 0.9, attr: "F"})
