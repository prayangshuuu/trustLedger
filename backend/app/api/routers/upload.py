"""Real user multi-source upload and review endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import ApiKeyAuth, DbSession
from app.core.validation import compute_feature_hash, validate_features_before_scoring
from app.db.models import FeatureSnapshot, User
from app.parsers.features import extract_features
from app.parsers.sms import (
    extract_messages_from_export,
    parse_sms_batch,
)
from app.privacy.consent import ConsentMissingError, has_consent
from app.schemas.upload import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    UploadSmsResponse,
)

logger = logging.getLogger("trustledger.upload")

router = APIRouter(prefix="/upload", tags=["Real User Upload"])

MAX_SMS_FILE_BYTES = 10_000_000  # 10 MB limit


@router.post(
    "/sms",
    response_model=UploadSmsResponse,
    summary="Upload and Parse SMS Export or Pasted Text (In-Memory Only)",
)
async def upload_sms(
    request: Request,
    db: DbSession,
    _api_key: ApiKeyAuth = None,
) -> UploadSmsResponse:
    """Ingest SMS export or pasted text, redact PII, and extract transactions in memory for review.

    Strict compliance: Raw SMS text is NEVER stored in database or persistent logs.
    """
    content_type = request.headers.get("content-type", "")
    user_id = ""
    raw_text: str | None = None
    file_bytes: bytes | None = None
    filename: str | None = None

    if "application/json" in content_type:
        body = await request.json()
        user_id = str(body.get("user_id") or "")
        raw_text = body.get("raw_text")
    else:
        form = await request.form()
        user_id = str(form.get("user_id") or "")
        raw_text_val = form.get("raw_text")
        if isinstance(raw_text_val, str):
            raw_text = raw_text_val
        upload_item = form.get("file")
        if upload_item is not None and hasattr(upload_item, "read"):
            filename = getattr(upload_item, "filename", None)
            file_bytes = await upload_item.read(MAX_SMS_FILE_BYTES + 1)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field 'user_id'.",
        )

    user = db.scalars(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Applicant user '{user_id}' not found.",
        )

    # Granular consent check
    if not (has_consent(db, user_id, "sms") or has_consent(db, user_id, "financial_sms")):
        raise ConsentMissingError(
            f"Applicant '{user_id}' lacks active consent for SMS processing (sms)."
        )

    content: str | bytes = ""
    if file_bytes is not None and len(file_bytes) > 0:
        if len(file_bytes) > MAX_SMS_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="SMS export file exceeds 10 MB limit.",
            )
        content = file_bytes
    elif raw_text and raw_text.strip():
        content = raw_text.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide an SMS export file (.txt, .csv, .xml) or paste SMS text.",
        )

    messages = extract_messages_from_export(content, filename=filename)
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid SMS messages found in the uploaded content.",
        )

    # In-memory parsing only - raw messages are never persisted
    transactions = parse_sms_batch(messages, use_llm_fallback=True)

    months_covered = 0.0
    if len(transactions) >= 2:
        date_min = min(t.date for t in transactions)
        date_max = max(t.date for t in transactions)
        months_covered = round(max(0.1, (date_max - date_min).days / 30.4375), 1)

    low_confidence_count = sum(1 for t in transactions if t.confidence < 0.70)

    return UploadSmsResponse(
        transactions=transactions,
        total_messages_parsed=len(messages),
        low_confidence_count=low_confidence_count,
        months_covered=months_covered,
    )


@router.post(
    "/confirm",
    response_model=ConfirmUploadResponse,
    summary="Confirm Reviewed Data, Validate AI Outputs, and Persist Snapshot",
)
def confirm_upload(
    payload: ConfirmUploadRequest,
    db: DbSession,
    _api_key: ApiKeyAuth = None,
) -> ConfirmUploadResponse:
    """Validate user-reviewed transactions and documents, extract credit features, and store snapshot."""
    user = db.scalars(select(User).where(User.id == payload.user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Applicant user '{payload.user_id}' not found.",
        )

    # Extract features from confirmed data
    txs = payload.transactions
    bills = payload.bill_records or None

    extraction = extract_features(
        transactions=txs,
        requested_amount_bdt=payload.requested_amount_bdt,
        default_due_day=payload.default_due_day,
        ocr_bills=bills,
    )

    # Run AI output validator (range check, OOD check, sufficiency, cross-checks)
    tx_dicts = [t.model_dump() for t in txs]
    val_result = validate_features_before_scoring(
        extraction.features,
        raw_sources={"transactions": tx_dicts, "documents": bills or []},
        enforce_sufficiency=False,
    )

    feature_hash = compute_feature_hash(val_result.cleaned_features)

    # Persist validated features snapshot (non-raw features only)
    sources = []
    if txs:
        sources.append(f"sms:{len(txs)}_txs")
    if bills:
        sources.append(f"ocr:{len(bills)}_bills")
    source_summary = ", ".join(sources) if sources else "user_confirmed"

    snapshot = FeatureSnapshot(
        user_id=user.id,
        features=val_result.cleaned_features,
        source_summary=source_summary[:255],
    )
    db.add(snapshot)
    db.commit()

    needs_bhorsha = bool(extraction.needs_bhorsha or val_result.data_quality.months_covered < 3.0)
    can_apply = bool(val_result.valid and not needs_bhorsha)

    return ConfirmUploadResponse(
        features=val_result.cleaned_features,
        data_quality=val_result.data_quality,
        feature_hash=feature_hash,
        needs_bhorsha=needs_bhorsha,
        months_on_wallet=extraction.months_on_wallet,
        can_apply=can_apply,
        validation_flags=val_result.flags,
    )
