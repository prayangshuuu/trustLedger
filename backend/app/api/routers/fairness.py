"""Fairness auditing and Inclusion Lift reporting endpoints."""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.fairness import audit
from app.db.models import DecisionRecord, FeatureSnapshot
from app.schemas.fairness import FairnessReportResponse, GroupFairnessMetrics, InclusionLiftResponse

router = APIRouter(tags=["Fairness & Inclusion"])


@router.get(
    "/fairness/report",
    response_model=FairnessReportResponse,
    summary="Demographic Fairness Audit Report",
)
def fairness_report(db: DbSession) -> FairnessReportResponse:
    """Compute live demographic parity and equalized odds gaps across stored decisions."""
    decisions = list(db.scalars(select(DecisionRecord)).all())
    if not decisions:
        return FairnessReportResponse(
            total_decisions=0,
            by_group={},
            approval_rate_gap=0.0,
            tpr_gap=0.0,
            fpr_gap=0.0,
            equalized_odds_gap=0.0,
            fairness_ok=True,
        )

    audit_summary = audit(decisions)

    by_group = {
        g: GroupFairnessMetrics(
            group=m.group,
            count=m.count,
            approval_rate=round(m.approval_rate, 4),
            tpr=round(m.tpr, 4) if m.tpr is not None else None,
            fpr=round(m.fpr, 4) if m.fpr is not None else None,
        )
        for g, m in audit_summary.by_group.items()
    }

    return FairnessReportResponse(
        total_decisions=len(decisions),
        by_group=by_group,
        approval_rate_gap=round(audit_summary.approval_rate_gap, 4),
        tpr_gap=round(audit_summary.tpr_gap, 4) if audit_summary.tpr_gap is not None else None,
        fpr_gap=round(audit_summary.fpr_gap, 4) if audit_summary.fpr_gap is not None else None,
        equalized_odds_gap=round(audit_summary.equalized_odds_gap, 4)
        if audit_summary.equalized_odds_gap is not None
        else None,
        fairness_ok=audit_summary.fairness_ok,
    )


@router.get(
    "/inclusion-lift",
    response_model=InclusionLiftResponse,
    summary="Financial Inclusion Lift vs Traditional Bank Rules",
)
def inclusion_lift(db: DbSession) -> InclusionLiftResponse:
    """Compare TrustLedger fair approval reach against traditional bank lending rules.

    Traditional bank rule: Requires formal bank account and (salary slip OR monthly inflow >= 25,000 BDT).
    """
    decisions = list(db.scalars(select(DecisionRecord)).all())
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
            rule_description="has_bank_account == 1 AND (has_salary_slip == 1 OR monthly_inflow_bdt >= 25000)",
        )

    # Collect snapshots for linked users
    user_ids = {d.user_id for d in decisions if d.user_id}
    snapshots_by_user: dict[str, FeatureSnapshot] = {}
    if user_ids:
        snaps = db.scalars(
            select(FeatureSnapshot).where(FeatureSnapshot.user_id.in_(user_ids))
        ).all()
        for s in snaps:
            if s.user_id not in snapshots_by_user:
                snapshots_by_user[s.user_id] = s

    bank_approvals = 0
    tl_approvals = 0
    newly_included = 0

    for decision in decisions:
        snapshot = snapshots_by_user.get(decision.user_id) if decision.user_id else None
        features = snapshot.features if snapshot else {}
        # Traditional banking rule per notebook
        has_bank = features.get("has_bank_account", 0) == 1
        has_slip = features.get("has_salary_slip", 0) == 1
        inflow = float(features.get("monthly_inflow_bdt", 0.0) or 0.0)
        bank_approved = has_bank and (has_slip or inflow >= 25000.0)

        tl_approved = bool(decision.approved)

        if bank_approved:
            bank_approvals += 1
        if tl_approved:
            tl_approvals += 1
        if tl_approved and not bank_approved:
            newly_included += 1

    bank_rate = bank_approvals / total
    tl_rate = tl_approvals / total
    new_rate = newly_included / total
    lift = ((tl_rate - bank_rate) / bank_rate * 100.0) if bank_rate > 0 else (new_rate * 100.0)

    return InclusionLiftResponse(
        total_evaluated=total,
        bank_rule_approvals=bank_approvals,
        bank_rule_approval_rate=round(bank_rate, 4),
        trustledger_approvals=tl_approvals,
        trustledger_approval_rate=round(tl_rate, 4),
        newly_included_count=newly_included,
        newly_included_rate=round(new_rate, 4),
        inclusion_lift_percentage=round(lift, 1),
        rule_description="has_bank_account == 1 AND (has_salary_slip == 1 OR monthly_inflow_bdt >= 25000)",
    )
