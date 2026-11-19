"""Fairness report and inclusion lift response schemas."""

from pydantic import BaseModel, Field


class GroupFairnessMetrics(BaseModel):
    """Fairness metrics for a specific demographic group."""

    group: str
    count: int
    approval_rate: float
    tpr: float | None = None
    fpr: float | None = None


class FairnessReportResponse(BaseModel):
    """Live fairness audit report calculated across stored decisions."""

    total_decisions: int
    by_group: dict[str, GroupFairnessMetrics]
    approval_rate_gap: float
    tpr_gap: float | None = None
    fpr_gap: float | None = None
    equalized_odds_gap: float | None = None
    fairness_ok: bool = Field(..., description="True if all disparity gaps remain <= 0.05")


class InclusionLiftResponse(BaseModel):
    """Inclusion Lift metrics comparing traditional bank rules against TrustLedger."""

    total_evaluated: int
    bank_rule_approvals: int
    bank_rule_approval_rate: float
    trustledger_approvals: int
    trustledger_approval_rate: float
    newly_included_count: int
    newly_included_rate: float
    inclusion_lift_percentage: float
    rule_description: str
