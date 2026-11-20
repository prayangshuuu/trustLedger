"""Consent lifecycle, borrower sessions, profile and delete-my-data."""

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import ApiKeyAuth, CurrentUserId, DbSession, authorize_user_access
from app.db.models import Application, DecisionRecord, User
from app.privacy.consent import get_active_consents, grant_consent, revoke_consent
from app.privacy.deletion import delete_user_data
from app.schemas.consent import ConsentRequest, ConsentResponse, ConsentRevokeResponse
from app.security import issue_token

router = APIRouter(tags=["Privacy & Consent"])

AuthHeader = Annotated[str | None, Header(alias="Authorization")]
KeyHeader = Annotated[str | None, Header(alias="X-API-Key")]


class SessionRequest(BaseModel):
    user_id: str


class SessionResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: int
    user_id: str


class RegisterUserRequest(BaseModel):
    phone: str | None = None
    gender: str = "F"
    region: str = "urban"
    division: str = "Dhaka"


@router.post(
    "/auth/register",
    response_model=SessionResponse,
    summary="Register a real user or guest session",
)
def register_user(
    payload: RegisterUserRequest, db: DbSession, _api_key: ApiKeyAuth = None
) -> SessionResponse:
    """Register a new borrower user and return an active session token."""
    import hashlib
    import uuid

    if payload.phone and payload.phone.strip():
        phone_hash = hashlib.sha256(payload.phone.strip().encode()).hexdigest()
    else:
        phone_hash = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()

    existing = db.scalars(select(User).where(User.phone_hash == phone_hash)).first()
    if existing:
        user = existing
    else:
        user = User(
            id=str(uuid.uuid4()),
            phone_hash=phone_hash,
            gender=payload.gender,
            region=payload.region,
            division=payload.division,
            has_bank_account=False,
            has_salary_slip=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token, expires = issue_token(user.id)
    return SessionResponse(token=token, expires_at=expires, user_id=user.id)


@router.post("/auth/session", response_model=SessionResponse, summary="Issue a borrower session")
def create_session(
    payload: SessionRequest, db: DbSession, _api_key: ApiKeyAuth = None
) -> SessionResponse:
    """Issue a signed 12-hour borrower token. Requires the app's API key; in production this
    step sits behind phone-number OTP verification."""
    if db.get(User, payload.user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User '{payload.user_id}' not found")
    token, expires = issue_token(payload.user_id)
    return SessionResponse(token=token, expires_at=expires, user_id=payload.user_id)


@router.post(
    "/consent",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant Data Source Consent",
)
def create_consent(
    payload: ConsentRequest,
    db: DbSession,
    authorization: AuthHeader = None,
    x_api_key: KeyHeader = None,
) -> ConsentResponse:
    """Grant or reactivate consent for one source (sms, bills, recharge, ocr, bhorsha)."""
    authorize_user_access(payload.user_id, authorization, x_api_key)
    if db.get(User, payload.user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User '{payload.user_id}' not found")
    try:
        consent = grant_consent(db, payload.user_id, payload.source)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ConsentResponse(
        status="granted",
        user_id=consent.user_id,
        source=consent.source,
        granted_at=consent.granted_at,
    )


@router.delete(
    "/consent/{source}",
    response_model=ConsentRevokeResponse,
    summary="Revoke Data Source Consent",
)
def remove_consent(
    source: str,
    db: DbSession,
    user_id: Annotated[str | None, Query(description="User ID (with an API key)")] = None,
    authorization: AuthHeader = None,
    x_api_key: KeyHeader = None,
) -> ConsentRevokeResponse:
    """Revoke consent for a data source. Scoring stops using it immediately."""
    from app.security import verify_token

    target = user_id
    if not target and authorization and authorization.startswith("Bearer "):
        target = verify_token(authorization[7:].strip())
    if not target:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Session token or user_id + API key required"
        )
    authorize_user_access(target, authorization, x_api_key)
    try:
        revoke_consent(db, target, source)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ConsentRevokeResponse(status="revoked", user_id=target, source=source)


@router.get("/me", summary="Borrower profile, consents and latest decision")
def get_me(user_id: CurrentUserId, db: DbSession) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    latest = db.scalars(
        select(DecisionRecord)
        .where(DecisionRecord.user_id == user_id)
        .order_by(DecisionRecord.created_at.desc())
    ).first()
    app = db.get(Application, latest.application_id) if latest and latest.application_id else None
    return {
        "user_id": user.id,
        "group": f"{user.gender}_{user.region}",
        "division": user.division,
        "consents": sorted(get_active_consents(db, user_id)),
        "latest_decision": None
        if latest is None
        else {
            "decision_id": latest.id,
            "application_id": latest.application_id,
            "score": latest.score,
            "band": latest.band,
            "approved": latest.approved,
            "status": app.status if app else None,
        },
    }


@router.delete("/me", summary="Delete All User Data (Right to be Forgotten)")
def delete_me(user_id: CurrentUserId, db: DbSession) -> dict[str, str]:
    """Permanently delete the user and every related record and stored document image."""
    existed = delete_user_data(db, user_id)
    if not existed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found"
        )
    return {"status": "deleted", "user_id": user_id}
