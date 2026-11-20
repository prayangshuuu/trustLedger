"""Schemas for real user multi-source data upload and review flow."""

from typing import Any

from pydantic import BaseModel, Field

from app.core.validation import DataQualityBlock
from app.parsers.sms import Transaction


class UploadSmsResponse(BaseModel):
    """Result of parsing uploaded SMS export or pasted text."""

    transactions: list[Transaction] = Field(..., description="Extracted transactions for review")
    total_messages_parsed: int = Field(..., ge=0)
    low_confidence_count: int = Field(..., ge=0)
    months_covered: float = Field(..., ge=0.0)


class ConfirmUploadRequest(BaseModel):
    """User-confirmed and edited transactions and bill records from review screen."""

    user_id: str = Field(..., description="Applicant User UUID")
    transactions: list[Transaction] = Field(
        default_factory=list, description="Confirmed transactions"
    )
    bill_records: list[dict[str, Any]] = Field(
        default_factory=list, description="Extracted bill/receipt metadata"
    )
    requested_amount_bdt: float = Field(default=15000.0, ge=1000.0)
    default_due_day: int = Field(default=5, ge=1, le=31)


class ConfirmUploadResponse(BaseModel):
    """Response after confirming reviewed data, engineering features, and running validation."""

    features: dict[str, float | None] = Field(..., description="Engineered credit features")
    data_quality: DataQualityBlock = Field(
        ..., description="Confidence and quality metrics with Bangla notes"
    )
    feature_hash: str = Field(..., description="Deterministic SHA-256 fingerprint of features")
    needs_bhorsha: bool = Field(
        ..., description="True if wallet history is insufficient (<3 months)"
    )
    months_on_wallet: float = Field(..., ge=0.0)
    can_apply: bool = Field(..., description="True if eligible to proceed to scoring")
    validation_flags: list[str] = Field(default_factory=list)
