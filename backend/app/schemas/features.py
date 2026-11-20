"""Schemas for feature extraction endpoints and feature snapshot persistence."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.parsers.sms import Transaction


class ParseSmsRequest(BaseModel):
    """Payload to parse an array of SMS messages into transactions and extracted features."""

    sms_list: list[str] = Field(
        ..., min_length=1, description="List of raw or semi-structured SMS strings"
    )
    requested_amount_bdt: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional requested credit amount for loan_to_income ratio",
    )
    default_due_day: int = Field(
        default=25, ge=1, le=31, description="Default day of month for utility bill due dates"
    )


class ParseSmsResponse(BaseModel):
    """Extracted transactions, computed features, and Bhorsha handoff requirement."""

    transactions: list[Transaction] = Field(..., description="Deduplicated structured transactions")
    features: dict[str, float | None] = Field(..., description="Clipped 10 model feature vector")
    needs_bhorsha: bool = Field(
        ..., description="True if applicant history is < 3 months, requiring Bhorsha assessment"
    )
    months_on_wallet: float = Field(..., description="Observed transaction history span in months")
    total_transactions: int = Field(..., description="Count of valid transactions parsed")


class StoreFeatureSnapshotRequest(BaseModel):
    """Payload to persist an applicant feature snapshot in the database."""

    user_id: str = Field(..., description="Registered applicant UUID")
    features: dict[str, Any] = Field(
        ..., description="Applicant feature dictionary (partial or full 10 features)"
    )
    source_summary: str | None = Field(
        default="SMS and digital records",
        description="Audit summary of the data source for this feature set",
    )


class FeatureSnapshotResponse(BaseModel):
    """Persisted feature snapshot representation."""

    id: str
    user_id: str
    features: dict[str, Any]
    source_summary: str | None
    created_at: datetime
