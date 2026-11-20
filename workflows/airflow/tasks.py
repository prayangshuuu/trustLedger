"""Plain-Python task logic for the Airflow DAGs (importable and testable without Airflow)."""

import json
import math
import os
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "models" / "feature_baseline.json"
MAX_GAP = 0.05
PSI_ALERT = 0.25  # common rule of thumb: <0.1 stable, 0.1-0.25 moderate, >0.25 significant


class FairnessGateError(RuntimeError):
    """Raised (and fails the DAG run) when a fairness gap exceeds the gate."""


class DriftAlert(RuntimeError):
    pass


def api_get(path: str) -> dict[str, Any]:
    resp = httpx.get(
        os.getenv("TRUSTLEDGER_API_URL", "http://localhost:8000") + path,
        headers={"X-API-Key": os.getenv("TRUSTLEDGER_API_KEY", "")},
        timeout=60,
    )
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    return data


def fairness_gate(report: dict[str, Any], max_gap: float = MAX_GAP) -> dict[str, Any]:
    """Fail loudly if approval-rate or equalized-odds gap is above max_gap."""
    gaps = {
        "approval_rate_gap": report.get("approval_rate_gap") or 0.0,
        "equalized_odds_gap": report.get("equalized_odds_gap") or 0.0,
    }
    failed = {k: v for k, v in gaps.items() if v > max_gap}
    if failed:
        raise FairnessGateError(
            f"Fairness gate FAILED (> {max_gap}): {failed}; by_group={report.get('by_group')}"
        )
    return {"ok": True, **gaps, "total_decisions": report.get("total_decisions", 0)}


def weekly_fairness_audit() -> dict[str, Any]:
    return fairness_gate(api_get("/fairness/report"))


def psi(expected: list[float], edges: list[float], values: list[float]) -> float:
    """Population Stability Index of values against baseline bin proportions."""
    if not values or len(edges) < 2:
        return 0.0
    counts = [0] * (len(edges) - 1)
    for v in values:
        x = min(max(v, edges[0]), edges[-1])
        idx = len(edges) - 2
        for i in range(len(edges) - 1):
            if x < edges[i + 1]:
                idx = i
                break
        counts[idx] += 1
    total = sum(counts)
    eps = 1e-4
    out = 0.0
    for e, c in zip(expected, counts, strict=False):
        a = max(c / total, eps)
        e = max(e, eps)
        out += (a - e) * math.log(a / e)
    return round(out, 4)


def drift_report(
    rows: list[dict[str, Any]], baseline: dict[str, Any] | None = None, alert: float = PSI_ALERT
) -> dict[str, Any]:
    baseline = baseline or json.loads(BASELINE_PATH.read_text())
    result: dict[str, Any] = {"n": len(rows), "features": {}, "drifted": []}
    for feature, b in baseline["features"].items():
        values = [float(r[feature]) for r in rows if r.get(feature) is not None]
        score = psi(b["proportions"], b["edges"], values)
        result["features"][feature] = {"psi": score, "n": len(values)}
        if len(values) >= 30 and score > alert:
            result["drifted"].append(feature)
    return result


def load_recent_snapshots(limit: int = 5000) -> list[dict[str, Any]]:
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from app.db.models import FeatureSnapshot
    from app.db.session import get_session_factory
    from sqlalchemy import select

    with get_session_factory()() as db:
        snaps = db.scalars(
            select(FeatureSnapshot).order_by(FeatureSnapshot.created_at.desc()).limit(limit)
        )
        return [dict(s.features) for s in snaps]


def nightly_drift_check() -> dict[str, Any]:
    report = drift_report(load_recent_snapshots())
    if report["drifted"]:
        raise DriftAlert(f"Feature drift (PSI > {PSI_ALERT}): {report['drifted']}")
    return report


def purge_expired_documents() -> int:
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from app.storage import get_store

    return get_store().purge_expired()


def federated_round(rounds: int = 1) -> dict[str, Any]:
    """Run Flower aggregation rounds (Prompt 14) and return the latest AUC."""
    import sys

    sys.path.insert(0, str(ROOT))
    from federated.simulate import run_simulation

    history = run_simulation(rounds=rounds, save=False)
    return {"rounds": rounds, "auc": history[-1]}
