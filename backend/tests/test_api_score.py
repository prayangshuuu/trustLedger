"""Integration tests for scoring and explanation endpoints."""

from collections.abc import Generator

import pytest
from app.db.base import Base
from app.db.models import DecisionRecord, FeatureSnapshot, User
from app.db.session import create_app_engine, get_db
from app.main import create_app
from app.privacy.consent import grant_consent
from fastapi.testclient import TestClient
from sqlalchemy import select
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


def test_score_shathi_payload_approved_and_stored(client: TestClient, db_session: Session) -> None:
    """Verify POST /score for Shathi returns approved + Bangla reasons, and stores decision."""
    payload = {
        "group": "F_urban",
        "amount_bdt": 15000.0,
        "features": {
            "monthly_inflow_bdt": 14000.0,
            "income_volatility": 0.10,
            "months_on_wallet": 30.0,
            "txn_per_month": 18.0,
            "bills_on_time": 0.97,
            "recharge_regularity": 0.90,
            "savings_ratio": 0.04,
            "sends_money_home": 1.0,
            "bhorsha_score": None,
            "loan_to_income": 4.0,
        },
    }

    resp = client.post("/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["approved"] is True
    assert data["band"] == "Good"
    assert data["score"] == 691
    assert abs(data["p_repay"] - 0.934) <= 0.01

    # Bangla reasons
    assert "বিল সময়মতো পরিশোধ" in data["good"]
    assert "নিয়মিত মোবাইল রিচার্জ" in data["good"]
    assert "সঞ্চয় কম" in data["bad"]
    assert "প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।" in data["tips"]

    # Verify decision is stored in database
    dec_id = data["decision_id"]
    assert dec_id is not None
    stored_dec = db_session.scalars(
        select(DecisionRecord).where(DecisionRecord.id == dec_id)
    ).first()
    assert stored_dec is not None
    assert stored_dec.score == 691
    assert stored_dec.approved is True


def test_score_consent_missing_forbidden(client: TestClient, db_session: Session) -> None:
    """Verify scoring refuses with 403 Forbidden when applicant lacks active consent."""
    user = User(
        phone_hash="hash_no_consent",
        gender="F",
        region="urban",
        division="Dhaka",
    )
    db_session.add(user)
    db_session.commit()

    payload = {
        "user_id": user.id,
        "features": {"monthly_inflow_bdt": 15000.0},
    }

    resp = client.post("/score", json=payload)
    assert resp.status_code == 403
    assert resp.json()["error"] == "CONSENT_MISSING"


def test_score_with_user_and_stored_snapshot(client: TestClient, db_session: Session) -> None:
    """Verify scoring retrieves latest feature snapshot when features are omitted."""
    user = User(
        phone_hash="hash_snapshot_user",
        gender="M",
        region="urban",
        division="Dhaka",
    )
    db_session.add(user)
    db_session.commit()

    # Grant consent
    grant_consent(db_session, user.id, "sms")

    # Add snapshot
    snap = FeatureSnapshot(
        user_id=user.id,
        features={
            "monthly_inflow_bdt": 10000.0,
            "bills_on_time": 0.90,
            "bhorsha_score": 70.0,
        },
        source_summary="Test snapshot",
    )
    db_session.add(snap)
    db_session.commit()

    payload = {"user_id": user.id}
    resp = client.post("/score", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["group"] == "M_urban"
    assert 300 <= data["score"] <= 900


def test_score_all_features_missing_bad_request(client: TestClient) -> None:
    """Verify all-missing feature dictionary returns 400 Bad Request."""
    payload = {"features": {}}
    resp = client.post("/score", json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"] == "ALL_FEATURES_MISSING"


def test_get_explanation_endpoint(client: TestClient, db_session: Session) -> None:
    """Verify GET /explain/{decision_id} returns reasons and tips."""
    # First generate a score
    score_resp = client.post(
        "/score",
        json={
            "group": "F_urban",
            "features": {
                "monthly_inflow_bdt": 14000.0,
                "bills_on_time": 0.97,
                "recharge_regularity": 0.90,
                "savings_ratio": 0.04,
                "sends_money_home": 1.0,
            },
        },
    )
    decision_id = score_resp.json()["decision_id"]

    # Now explain it
    exp_resp = client.get(f"/explain/{decision_id}")
    assert exp_resp.status_code == 200
    exp_data = exp_resp.json()
    assert exp_data["decision_id"] == decision_id
    assert exp_data["score"] == score_resp.json()["score"]
    assert len(exp_data["good"]) >= 1
    assert "বিল সময়মতো পরিশোধ" in exp_data["good"]
