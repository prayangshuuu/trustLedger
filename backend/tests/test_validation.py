"""Unit and integration tests for AI model validation guardrails (Prompt 25)."""

from collections.abc import Generator

import pytest
from app.core.validation import (
    InsufficientDataError,
    ValidationFailureError,
    check_cross_source_consistency,
    check_feature_ranges,
    check_out_of_distribution,
    validate_bhorsha_session,
    validate_explanation,
    validate_features_before_scoring,
    validate_sufficiency,
    validate_transaction_item,
)
from app.db.base import Base
from app.db.session import create_app_engine, get_db
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
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
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as tc:
        yield tc


def test_transaction_sanitization_and_date_check():
    # Negative amount clipped to 0
    tx, flags = validate_transaction_item({"amount_bdt": -50.0, "type": "unknown"})
    assert tx["amount_bdt"] == 0.0
    assert tx["type"] == "other"
    assert "negative_amount_clipped" in flags

    # Future date flagged
    _tx2, flags2 = validate_transaction_item({"amount_bdt": 500.0, "date": "2030-01-01T00:00:00Z"})
    assert "future_date_flagged" in flags2


def test_feature_ranges_and_clipping():
    features = {
        "monthly_inflow_bdt": -100.0,  # below min
        "loan_to_income": 99.0,  # above max
        "bills_on_time": 1.0,
    }
    clipped, flags = check_feature_ranges(features)
    assert clipped["monthly_inflow_bdt"] >= 0.0
    assert clipped["loan_to_income"] < 99.0
    assert any("below_min" in f for f in flags)
    assert any("above_max" in f for f in flags)


def test_out_of_distribution_check():
    # Normal features
    normal_features = {
        "monthly_inflow_bdt": 25000.0,
        "loan_to_income": 1.2,
        "txn_per_month": 15.0,
    }
    is_ood, flags = check_out_of_distribution(normal_features)
    assert not is_ood

    # Extreme OOD features across multiple dimensions
    extreme_features = {
        "monthly_inflow_bdt": 50_000_000.0,
        "loan_to_income": 80.0,
        "txn_per_month": 500.0,
    }
    is_ood, flags = check_out_of_distribution(extreme_features)
    assert is_ood
    assert len(flags) >= 2


def test_sufficiency_check():
    # Insufficient: < 3 months and no bhorsha
    insufficient = {"months_on_wallet": 1.5, "bhorsha_score": None}
    ok, msg = validate_sufficiency(insufficient)
    assert not ok
    assert msg is not None

    # Sufficient with wallet history
    with_wallet = {"months_on_wallet": 4.0, "bhorsha_score": None}
    ok, _ = validate_sufficiency(with_wallet)
    assert ok

    # Sufficient with Bhorsha
    with_bhorsha = {"months_on_wallet": 1.0, "bhorsha_score": 75.0}
    ok, _ = validate_sufficiency(with_bhorsha)
    assert ok


def test_validate_features_before_scoring_gate():
    # Sufficiency enforcement failure
    with pytest.raises(InsufficientDataError):
        validate_features_before_scoring(
            {"months_on_wallet": 1.0, "bhorsha_score": None},
            enforce_sufficiency=True,
        )

    # All null failure
    with pytest.raises(ValidationFailureError):
        validate_features_before_scoring(
            {f: None for f in ["monthly_inflow_bdt", "loan_to_income"]},
            enforce_sufficiency=False,
        )


def test_cross_source_consistency():
    txs = [
        {"type": "bill", "amount_bdt": 1500.0, "raw_hash": "h1"},
        {"type": "bill", "amount_bdt": 1500.0, "raw_hash": "h1"},  # duplicate
    ]
    docs = [
        {"document_type": "utility_bill", "amount_bdt": 1500.0, "provider": "DESCO"},
    ]
    flags, notes = check_cross_source_consistency(txs, docs)
    # Matched bill amount
    assert any("সফলভাবে মেলানো হয়েছে" in n for n in notes)
    # Duplicate flagged
    assert any("duplicate_transactions_removed" in f for f in flags)


