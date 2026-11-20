"""Bhorsha conversational psychometric assessment router."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import ApiKeyAuth, DbSession
from app.bhorsha.interviewer import (
    answer_bhorsha_question,
    get_bhorsha_result,
    start_bhorsha_session,
)
from app.db.models import User
from app.privacy.consent import ConsentMissingError, has_consent
from app.schemas.bhorsha import (
    BhorshaAnswerRequest,
    BhorshaAnswerResponse,
    BhorshaResultResponse,
    BhorshaStartRequest,
    BhorshaStartResponse,
)

router = APIRouter(prefix="/bhorsha", tags=["Bhorsha Psychometric Assessment"])


@router.post(
    "/start",
    response_model=BhorshaStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Bhorsha Assessment Session",
)
def start_session_endpoint(
    payload: BhorshaStartRequest,
    db: DbSession,
    _api_key: ApiKeyAuth = None,
) -> BhorshaStartResponse:
    """Initialize a psychometric dialogue for zero-history borrowers.

    Enforces active consent for the 'bhorsha' data source before beginning.
    """
    user = db.scalars(select(User).where(User.id == payload.user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Applicant user '{payload.user_id}' not found.",
        )

    if not has_consent(db, user.id, "bhorsha"):
        raise ConsentMissingError(
            f"Applicant '{user.id}' lacks active consent for Bhorsha psychometric assessment."
        )

    session_id, first_q = start_bhorsha_session(user.id)

    return BhorshaStartResponse(
        session_id=session_id,
        question_id=first_q["question_id"],
        dimension=first_q["dimension"],
        question_text=first_q["question_text"],
        english_translation=first_q["english_translation"],
        turn=first_q["turn"],
        total_turns=first_q["total_turns"],
    )


@router.post(
    "/{session_id}/answer",
    response_model=BhorshaAnswerResponse,
    summary="Submit Scenario Answer",
)
def submit_answer_endpoint(
    session_id: str,
    payload: BhorshaAnswerRequest,
    _api_key: ApiKeyAuth = None,
) -> BhorshaAnswerResponse:
    """Record an answer to the current scenario and return next question or completion notification."""
    try:
        resp = answer_bhorsha_question(
            session_id=session_id,
            answer_text=payload.answer,
            elapsed_seconds=payload.elapsed_seconds,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bhorsha session '{session_id}' not found.",
        ) from None

    return BhorshaAnswerResponse(
        completed=resp["completed"],
        off_topic=resp.get("off_topic", False),
        turn=resp.get("turn", 1),
        total_turns=resp.get("total_turns"),
        acknowledgement=resp.get("acknowledgement"),
        message=resp.get("message"),
        question_id=resp.get("question_id"),
        dimension=resp.get("dimension"),
        question_text=resp.get("question_text"),
        english_translation=resp.get("english_translation"),
    )


@router.get(
    "/{session_id}/result",
    response_model=BhorshaResultResponse,
    summary="Get Bhorsha Assessment Outcome and Update Snapshot",
)
def get_result_endpoint(
    session_id: str,
    db: DbSession,
    _api_key: ApiKeyAuth = None,
) -> BhorshaResultResponse:
    """Compute aggregate Bhorsha score and write bhorsha_score into applicant feature snapshot."""
    try:
        result = get_bhorsha_result(session_id=session_id, db=db)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bhorsha session '{session_id}' not found.",
        ) from None

    return BhorshaResultResponse(
        session_id=session_id,
        bhorsha_score=result.bhorsha_score,
        confidence=result.confidence,
        dimension_scores=result.dimension_scores,
        anti_gaming_flags=result.anti_gaming_flags,
        is_consistent=result.is_consistent,
        snapshot_updated=True,
    )
