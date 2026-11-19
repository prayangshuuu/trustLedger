"""Common API schemas and structured error models."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized API error response format."""

    error: str = Field(..., description="Error classification or code")
    detail: str = Field(..., description="Human-readable error explanation")
    request_id: str | None = Field(
        default=None, description="Unique correlation request identifier"
    )
    context: dict[str, Any] | None = Field(
        default=None, description="Optional diagnostic error metadata"
    )
