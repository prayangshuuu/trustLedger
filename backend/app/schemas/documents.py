"""Schemas for document upload, OCR extraction, and storage audit records."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Result of document upload, OCR extraction, and ephemeral storage allocation."""

    id: str = Field(..., description="Document metadata database UUID")
    user_id: str = Field(..., description="Applicant identifier")
    document_type: str = Field(
        ..., description="Detected or verified type: utility_bill | receipt | khata_page"
    )
    storage_key: str = Field(..., description="Ephemeral encrypted storage key in object store")
    extracted_fields: dict[str, Any] = Field(
        ..., description="Extracted key-value financial signals"
    )
    confidence: float = Field(..., description="OCR extraction confidence score [0.0, 1.0]")
    needs_review: bool = Field(
        ..., description="Flagged true if confidence < 0.80 for manual back-office review"
    )
    expires_at: datetime = Field(..., description="30-day retention expiry deadline")
    created_at: datetime = Field(..., description="Upload timestamp")
