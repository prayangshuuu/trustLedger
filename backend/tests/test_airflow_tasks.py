"""Airflow task logic: fairness gate fails on biased decisions; PSI drift detection."""

import json
from pathlib import Path

import pytest
from app.db.base import Base
from app.db.models import DecisionRecord
from app.db.session import create_app_engine
from app.services.reports import fairness_report
from sqlalchemy.orm import sessionmaker

from workflows.airflow import tasks

BASELINE = json.loads(
    (Path(__file__).resolve().parents[2] / "models/feature_baseline.json").read_text()
)


def _decision(group: str, approved: bool) -> DecisionRecord:
    return DecisionRecord(
        p_repay=0.8,
        score=650,
        band="Good",
        approved=approved,
        reasons=[],
        tips=[],
        group=group,
        threshold_used=0.7,
        model_version="test",
    )


def test_fairness_dag_fails_on_biased_decisions() -> None:
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    # Men approved 90%, women 50%: a 0.40 approval gap
    for i in range(100):
        db.add(_decision("M_urban", i < 90))
        db.add(_decision("F_urban", i < 50))
    db.commit()
    report = fairness_report(db).model_dump()
    with pytest.raises(tasks.FairnessGateError, match="approval_rate_gap"):
        tasks.fairness_gate(report)


def test_fairness_gate_passes_balanced(monkeypatch: pytest.MonkeyPatch) -> None:
    report = {"approval_rate_gap": 0.013, "equalized_odds_gap": 0.034, "total_decisions": 10}
    assert tasks.fairness_gate(report)["ok"] is True
    monkeypatch.setattr(tasks, "api_get", lambda path: report)
    assert tasks.weekly_fairness_audit()["ok"] is True


def test_psi_detects_drift() -> None:
    b = BASELINE["features"]["bills_on_time"]
    stable = []
    for (lo, hi), p in zip(
        zip(b["edges"][:-1], b["edges"][1:], strict=True), b["proportions"], strict=True
    ):
        stable += [(lo + hi) / 2] * round(p * 1000)
    assert tasks.psi(b["proportions"], b["edges"], stable) < 0.1
    shifted = [b["edges"][0]] * 1000  # everyone at the minimum on-time rate
    assert tasks.psi(b["proportions"], b["edges"], shifted) > tasks.PSI_ALERT

    report = tasks.drift_report([{"bills_on_time": v} for v in shifted], BASELINE)
    assert "bills_on_time" in report["drifted"]


def test_dag_files_import_without_airflow() -> None:
    import importlib

    for name in (
        "weekly_fairness_audit",
        "nightly_drift_check",
        "federated_round",
        "purge_expired_documents",
    ):
        importlib.import_module(f"workflows.airflow.dags.{name}")
