"""Scoring pipeline and explanation endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import ApiKeyAuth, DbSession
from app.core.decision import score_applicant
from app.core.features import AllFeaturesMissingError
from app.db.models import DecisionRecord, FeatureSnapshot, User
from app.privacy.consent import ConsentMissingError, has_consent
from app.schemas.score import ExplainResponse, ReasonItem, ScoreRequest, ScoreResponse
from app.services.decisions import fairness_check, persist_decision

router = APIRouter(tags=["Scoring & Decisions"])


@router.post(
    "/score",
    response_model=ScoreResponse,
    summary="Score Applicant (Features or User ID)",
)
def score(payload: ScoreRequest, db: DbSession, _api_key: ApiKeyAuth = None) -> ScoreResponse:
    """Generate a fair, explainable credit decision for an applicant.

    Evaluates either raw features or the user's latest stored feature snapshot.
    Enforces active data consent before running scoring.
    """
    user: User | None = None
    features_dict: dict[str, Any] | None = payload.features
    demographic_group = payload.group

    # 1. Resolve user and enforce consent if user_id is provided
    if payload.user_id:
        user = db.scalars(select(User).where(User.id == payload.user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Applicant user '{payload.user_id}' not found",
            )

        # Check required consent (sms or bhorsha)
        has_sms = has_consent(db, user.id, "sms")
        has_bhorsha = has_consent(db, user.id, "bhorsha")
        if not (has_sms or has_bhorsha):
            raise ConsentMissingError(
                f"Applicant '{user.id}' lacks active consent for required scoring sources (sms or bhorsha)."
            )

        if not features_dict:
            latest_snap = db.scalars(
                select(FeatureSnapshot)
                .where(FeatureSnapshot.user_id == user.id)
                .order_by(FeatureSnapshot.created_at.desc())
            ).first()
            if not latest_snap:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No feature snapshot available for user '{user.id}'. Please provide features directly.",
                )
            features_dict = latest_snap.features

        if not demographic_group:
            demographic_group = f"{user.gender}_{user.region}"

    if features_dict is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feature vector is required either in request body or via stored snapshot.",
        )

    if not demographic_group:
        demographic_group = "F_urban"

    # 2. Run core scoring and explanation pipeline
    try:
        decision_result = score_applicant(features_dict, group=demographic_group)
    except AllFeaturesMissingError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # 3. Fairness sign-off, then persist decision with a full audit entry
    fairness = fairness_check(decision_result, demographic_group, features_dict)
    decision_record = persist_decision(
        db,
        decision_result,
        features=features_dict,
        user=user,
        amount_bdt=payload.amount_bdt or 15000.0,
        fairness=fairness,
    )
    db.commit()

    reasons_items = [
        ReasonItem(
            feature=r.feature,
            label=r.label,
            text=r.text,
            impact=r.impact,
            kind=r.kind,
        )
        for r in decision_result.reasons
    ]

    return ScoreResponse(
        decision_id=decision_record.id,
        p_repay=decision_result.p_repay,
        score=decision_result.score,
        band=decision_result.band,
        approved=decision_record.approved,
        fairness_ok=fairness.ok,
        good=decision_result.good,
        bad=decision_result.bad,
        tips=decision_result.tips,
        reasons=reasons_items,
        group=demographic_group,
        threshold_used=decision_result.threshold_used,
        model_version=decision_result.model_version,
        timestamp=decision_record.created_at or datetime.now(UTC),
    )


@router.get(
    "/explain/{decision_id}",
    response_model=ExplainResponse,
    summary="Get Decision Explanation",
)
def get_explanation(
    decision_id: str, db: DbSession, _api_key: ApiKeyAuth = None
) -> ExplainResponse:
    """Retrieve full SHAP feature attributions and Bangla reasons for a decision."""
    decision = db.scalars(select(DecisionRecord).where(DecisionRecord.id == decision_id)).first()
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision '{decision_id}' not found",
        )

    reasons_raw = decision.reasons or []
    reasons_items = [
        ReasonItem(
            feature=r.get("feature", ""),
            label=r.get("label", ""),
            text=r.get("text", ""),
            impact=float(r.get("impact", 0.0)),
            kind=r.get("kind", "good"),
        )
        for r in reasons_raw
    ]

    good_list = [r.text for r in reasons_items if r.kind == "good"]
    bad_list = [r.text for r in reasons_items if r.kind == "bad"]

    return ExplainResponse(
        decision_id=decision.id,
        score=decision.score,
        band=decision.band,
        approved=decision.approved,
        good=good_list,
        bad=bad_list,
        tips=decision.tips or [],
        reasons=reasons_items,
        model_version=decision.model_version,
        timestamp=decision.created_at or datetime.now(UTC),
    )
