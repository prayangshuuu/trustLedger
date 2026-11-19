"""Consent lifecycle and Right-to-be-Forgotten privacy endpoints."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.api.deps import CurrentUserId, DbSession
from app.privacy.consent import grant_consent, revoke_consent
from app.privacy.deletion import delete_user_data
from app.schemas.consent import ConsentRequest, ConsentResponse, ConsentRevokeResponse

router = APIRouter(tags=["Privacy & Consent"])


@router.post(
    "/consent",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant Data Source Consent",
)
def create_consent(payload: ConsentRequest, db: DbSession) -> ConsentResponse:
    """Grant or reactivate consent for a specific data source (sms, bills, recharge, ocr, bhorsha)."""
    try:
        consent = grant_consent(db, payload.user_id, payload.source)
        return ConsentResponse(
            status="granted",
            user_id=consent.user_id,
            source=consent.source,
            granted_at=consent.granted_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/consent/{source}",
    response_model=ConsentRevokeResponse,
    summary="Revoke Data Source Consent",
)
def remove_consent(
    source: str,
    db: DbSession,
    user_id: Annotated[str | None, Query(description="Applicant user ID")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> ConsentRevokeResponse:
    """Revoke consent for a given data source. Immediately invalidates scoring access."""
    target_user_id = user_id or x_user_id
    if not target_user_id and authorization and authorization.startswith("Bearer "):
        target_user_id = authorization[7:].strip()

    if not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be provided via query parameter or header",
        )

    try:
        revoke_consent(db, target_user_id, source)
        return ConsentRevokeResponse(status="revoked", user_id=target_user_id, source=source)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/me",
    summary="Delete All User Data (Right to be Forgotten)",
)
def delete_me(user_id: CurrentUserId, db: DbSession) -> dict[str, str]:
    """Permanently delete all user records, consents, applications, and decisions."""
    existed = delete_user_data(db, user_id)
    if not existed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    return {"status": "deleted", "user_id": user_id}
