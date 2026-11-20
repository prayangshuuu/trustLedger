"""Lender dashboard data: KPIs, score distribution, divisions, decision feed and model metrics."""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import ApiKeyAuth, DbSession
from app.db.models import Application, AuditLog, DecisionRecord, Repayment, User
from app.services.reports import fairness_report, inclusion_lift

router = APIRouter(tags=["Dashboard"])
ROOT = Path(__file__).resolve().parents[4]


@router.get("/stats/overview", summary="Dashboard KPIs")
def overview(db: DbSession, _api_key: ApiKeyAuth = None) -> dict[str, Any]:
    decisions = list(db.scalars(select(DecisionRecord)))
    n = len(decisions)
    approved = sum(d.approved for d in decisions)
    reps = list(db.scalars(select(Repayment)))
    lift = inclusion_lift(db)
    fair = fairness_report(db)
    return {
        "applications": db.scalar(select(func.count()).select_from(Application)) or 0,
        "decisions": n,
        "approval_rate": round(approved / n, 4) if n else 0.0,
        "repayments": len(reps),
        "repayment_rate": round(sum(r.on_time for r in reps) / len(reps), 4) if reps else 0.0,
        "avg_score": round(sum(d.score for d in decisions) / n, 1) if n else 0.0,
        "by_band": dict(Counter(d.band for d in decisions)),
        "needs_review": db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.status == "needs_review")
        )
        or 0,
        "inclusion": lift.model_dump(),
        "fairness_ok": fair.fairness_ok,
        "approval_rate_gap": fair.approval_rate_gap,
    }


@router.get("/stats/score-distribution", summary="Histogram of scores")
def score_distribution(
    db: DbSession, bin_width: Annotated[int, Query(ge=10, le=100)] = 25, _api_key: ApiKeyAuth = None
) -> list[dict[str, Any]]:
    counts: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for d in db.scalars(select(DecisionRecord)):
        lo = min(900 - bin_width, 300 + ((d.score - 300) // bin_width) * bin_width)
        counts[lo][0] += 1
        counts[lo][1] += int(d.approved)
    return [
        {
            "bin_start": lo,
            "bin_end": lo + bin_width,
            "count": counts[lo][0],
            "approved": counts[lo][1],
        }
        for lo in range(300, 900, bin_width)
    ]


@router.get("/stats/divisions", summary="Approvals by division (aggregate only)")
def divisions(db: DbSession, _api_key: ApiKeyAuth = None) -> list[dict[str, Any]]:
    rows = db.execute(
        select(User.division, DecisionRecord.approved).join(User, DecisionRecord.user_id == User.id)
    ).all()
    agg: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for division, ok in rows:
        agg[division][0] += 1
        agg[division][1] += int(ok)
    return [
        {"division": d, "applications": a, "approvals": k, "approval_rate": round(k / a, 4)}
        for d, (a, k) in sorted(agg.items())
    ]


def _decision_row(d: DecisionRecord, division: str | None = None) -> dict[str, Any]:
    return {
        "decision_id": d.id,
        "application_id": d.application_id,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "score": d.score,
        "band": d.band,
        "p_repay": round(d.p_repay, 4),
        "approved": d.approved,
        "group": d.group,
        "division": division,
        "threshold_used": round(d.threshold_used, 4),
        "fairness_ok": d.fairness_ok,
        "model_version": d.model_version,
        "reasons": d.reasons,
        "tips": d.tips,
    }


@router.get("/decisions", summary="Live decision feed")
def list_decisions(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    _api_key: ApiKeyAuth = None,
) -> dict[str, Any]:
    total = db.scalar(select(func.count()).select_from(DecisionRecord)) or 0
    rows = db.execute(
        select(DecisionRecord, User.division)
        .outerjoin(User, DecisionRecord.user_id == User.id)
        .order_by(DecisionRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"total": total, "items": [_decision_row(d, div) for d, div in rows]}


@router.get("/decisions/{decision_id}", summary="Applicant decision detail with trace")
def decision_detail(decision_id: str, db: DbSession, _api_key: ApiKeyAuth = None) -> dict[str, Any]:
    d = db.get(DecisionRecord, decision_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Decision '{decision_id}' not found")
    user = db.get(User, d.user_id) if d.user_id else None
    audit = db.scalars(
        select(AuditLog).where(AuditLog.entity_type == "decision", AuditLog.entity_id == d.id)
    ).first()
    details = audit.details if audit else {}
    trace = None
    if details.get("trace_id"):
        t = db.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == "trace", AuditLog.entity_id == details["trace_id"]
            )
        ).first()
        trace = t.details if t else None
    app = db.get(Application, d.application_id) if d.application_id else None
    return {
        **_decision_row(d, user.division if user else None),
        "status": app.status if app else None,
        "amount_bdt": app.amount_bdt if app else None,
        "features": details.get("features", {}),
        "fairness": details.get("fairness"),
        "trace_id": details.get("trace_id"),
        "trace": trace,
    }


@router.get("/stats/model-metrics", summary="Offline model, fairness and federated metrics")
def model_metrics(_api_key: ApiKeyAuth = None) -> dict[str, Any]:
    """Notebook test-set metrics (training_files/metrics.json) and Flower results."""
    out: dict[str, Any] = {}
    for key, name in (
        ("notebook", "metrics.json"),
        ("flower", "flower_metrics.json"),
        ("evals", "eval_report.json"),
    ):
        path = ROOT / "training_files" / name
        if path.exists():
            out[key] = json.loads(path.read_text())
    return out
