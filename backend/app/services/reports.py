"""Fairness and Inclusion Lift reports computed over stored decisions."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.fairness import audit
from app.db.models import AuditLog, DecisionRecord, Repayment, User
from app.schemas.fairness import FairnessReportResponse, GroupFairnessMetrics, InclusionLiftResponse

BANK_RULE = "has_bank_account == 1 AND (has_salary_slip == 1 OR monthly_inflow_bdt >= 25000)"
BANK_INFLOW_MIN = 25000.0


def load_decisions(db: Session, since: datetime | None = None) -> list[DecisionRecord]:
    stmt = select(DecisionRecord).order_by(DecisionRecord.created_at)
    if since is not None:
        stmt = stmt.where(DecisionRecord.created_at >= since)
    return list(db.scalars(stmt).all())


def repayment_outcomes(db: Session, decisions: list[DecisionRecord]) -> dict[str, int]:
    """Observed outcome per application: 1 if every repayment was on time, 0 if any was late."""
    app_ids = [d.application_id for d in decisions if d.application_id]
    if not app_ids:
        return {}
    outcomes: dict[str, int] = {}
    for rep in db.scalars(select(Repayment).where(Repayment.application_id.in_(app_ids))):
        prev = outcomes.get(rep.application_id, 1)
        outcomes[rep.application_id] = prev if rep.on_time else 0
    return outcomes


def fairness_report(db: Session, since: datetime | None = None) -> FairnessReportResponse:
    decisions = load_decisions(db, since)
    if not decisions:
        return FairnessReportResponse(
            total_decisions=0,
            by_group={},
            approval_rate_gap=0.0,
            tpr_gap=None,
            fpr_gap=None,
            equalized_odds_gap=None,
            fairness_ok=True,
        )

    outcomes = repayment_outcomes(db, decisions)
    # TPR/FPR need outcomes for rejected applicants too (e.g. a back-test); approved-only
    # outcomes would make both rates trivially 1.0, so we drop them in that case.
    if not any(not d.approved and d.application_id in outcomes for d in decisions):
        outcomes = {}
    rows: list[dict[str, Any]] = [
        {
            "group": d.group,
            "approved": int(d.approved),
            "repaid": outcomes.get(d.application_id or "", None),
        }
        for d in decisions
    ]
    result = audit(rows)

    def r4(v: float | None) -> float | None:
        return round(v, 4) if v is not None else None

    by_group = {
        g: GroupFairnessMetrics(
            group=m.group,
            count=m.count,
            approval_rate=round(m.approval_rate, 4),
            tpr=r4(m.tpr),
            fpr=r4(m.fpr),
        )
        for g, m in sorted(result.by_group.items())
    }
    return FairnessReportResponse(
        total_decisions=len(decisions),
        by_group=by_group,
        approval_rate_gap=round(result.approval_rate_gap, 4),
        tpr_gap=r4(result.tpr_gap),
        fpr_gap=r4(result.fpr_gap),
        equalized_odds_gap=r4(result.equalized_odds_gap),
        fairness_ok=result.fairness_ok,
    )


def bank_rule_approves(user: User | None, monthly_inflow: float | None) -> bool:
    if user is None:
        return False
    inflow = float(monthly_inflow or 0.0)
    return bool(user.has_bank_account) and (bool(user.has_salary_slip) or inflow >= BANK_INFLOW_MIN)


def inclusion_lift(db: Session, since: datetime | None = None) -> InclusionLiftResponse:
    """Bank-rule approvals vs TrustLedger approvals, same rule as the training notebook."""
    decisions = load_decisions(db, since)
    total = len(decisions)
    if total == 0:
        return InclusionLiftResponse(
            total_evaluated=0,
            bank_rule_approvals=0,
            bank_rule_approval_rate=0.0,
            trustledger_approvals=0,
            trustledger_approval_rate=0.0,
            newly_included_count=0,
            newly_included_rate=0.0,
            inclusion_lift_percentage=0.0,
            rule_description=BANK_RULE,
        )

    user_ids = {d.user_id for d in decisions if d.user_id}
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids)))}
    inflow_by_decision: dict[str, float | None] = {}
    for entry in db.scalars(
        select(AuditLog).where(
            AuditLog.entity_type == "decision",
            AuditLog.entity_id.in_([d.id for d in decisions]),
        )
    ):
        feats = (entry.details or {}).get("features") or {}
        inflow_by_decision[entry.entity_id] = feats.get("monthly_inflow_bdt")

    bank = tl = new = 0
    for d in decisions:
        user = users.get(d.user_id) if d.user_id else None
        bank_ok = bank_rule_approves(user, inflow_by_decision.get(d.id))
        bank += bank_ok
        tl += bool(d.approved)
        new += bool(d.approved) and not bank_ok

    bank_rate, tl_rate, new_rate = bank / total, tl / total, new / total
    lift = ((tl_rate - bank_rate) / bank_rate * 100.0) if bank_rate > 0 else new_rate * 100.0
    return InclusionLiftResponse(
        total_evaluated=total,
        bank_rule_approvals=bank,
        bank_rule_approval_rate=round(bank_rate, 4),
        trustledger_approvals=tl,
        trustledger_approval_rate=round(tl_rate, 4),
        newly_included_count=new,
        newly_included_rate=round(new_rate, 4),
        inclusion_lift_percentage=round(lift, 1),
        rule_description=BANK_RULE,
    )
