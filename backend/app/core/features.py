"""Feature vector definition and transformation for TrustLedger.

Defines the Pydantic FeatureVector model with validated ranges for the 10 alternative
credit scoring features, and converts vectors to 1-row DataFrames in the exact training order.
"""

from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.model import load_meta

FEATURE_NAMES: tuple[str, ...] = (
    "monthly_inflow_bdt",
    "income_volatility",
    "months_on_wallet",
    "txn_per_month",
    "bills_on_time",
    "recharge_regularity",
    "savings_ratio",
    "sends_money_home",
    "bhorsha_score",
    "loan_to_income",
)


class AllFeaturesMissingError(ValueError):
    """Raised when all features are missing or null."""


class FeatureVector(BaseModel):
    """Applicant feature vector containing alternative financial habits."""

    model_config = ConfigDict(extra="forbid")

    monthly_inflow_bdt: float | None = Field(
        default=None,
        ge=0.0,
        description="Average monthly mobile wallet inflow in Bangladeshi Taka (BDT)",
    )
    income_volatility: float | None = Field(
        default=None,
        ge=0.0,
        description="Standard deviation of monthly income divided by mean inflow",
    )
    months_on_wallet: float | None = Field(
        default=None,
        ge=0.0,
        description="Tenure on mobile financial service wallet in months",
    )
    txn_per_month: float | None = Field(
        default=None,
        ge=0.0,
        description="Average number of wallet transactions per month",
    )
    bills_on_time: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Ratio of utility/service bills paid on or before due date [0.0, 1.0]",
    )
    recharge_regularity: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Consistency index of mobile airtime recharge frequency [0.0, 1.0]",
    )
    savings_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Proportion of monthly inflow retained or sent to DPS/savings [0.0, 1.0]",
    )
    sends_money_home: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Binary or frequency indicator of sending remittances to family [0.0, 1.0]",
    )
    bhorsha_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Bangla conversational psychometric trustworthiness score [0.0, 100.0]",
    )
    loan_to_income: float | None = Field(
        default=None,
        ge=0.0,
        description="Ratio of requested loan principal to monthly inflow",
    )

    @model_validator(mode="before")
    @classmethod
    def sanitize_nan_values(cls, data: Any) -> Any:
        """Convert float NaN, numpy NaN, and pd.NA values in dictionaries to None."""
        if isinstance(data, dict):
            sanitized: dict[str, Any] = {}
            for k, v in data.items():
                if v is None or v is pd.NA or isinstance(v, (float, np.floating)) and np.isnan(v):
                    sanitized[k] = None
                else:
                    sanitized[k] = v
            return sanitized
        return data

    def is_empty(self) -> bool:
        """Check whether all features in this vector are None or NaN."""
        return all(
            v is None or (isinstance(v, (float, np.floating)) and np.isnan(v))
            for v in self.model_dump().values()
        )


def get_feature_order(model_dir: str | None = None) -> list[str]:
    """Retrieve expected feature order from model metadata, falling back to canonical order."""
    try:
        meta = load_meta(model_dir=model_dir)
        meta_features = meta.get("features")
        if isinstance(meta_features, list) and meta_features:
            return [str(f) for f in meta_features]
    except Exception:  # noqa: BLE001, S110
        pass
    return list(FEATURE_NAMES)


def to_dataframe(
    features: FeatureVector | dict[str, Any],
    model_dir: str | None = None,
) -> pd.DataFrame:
    """Convert a FeatureVector or feature dict to a 1-row DataFrame in exact training order.

    Raises:
        AllFeaturesMissingError: If every feature is None or NaN.
    """
    if isinstance(features, dict):
        fv = FeatureVector(**features)
    elif isinstance(features, FeatureVector):
        fv = features
    else:
        raise TypeError(f"Expected FeatureVector or dict, got {type(features).__name__}")

    if fv.is_empty():
        raise AllFeaturesMissingError(
            "All features are missing. At least one feature must be provided to score an applicant."
        )

    feature_order = get_feature_order(model_dir=model_dir)
    row: dict[str, float] = {}
    for col in feature_order:
        val = getattr(fv, col, None)
        row[col] = float(val) if val is not None else np.nan

    return pd.DataFrame([row], columns=feature_order, dtype=float)
