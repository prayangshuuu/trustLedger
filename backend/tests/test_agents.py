"""LangGraph pipeline: personas end to end, Bhorsha routing, borderline review, fairness block."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.agents.prompts import AGENT_NAMES
from app.config import get_settings
from app.core.model import load_meta
from app.db.base import Base
from app.db.models import AuditLog, DecisionRecord, User
from app.db.session import create_app_engine, get_db
from app.main import create_app
from app.rag.ingest import ingest_directory
from fastapi.testclient import TestClient
from scripts.seed_demo import hash_phone, seed_demo_personas
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    ingest_directory(session)
    seed_demo_personas(session)
    yield session
    session.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as tc:
        yield tc


def persona(db: Session, phone: str) -> User:
    user = db.scalars(select(User).where(User.phone_hash == hash_phone(phone))).first()
    assert user is not None
    return user


SHATHI, STUDENT, HOMEMAKER = "+8801711000001", "+8801811000002", "+8801911000003"


def shathi_sms() -> list[str]:
    out: list[str] = []
    start = datetime(2025, 11, 1, 10, 0, tzinfo=UTC)
    for i in range(12):
        dt = start + timedelta(days=i * 30 + 1)

        def d(n: int, base: datetime = dt) -> str:
            return (base + timedelta(days=n)).strftime("%d/%m/%Y")

        out += [
            f"You have received Tk 14,000.00 from Garments Payroll on {d(0)} 09:00. TrxID SAL{i:02d}.",
            f"Payment Tk 1,200.00 to DESCO Bill successful on {d(10)} 14:00. TrxID BIL{i:02d}.",
            f"Send Money Tk 3,000.00 to 01712000000 successful on {d(15)} 11:30. TrxID REM{i:02d}.",
            f"Transfer Tk 600.00 to DPS Savings account successful on {d(22)} 16:15. TrxID SAV{i:02d}.",
            f"Mobile Recharge Tk 100.00 to 01811000000 successful on {d(5)} 10:00. TrxID REC{i:02d}A.",
            f"Mobile Recharge Tk 100.00 to 01811000000 successful on {d(20)} 18:00. TrxID REC{i:02d}B.",
        ]
    return out


def assert_complete_trace(db: Session, trace_id: str) -> dict[str, Any]:
    entry = db.scalars(select(AuditLog).where(AuditLog.entity_id == trace_id)).first()
    assert entry is not None
    details = entry.details
    assert set(details["prompt_versions"]) == set(AGENT_NAMES)
    assert details["model_version"]
    assert all("ms" in n for n in details["nodes"])
    return details


@pytest.mark.parametrize("phone", [SHATHI, STUDENT])
def test_personas_with_history_are_scored(client: TestClient, db: Session, phone: str) -> None:
    user = persona(db, phone)
    resp = client.post("/apply", json={"user_id": user.id, "amount_bdt": 15000})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] in ("approved", "needs_review")
    assert body["decision"]["reasons"]
    assert body["summary_bn"]
    nodes = [n["node"] for n in assert_complete_trace(db, body["trace_id"])["nodes"]]
    assert nodes == [
        "data_agent",
        "bhorsha_router",
        "scoring_agent",
        "explainer_agent",
        "fairness_agent",
        "finalize",
    ]


def test_shathi_end_to_end_from_sms_is_approved(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "DEMO_MODE", True)
    user = persona(db, SHATHI)
    resp = client.post(
        "/apply", json={"user_id": user.id, "amount_bdt": 56000, "sms": shathi_sms()}
    )
    body = resp.json()
    assert body["status"] == "approved", body
    assert body["decision"]["score"] >= 650
    assert body["features"]["loan_to_income"] == 4.0
    assert any(t["source"] for t in body["grounded_tips"]) or not body["grounded_tips"]
    record = db.get(DecisionRecord, body["decision"]["decision_id"])
    assert record is not None and record.approved and record.fairness_ok


def test_sms_rejected_outside_demo_mode(client: TestClient, db: Session) -> None:
    user = persona(db, SHATHI)
    body = client.post("/apply", json={"user_id": user.id, "sms": ["Tk 10 received"]}).json()
    assert body["status"] == "rejected_input"
    assert "DEMO_ONLY" in body["error"]


def test_zero_history_user_is_routed_to_bhorsha_then_scored(
    client: TestClient, db: Session
) -> None:
    user = User(phone_hash="zero-history", gender="F", region="rural", division="Rangpur")
    db.add(user)
    db.commit()
    client.post("/consent", json={"user_id": user.id, "source": "bhorsha"})
    body = client.post("/apply", json={"user_id": user.id, "amount_bdt": 5000}).json()
    assert body["status"] == "bhorsha_required"
    assert body["decision"] is None
    nodes = [n["node"] for n in body["trace"]]
    assert "scoring_agent" not in nodes

    start = client.post("/bhorsha/start", json={"user_id": user.id}).json()
    sid = start["session_id"]
    for i in range(12):
        client.post(
            f"/bhorsha/{sid}/answer",
            json={
                "answer": f"আমি প্রতি মাসে বাজেট করি, সঞ্চয় আলাদা রাখি ও কিস্তি সময়মতো দিই {i}",
                "elapsed_seconds": 12,
            },
        )
    assert client.get(f"/bhorsha/{sid}/result").status_code == 200
    body = client.post("/apply", json={"user_id": user.id, "amount_bdt": 5000}).json()
    assert body["status"] in ("approved", "rejected", "needs_review")
    assert body["decision"]["reasons"]


def test_homemaker_persona_scored_from_bhorsha(client: TestClient, db: Session) -> None:
    user = persona(db, HOMEMAKER)
    body = client.post("/apply", json={"user_id": user.id, "amount_bdt": 8000}).json()
    assert body["status"] in ("approved", "rejected", "needs_review")
    assert body["decision"]["reasons"][0]["feature"] == "bhorsha_score"


def test_borderline_goes_to_review(client: TestClient, db: Session) -> None:
    user = persona(db, SHATHI)
    first = client.post("/apply", json={"user_id": user.id, "amount_bdt": 15000}).json()
    p = first["decision"]["p_repay"]
    thresholds = load_meta()["group_thresholds"]
    original = thresholds["F_urban"]
    thresholds["F_urban"] = p - 0.01
    try:
        body = client.post("/apply", json={"user_id": user.id, "amount_bdt": 15000}).json()
    finally:
        thresholds["F_urban"] = original
    assert body["status"] == "needs_review", body["fairness"]
    record = db.get(DecisionRecord, body["decision"]["decision_id"])
    assert record is not None and record.approved is False


def test_fairness_agent_blocks_when_threshold_missing(client: TestClient, db: Session) -> None:
    user = persona(db, SHATHI)
    thresholds = load_meta()["group_thresholds"]
    original = thresholds.pop("F_urban")
    try:
        body = client.post("/apply", json={"user_id": user.id, "amount_bdt": 15000}).json()
    finally:
        thresholds["F_urban"] = original
    # Scoring itself refuses an unknown group, and the decision is never approved
    assert body["status"] in ("blocked", "rejected_input")
    assert body["decision"] is None or body["decision"]["approved"] is False


def test_fairness_check_blocks_missing_threshold_directly() -> None:
    from app.core.decision import score_applicant
    from app.services.decisions import fairness_check

    decision = score_applicant({"bills_on_time": 0.9, "monthly_inflow_bdt": 14000}, "F_urban")
    assert fairness_check(decision, "F_urban", {}).ok
    blocked = fairness_check(decision, "X_unknown", {})
    assert not blocked.ok and "threshold" in (blocked.blocked_reason or "")
    leak = fairness_check(decision, "F_urban", {"gender": "F"})
    assert not leak.ok


def test_trace_endpoint(client: TestClient, db: Session) -> None:
    user = persona(db, STUDENT)
    trace_id = client.post("/apply", json={"user_id": user.id}).json()["trace_id"]
    resp = client.get(f"/traces/{trace_id}")
    assert resp.status_code == 200
    assert resp.json()["details"]["prompt_versions"]["explainer_agent"] == "1.0.0"
    assert client.get("/traces/nope").status_code == 404
