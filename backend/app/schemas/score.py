"""Scoring and explanation request/response schemas with Moon persona examples."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.validation import DataQualityBlock

MOON_EXAMPLE_FEATURES: dict[str, Any] = {
    "monthly_inflow_bdt": 14000.0,
    "income_volatility": 0.10,
    "months_on_wallet": 30.0,
    "txn_per_month": 18.0,
    "bills_on_time": 0.97,
    "recharge_regularity": 0.90,
    "savings_ratio": 0.04,
    "sends_money_home": 1.0,
    "bhorsha_score": None,
    "loan_to_income": 4.0,
}


class ScoreRequest(BaseModel):
    """Scoring request payload.

    Provide explicit `features` dict, or `user_id` to score against their latest stored snapshot.
    """

    user_id: str | None = Field(
        default=None,
        description="Applicant user ID. If provided, latest feature snapshot will be retrieved if features is omitted.",
    )
    group: str | None = Field(
        default=None,
        description="Demographic group (e.g. 'F_urban', 'F_rural', 'M_urban', 'M_rural'). Inferred from user if omitted.",
        examples=["F_urban"],
    )
    amount_bdt: float | None = Field(
        default=15000.0,
        ge=0.0,
        description="Requested loan principal amount in Bangladeshi Taka (BDT)",
        examples=[15000.0],
    )
    features: dict[str, Any] | None = Field(
        default=None,
        description="10 alternative credit features. If omitted, fetched from user_id feature snapshot.",
        examples=[MOON_EXAMPLE_FEATURES],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "group": "F_urban",
                "amount_bdt": 15000.0,
                "features": MOON_EXAMPLE_FEATURES,
            }
        }
    }


class ReasonItem(BaseModel):
    """Individual SHAP score driver with English and Bangla explanations."""

    feature: str
    label: str
    text: str
    impact: float
    kind: str


class ScoreResponse(BaseModel):
    """Complete credit decision, risk tier, Bangla reasons, and actionable tips."""

    decision_id: str | None = Field(default=None, description="Persisted decision record ID")
    p_repay: float = Field(..., description="Estimated repayment probability [0.0, 1.0]")
    score: int = Field(..., description="TrustLedger credit score [300, 900]")
    band: str = Field(..., description="Risk tier: Excellent | Good | Fair | Building")
    approved: bool = Field(..., description="Final lending approval status")
    fairness_ok: bool = Field(default=True, description="Fairness Agent sign-off")
    good: list[str] = Field(..., description="Top positive drivers (Bangla)")
    bad: list[str] = Field(..., description="Top negative drivers (Bangla)")
    tips: list[str] = Field(..., description="Actionable improvement recommendations (Bangla)")
    reasons: list[ReasonItem] = Field(..., description="Structured feature attributions")
    group: str = Field(..., description="Demographic group used for fair calibrated threshold")
    threshold_used: float = Field(..., description="Calibrated decision threshold applied")
    model_version: str = Field(..., description="Model artifact SHA-256 fingerprint")
    feature_hash: str | None = Field(default=None, description="Feature vector fingerprint")
    data_quality: DataQualityBlock | None = Field(
        default=None, description="Data verification & quality metrics"
    )
    ocr_backend: str | None = Field(default=None, description="Active OCR extraction backend")
    timestamp: datetime = Field(..., description="Decision generation timestamp")


class ExplainResponse(BaseModel):
    """Full explainability breakdown for a previously rendered decision."""

    decision_id: str
    score: int
    band: str
    approved: bool
    good: list[str]
    bad: list[str]
    tips: list[str]
    reasons: list[ReasonItem]
    model_version: str
    timestamp: datetime