def test_explanation_guard():
    # 1. Hallucinated feature rejected
    valid, err = validate_explanation(
        summary_bn="আপনার নিয়মিত সঞ্চয় এবং ভালো আয় স্কোর বাড়িয়েছে।",
        decision_score=720,
        shap_features={"monthly_inflow_bdt"},  # savings_ratio is missing!
    )
    assert not valid
    assert "hallucinated_features" in (err or "")

    # 2. Approval promise rejected
    valid, err = validate_explanation(
        summary_bn="আপনার ঋণ নিশ্চিত অনুমোদন হবে এবং ১০০% পাবেন।",
        decision_score=720,
        shap_features={"monthly_inflow_bdt"},
    )
    assert not valid
    assert err == "contains_approval_promise"

    # 3. Mismatched score number rejected
    valid, err = validate_explanation(
        summary_bn="আপনার স্কোর 550 হওয়ায় আবেদন অনুমোদিত হয়েছে।",
        decision_score=720,
        shap_features=set(),
    )
    assert not valid
    assert "mismatched_score_number" in (err or "")

    # 4. Valid summary accepted
    valid, err = validate_explanation(
        summary_bn="আপনার নিয়মিত আয় বৃদ্ধি পাওয়ায় স্কোর 720 হয়েছে।",
        decision_score=720,
        shap_features={"monthly_inflow_bdt"},
    )
    assert valid
    assert err is None


def test_bhorsha_guard():
    valid, flags = validate_bhorsha_session([{"score": 85.0}, {"score": 70.0}])
    assert valid
    assert len(flags) == 0

    invalid, flags = validate_bhorsha_session([{"score": 150.0}])
    assert not invalid
    assert any("out_of_bounds" in f for f in flags)


def test_health_ai_endpoint(client: TestClient):
    resp = client.get("/health/ai")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "chat_model" in data
    assert "reasoner_model" in data
    assert "ocr_backend" in data
    assert "latency_ms" in data
    # Security constraint: key must never appear in response
    assert "api_key" not in data
    assert "key" not in data or data.get("key_configured") is not None


def test_upload_and_confirm_endpoints(client: TestClient):
    # 1. Register a real user session
    reg_resp = client.post(
        "/auth/register",
        json={"gender": "F", "region": "urban", "division": "Dhaka"},
    )
    assert reg_resp.status_code == 200
    user_id = reg_resp.json()["user_id"]
    token = reg_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Grant SMS consent
    consent_resp = client.post(
        "/consent",
        json={"user_id": user_id, "source": "sms"},
        headers=headers,
    )
    assert consent_resp.status_code == 201

    # 2. Upload raw SMS text
    sms_text = """
    You have received Tk 25,000.00 from Employer Co. Ref: Salary. Balance Tk 30,000.00. TrxID TX01 at 05/05/2026 12:00
    Mobile Recharge of Tk 200.00 to 01712345678 is successful. TrxID TX02 at 10/05/2026 12:00
    Payment of Tk 1200.00 to DESCO is successful. TrxID TX03 at 15/05/2026 12:00
    You have received Tk 25,000.00 from Employer Co. Ref: Salary. Balance Tk 35,000.00. TrxID TX04 at 05/08/2026 12:00
    """
    up_resp = client.post(
        "/upload/sms",
        json={"user_id": user_id, "raw_text": sms_text},
        headers=headers,
    )
    assert up_resp.status_code == 200
    txs = up_resp.json()["transactions"]
    assert len(txs) >= 3

    # 3. Confirm reviewed data
    confirm_resp = client.post(
        "/upload/confirm",
        json={
            "user_id": user_id,
            "transactions": txs,
            "requested_amount_bdt": 15000.0,
        },
        headers=headers,
    )
    assert confirm_resp.status_code == 200
    cdata = confirm_resp.json()
    assert "features" in cdata
    assert "data_quality" in cdata
    assert "feature_hash" in cdata
    assert isinstance(cdata["data_quality"]["notes_bn"], list)
