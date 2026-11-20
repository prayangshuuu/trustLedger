"""Feature extraction and feature snapshot persistence router."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import ApiKeyAuth, DbSession
from app.config import get_settings
from app.db.models import FeatureSnapshot, User
from app.parsers.features import extract_features
from app.parsers.sms import parse_sms_batch
from app.schemas.features import (
    FeatureSnapshotResponse,
    ParseSmsRequest,
    ParseSmsResponse,
    StoreFeatureSnapshotRequest,
)

router = APIRouter(tags=["Features & Parsers"])


@router.post(
    "/parse/sms",
    response_model=ParseSmsResponse,
    summary="Parse SMS into Transactions and Features (DEMO_MODE only)",
)
def parse_sms_endpoint(
    payload: ParseSmsRequest,
    _api_key: ApiKeyAuth = None,
) -> ParseSmsResponse:
    """Parse raw SMS list, deduplicate transactions, and engineer the 10 credit scoring features.

    Strictly gated to DEMO_MODE=true to ensure zero raw SMS handling in production.
    """
    settings = get_settings()
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SMS parsing endpoint is only available when DEMO_MODE=true.",
        )

    # 1. Parse SMS into deduplicated structured transactions
    transactions = parse_sms_batch(payload.sms_list, use_llm_fallback=True)

    # 2. Extract features from transactions
    extraction = extract_features(
        transactions=transactions,
        requested_amount_bdt=payload.requested_amount_bdt,
        default_due_day=payload.default_due_day,
    )

    return ParseSmsResponse(
        transactions=transactions,
        features=extraction.features,
        needs_bhorsha=extraction.needs_bhorsha,
        months_on_wallet=extraction.months_on_wallet,
        total_transactions=extraction.total_transactions,
    )


@router.post(
    "/features",
    response_model=FeatureSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store Feature Snapshot",
)
def store_feature_snapshot(
    payload: StoreFeatureSnapshotRequest,
    db: DbSession,
    _api_key: ApiKeyAuth = None,
) -> FeatureSnapshotResponse:
    """Persist an applicant feature snapshot for scoring evaluation."""
    user = db.scalars(select(User).where(User.id == payload.user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{payload.user_id}' not found.",
        )

    snapshot = FeatureSnapshot(
        user_id=user.id,
        features=payload.features,
        source_summary=payload.source_summary,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return FeatureSnapshotResponse(
        id=snapshot.id,
        user_id=snapshot.user_id,
        features=snapshot.features,
        source_summary=snapshot.source_summary,
        created_at=snapshot.created_at,
    )
