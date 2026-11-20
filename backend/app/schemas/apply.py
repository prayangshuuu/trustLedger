"""Schemas for the agent pipeline endpoint (POST /apply)."""

from typing import Any

from pydantic import BaseModel, Field

from app.rag.tips import GroundedTip
from app.schemas.score import ReasonItem


class ApplyRequest(BaseModel):
    user_id: str = Field(..., description="Registered applicant ID")
    amount_bdt: float = Field(default=15000.0, gt=0, le=500000, description="Requested loan (BDT)")
    sms: list[str] | None = Field(
        default=None, max_length=2000, description="Raw SMS list (DEMO_MODE only, never stored)"
    )
    features: dict[str, Any] | None = Field(default=None, description="Pre-computed features")


class ApplyDecision(BaseModel):
    decision_id: str | None
    application_id: str | None = None
    p_repay: float
    score: int
    band: str
    approved: bool
    threshold_used: float
    model_version: str
    reasons: list[ReasonItem]
    good: list[str]
    bad: list[str]
    tips: list[str]


class ApplyResponse(BaseModel):
    trace_id: str
    status: str = Field(
        ...,
        description="approved | rejected | needs_review | blocked | bhorsha_required | rejected_input",
    )
    bhorsha_required: bool = False
    error: str | None = None
    decision: ApplyDecision | None = None
    summary_bn: str | None = None
    grounded_tips: list[GroundedTip] = []
    fairness: dict[str, Any] | None = None
    features: dict[str, Any] = {}
    trace: list[dict[str, Any]] = []


class TraceResponse(BaseModel):
    trace_id: str
    user_id: str | None
    created_at: str
    details: dict[str, Any]
