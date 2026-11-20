"""Agent pipeline endpoint: one call from raw inputs to a fair, explained decision."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.agents.graph import run_pipeline
from app.api.deps import ApiKeyAuth, DbSession
from app.core.validation import DataQualityBlock
from app.db.models import AuditLog, DecisionRecord, User
from app.parsers.ocr import get_active_ocr_backend
from app.schemas.apply import ApplyDecision, ApplyRequest, ApplyResponse, TraceResponse
from app.schemas.score import ReasonItem

router = APIRouter(tags=["Agent Pipeline"])


@router.post("/apply", response_model=ApplyResponse, summary="Run the multi-agent pipeline")
def apply(payload: ApplyRequest, db: DbSession, _api_key: ApiKeyAuth = None) -> ApplyResponse:
    """Data -> Bhorsha router -> Scoring -> Explainer -> Fairness. Returns the decision and trace id.

    Status ``bhorsha_required`` means the user has no wallet history: run /bhorsha first.
    ``needs_review`` means p_repay is within 0.03 of the group threshold.
    """
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Applicant user '{payload.user_id}' not found"
        )

    state = run_pipeline(db, user, payload.amount_bdt, sms=payload.sms, features=payload.features)
    decision_out: ApplyDecision | None = None
    if state.get("decision"):
        d = state["decision"] or {}
        reasons = [ReasonItem(**r) for r in d["reasons"]]
        record = db.get(DecisionRecord, state["decision_id"]) if state.get("decision_id") else None
        d_dq_raw = d.get("data_quality")
        d_dq_block = (
            DataQualityBlock.model_validate(d_dq_raw)
            if isinstance(d_dq_raw, dict)
            else d_dq_raw
            if isinstance(d_dq_raw, DataQualityBlock)
            else None
        )
        decision_out = ApplyDecision(
            decision_id=state.get("decision_id"),
            application_id=record.application_id if record else None,
            p_repay=d["p_repay"],
            score=d["score"],
            band=d["band"],
            approved=state.get("status") == "approved",
            threshold_used=d["threshold_used"],
            model_version=d["model_version"],
            feature_hash=d.get("feature_hash"),
            data_quality=d_dq_block,
            ocr_backend=get_active_ocr_backend(),
            reasons=reasons,
            good=[r.text for r in reasons if r.kind == "good"],
            bad=[r.text for r in reasons if r.kind == "bad"],
            tips=d["tips"],
        )
    explanation = state.get("explanation") or {}
    dq_raw = state.get("data_quality")
    dq_block = (
        DataQualityBlock.model_validate(dq_raw)
        if isinstance(dq_raw, dict)
        else dq_raw
        if isinstance(dq_raw, DataQualityBlock)
        else None
    )
    return ApplyResponse(
        trace_id=state["trace_id"],
        status=state.get("status") or "rejected_input",
        bhorsha_required=bool(state.get("bhorsha_required")),
        error=state.get("error"),
        decision=decision_out,
        data_quality=dq_block,
        summary_bn=explanation.get("summary_bn"),
        grounded_tips=explanation.get("grounded_tips", []),
        fairness=state.get("fairness"),
        features=state.get("features", {}),
        trace=[dict(t) for t in state.get("trace", [])],
    )


@router.get("/traces/{trace_id}", response_model=TraceResponse, summary="Get an agent run trace")
def get_trace(trace_id: str, db: DbSession, _api_key: ApiKeyAuth = None) -> TraceResponse:
    entry = db.scalars(
        select(AuditLog).where(AuditLog.entity_type == "trace", AuditLog.entity_id == trace_id)
    ).first()
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Trace '{trace_id}' not found")
    return TraceResponse(
        trace_id=trace_id,
        user_id=entry.user_id,
        created_at=entry.created_at.isoformat(),
        details=entry.details,
    )
