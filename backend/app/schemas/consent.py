"""Consent request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ConsentRequest(BaseModel):
    """Payload to grant data access consent."""

    user_id: str = Field(..., description="Applicant unique identifier")
    source: str = Field(
        ...,
        description="Data source category",
        examples=["sms", "bills", "recharge", "ocr", "bhorsha"],
    )


class ConsentResponse(BaseModel):
    """Response returned upon granting consent."""

    status: str = Field("granted", description="Consent status")
    user_id: str
    source: str
    granted_at: datetime


class ConsentRevokeResponse(BaseModel):
    """Response returned upon revoking consent."""

    status: str = Field("revoked", description="Revocation status")
    user_id: str
    source: str
