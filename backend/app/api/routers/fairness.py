"""Fairness auditing and Inclusion Lift reporting endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ApiKeyAuth, DbSession
from app.schemas.fairness import FairnessReportResponse, InclusionLiftResponse
from app.services.reports import fairness_report as build_fairness_report
from app.services.reports import inclusion_lift as build_inclusion_lift

router = APIRouter(tags=["Fairness & Inclusion"])

SinceParam = Annotated[
    datetime | None, Query(description="Only include decisions created at or after this time")
]


@router.get(
    "/fairness/report",
    response_model=FairnessReportResponse,
    summary="Demographic Fairness Audit Report",
)
def fairness_report(
    db: DbSession, since: SinceParam = None, _api_key: ApiKeyAuth = None
) -> FairnessReportResponse:
    """Approval rate, TPR and FPR per group over stored decisions, with gaps vs the 0.05 gate.

    TPR/FPR use observed repayment outcomes (all on time = repaid) when they exist.
    """
    return build_fairness_report(db, since)


@router.get(
    "/inclusion-lift",
    response_model=InclusionLiftResponse,
    summary="Financial Inclusion Lift vs Traditional Bank Rules",
)
def inclusion_lift(
    db: DbSession, since: SinceParam = None, _api_key: ApiKeyAuth = None
) -> InclusionLiftResponse:
    """Compare TrustLedger approvals against the legacy bank rule used in the notebook:
    has_bank_account AND (has_salary_slip OR monthly_inflow_bdt >= 25,000).
    """
    return build_inclusion_lift(db, since)
