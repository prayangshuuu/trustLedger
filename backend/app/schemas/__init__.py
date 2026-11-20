"""Schemas package exposing request and response models."""

from app.schemas.common import ErrorResponse
from app.schemas.consent import (
    ConsentRequest,
    ConsentResponse,
    ConsentRevokeResponse,
)
from app.schemas.documents import DocumentUploadResponse
from app.schemas.fairness import (
    FairnessReportResponse,
    GroupFairnessMetrics,
    InclusionLiftResponse,
)
from app.schemas.features import (
    FeatureSnapshotResponse,
    ParseSmsRequest,
    ParseSmsResponse,
    StoreFeatureSnapshotRequest,
)
from app.schemas.score import ExplainResponse, ReasonItem, ScoreRequest, ScoreResponse

__all__ = [
    "ConsentRequest",
    "ConsentResponse",
    "ConsentRevokeResponse",
    "DocumentUploadResponse",
    "ErrorResponse",
    "ExplainResponse",
    "FairnessReportResponse",
    "FeatureSnapshotResponse",
    "GroupFairnessMetrics",
    "InclusionLiftResponse",
    "ParseSmsRequest",
    "ParseSmsResponse",
    "ReasonItem",
    "ScoreRequest",
    "ScoreResponse",
    "StoreFeatureSnapshotRequest",
]
