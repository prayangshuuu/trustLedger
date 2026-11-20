"""LangGraph supervisor pipeline: Data -> (Bhorsha?) -> Scoring -> Explainer -> Fairness -> decision.

The supervisor routes deterministically (policy in agents/prompts/supervisor.md); each worker
returns to it. Every node appends a timed entry to the trace, which is stored in audit_log
together with model and prompt versions.
"""

import operator
import time
import uuid
from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.explainer import explain_decision
from app.agents.prompts import prompt_versions
from app.config import get_settings
from app.core.decision import Decision, score_applicant
from app.core.features import FEATURE_NAMES
from app.core.model import get_model_version
from app.core.validation import (
    DataQualityBlock,
    compute_feature_hash,
    validate_features_before_scoring,
)
from app.db.models import AuditLog, DocumentRecord, FeatureSnapshot, User
from app.parsers.features import extract_features
from app.parsers.ocr import get_active_ocr_backend
from app.parsers.sms import parse_sms_batch
from app.privacy.consent import get_active_consents
from app.services.decisions import FairnessCheck, fairness_check, persist_decision

BORDERLINE_MARGIN = 0.03
WALLET_FEATURES = tuple(f for f in FEATURE_NAMES if f not in ("bhorsha_score", "loan_to_income"))
PIPELINE_VERSION = "1.0.0"


class TraceEntry(TypedDict):
    node: str
    ms: float
    ok: bool
    detail: dict[str, Any]


class PipelineState(TypedDict, total=False):
    trace_id: str
    user_id: str
    group: str
    amount_bdt: float
    consents: list[str]
    sms: list[str] | None
    input_features: dict[str, Any] | None
    documents: list[dict[str, Any]]
    features: dict[str, Any]
    data_quality: dict[str, Any]
    feature_hash: str
    sources: list[str]
    needs_bhorsha: bool
    bhorsha_required: bool
    decision: dict[str, Any] | None
    explanation: dict[str, Any] | None
    fairness: dict[str, Any] | None
    status: str
    error: str | None
    decision_id: str | None
    next: str
    trace: Annotated[list[TraceEntry], operator.add]


def _db(config: RunnableConfig) -> Session:
    return config["configurable"]["db"]  # type: ignore[no-any-return]


def traced(name: str) -> Callable[[Callable[..., dict[str, Any]]], Callable[..., dict[str, Any]]]:
    def wrap(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
        def node(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
            start = time.perf_counter()
            update = fn(state, config)
            detail = update.pop("_detail", {})
            ok = not update.get("error")
            entry: TraceEntry = {
                "node": name,
                "ms": round((time.perf_counter() - start) * 1000, 2),
                "ok": ok,
                "detail": detail,
            }
            update["trace"] = [entry]
            return update

        node.__name__ = name
        return node

    return wrap


# ---- supervisor -------------------------------------------------------------------------


def supervisor(state: PipelineState) -> dict[str, Any]:
    done = {t["node"] for t in state.get("trace", [])}
    if state.get("error") or state.get("bhorsha_required"):
        nxt = "finalize"
    elif "data_agent" not in done:
        nxt = "data_agent"
    elif "bhorsha_router" not in done:
        nxt = "bhorsha_router"
    elif "scoring_agent" not in done:
        nxt = "scoring_agent"
    elif "explainer_agent" not in done:
        nxt = "explainer_agent"
    elif "fairness_agent" not in done:
        nxt = "fairness_agent"
    else:
        nxt = "finalize"
    return {"next": nxt}


# ---- workers ----------------------------------------------------------------------------


@traced("data_agent")
def data_agent(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
    db = _db(config)
    consents = set(state.get("consents", []))
    sources: list[str] = []
    amount = state.get("amount_bdt")

    docs: list[dict[str, Any]] = []
    if consents & {"ocr", "bills"}:
        for d in db.scalars(
            select(DocumentRecord).where(DocumentRecord.user_id == state["user_id"])
        ):
            docs.append({"document_type": d.document_type, **(d.extracted_fields or {})})
    bills = [d for d in docs if d["document_type"] == "utility_bill"]

    latest = db.scalars(
        select(FeatureSnapshot)
        .where(FeatureSnapshot.user_id == state["user_id"])
        .order_by(FeatureSnapshot.created_at.desc())
    ).first()
    previous = dict(latest.features) if latest else {}

    features: dict[str, Any]
    needs_bhorsha = False
    if state.get("input_features"):
        if not consents & {"sms", "bills", "recharge", "bhorsha"}:
            return {
                "error": "CONSENT_MISSING: no active data consent",
                "_detail": {"consents": sorted(consents)},
            }
        features = dict(state["input_features"] or {})
        sources.append("provided_features")
    elif state.get("sms"):
        if not get_settings().DEMO_MODE:
            return {
                "error": "DEMO_ONLY: raw SMS is accepted only when DEMO_MODE=true",
                "_detail": {},
            }
        if "sms" not in consents:
            return {"error": "CONSENT_MISSING: sms", "_detail": {"consents": sorted(consents)}}
        txs = parse_sms_batch(state["sms"] or [], use_llm_fallback=True)
        result = extract_features(txs, requested_amount_bdt=amount, ocr_bills=bills or None)
        features = dict(result.features)
        needs_bhorsha = result.needs_bhorsha
        sources.append(f"sms:{len(txs)}_transactions")
        if bills:
            sources.append(f"ocr:{len(bills)}_bills")
        features["bhorsha_score"] = previous.get("bhorsha_score")
        db.add(
            FeatureSnapshot(
                user_id=state["user_id"],
                features=features,
                source_summary=", ".join(sources)[:255],
            )
        )
        db.flush()
    elif previous:
        if not consents:
            return {"error": "CONSENT_MISSING: no active data consent", "_detail": {}}
        features = previous
        sources.append("latest_snapshot")
    else:
        features = {}
        needs_bhorsha = True

    features = {k: features.get(k) for k in FEATURE_NAMES}
    inflow = features.get("monthly_inflow_bdt")
    if amount and inflow:
        features["loan_to_income"] = round(float(amount) / float(inflow), 4)
    if all(features.get(f) is None for f in WALLET_FEATURES):
        needs_bhorsha = True

    if all(v is None for v in features.values()):
        dq_block = DataQualityBlock(
            sources_used=["zero_history"],
            months_covered=0.0,
            transactions_counted=0,
            flags=["all_features_null", "needs_bhorsha"],
            confidence=0.5,
            notes_bn=["পর্যাপ্ত লেনদেনের তথ্য নেই, ভরসা মূল্যায়ন প্রয়োজন।"],
        )
        return {
            "features": features,
            "data_quality": dq_block.model_dump(),
            "feature_hash": compute_feature_hash(features),
            "documents": docs,
            "sources": sources or ["zero_history"],
            "needs_bhorsha": True,
            "_detail": {
                "sources": sources or ["zero_history"],
                "documents": len(docs),
                "non_null_features": 0,
                "ocr_backend": get_active_ocr_backend(),
                "data_quality_confidence": 0.5,
                "data_quality_flags": ["all_features_null", "needs_bhorsha"],
            },
        }

    # Run AI validation guardrails on feature vector
    val_res = validate_features_before_scoring(
        features,
        raw_sources={"transactions": txs if "txs" in locals() else [], "documents": docs},
        enforce_sufficiency=False,
    )
    validated_features = val_res.features
    dq_dict = val_res.data_quality.model_dump()
    f_hash = val_res.feature_hash

    return {
        "features": validated_features,
        "data_quality": dq_dict,
        "feature_hash": f_hash,
        "documents": docs,
        "sources": sources,
        "needs_bhorsha": needs_bhorsha,
        "_detail": {
            "sources": sources,
            "documents": len(docs),
            "non_null_features": sum(v is not None for v in validated_features.values()),
            "ocr_backend": get_active_ocr_backend(),
            "data_quality_confidence": dq_dict.get("confidence"),
            "data_quality_flags": dq_dict.get("flags"),
        },
    }


@traced("bhorsha_router")
def bhorsha_router(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
    has_bhorsha = state.get("features", {}).get("bhorsha_score") is not None
    required = bool(state.get("needs_bhorsha")) and not has_bhorsha
    if required and "bhorsha" not in state.get("consents", []):
        reason = "no wallet history; Bhorsha consent needed"
    elif required:
        reason = "no wallet history and no bhorsha_score"
    else:
        reason = (
            "wallet history present" if not state.get("needs_bhorsha") else "bhorsha_score present"
        )
    return {
        "bhorsha_required": required,
        "_detail": {"bhorsha_required": required, "reason": reason},
    }


@traced("scoring_agent")
def scoring_agent(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
    try:
        decision = score_applicant(state["features"], group=state["group"])
        if state.get("data_quality"):
            decision.data_quality = state["data_quality"]
        if state.get("feature_hash"):
            decision.feature_hash = state["feature_hash"]
    except ValueError as e:  # includes AllFeaturesMissingError and unknown group
        return {"error": f"SCORING_FAILED: {e}", "_detail": {}}
    return {
        "decision": decision.model_dump(mode="json"),
        "_detail": {
            "p_repay": round(decision.p_repay, 4),
            "score": decision.score,
            "band": decision.band,
            "feature_hash": decision.feature_hash,
        },
    }


@traced("explainer_agent")
def explainer_agent(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
    decision = Decision.model_validate(state["decision"])
    out = explain_decision(_db(config), decision)
    return {
        "explanation": out.model_dump(mode="json"),
        "_detail": {
            "summary_source": out.summary_source,
            "cited_tips": sum(t.source is not None for t in out.grounded_tips),
            "mentioned_features": out.mentioned_features,
        },
    }


@traced("fairness_agent")
def fairness_agent(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
    decision = Decision.model_validate(state["decision"]) if state.get("decision") else None
    check = fairness_check(decision, state["group"], state.get("features", {}))
    flags = state.get("data_quality", {}).get("flags", [])
    if not check.ok or decision is None:
        status = "blocked"
    elif (
        "extreme_ood_detected" in flags
        or any("ood_" in f for f in flags)
        or abs(decision.p_repay - decision.threshold_used) <= BORDERLINE_MARGIN
    ):
        status = "needs_review"
    else:
        status = "approved" if decision.approved else "rejected"
    return {
        "fairness": check.model_dump(),
        "status": status,
        "_detail": {"status": status, **check.checks, "blocked_reason": check.blocked_reason},
    }


@traced("finalize")
def finalize(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
    db = _db(config)
    status = state.get("status")
    if state.get("error"):
        status = "rejected_input"
    elif state.get("bhorsha_required"):
        status = "bhorsha_required"
    decision_id: str | None = None
    if (
        state.get("decision")
        and state.get("fairness")
        and status
        in (
            "approved",
            "rejected",
            "needs_review",
            "blocked",
        )
    ):
        decision = Decision.model_validate(state["decision"])
        fairness = FairnessCheck.model_validate(state["fairness"])
        user = db.get(User, state["user_id"])
        record = persist_decision(
            db,
            decision,
            features=state.get("features", {}),
            user=user,
            amount_bdt=float(state.get("amount_bdt") or 15000.0),
            fairness=fairness,
            status=status,
            event="agent_decision",
            extra_audit={
                "trace_id": state["trace_id"],
                "status": status,
                "data_quality": state.get("data_quality"),
                "feature_hash": state.get("feature_hash"),
                "ocr_backend": get_active_ocr_backend(),
            },
        )
        decision_id = record.id
    return {"status": status, "decision_id": decision_id, "_detail": {"status": status}}


def build_graph() -> Any:
    graph = StateGraph(PipelineState)
    graph.add_node("supervisor", supervisor)
    workers = {
        "data_agent": data_agent,
        "bhorsha_router": bhorsha_router,
        "scoring_agent": scoring_agent,
        "explainer_agent": explainer_agent,
        "fairness_agent": fairness_agent,
    }
    for name, fn in workers.items():
        graph.add_node(name, fn)
        graph.add_edge(name, "supervisor")
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor", lambda s: s["next"], {**{n: n for n in workers}, "finalize": "finalize"}
    )
    graph.add_edge("finalize", END)
    return graph.compile()


_compiled: Any = None


def get_graph() -> Any:
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def run_pipeline(
    db: Session,
    user: User,
    amount_bdt: float,
    sms: list[str] | None = None,
    features: dict[str, Any] | None = None,
) -> PipelineState:
    """Run the full agent graph for one application and store its trace in audit_log."""
    trace_id = f"trace_{uuid.uuid4().hex[:16]}"
    initial: PipelineState = {
        "trace_id": trace_id,
        "user_id": user.id,
        "group": f"{user.gender}_{user.region}",
        "amount_bdt": amount_bdt,
        "consents": get_active_consents(db, user.id),
        "sms": sms,
        "input_features": features,
        "trace": [],
    }
    start = time.perf_counter()
    final: PipelineState = get_graph().invoke(initial, config={"configurable": {"db": db}})
    db.add(
        AuditLog(
            user_id=user.id,
            event="agent_trace",
            entity_type="trace",
            entity_id=trace_id,
            details={
                "pipeline_version": PIPELINE_VERSION,
                "status": final.get("status"),
                "decision_id": final.get("decision_id"),
                "error": final.get("error"),
                "group": initial["group"],
                "model_version": get_model_version(),
                "prompt_versions": prompt_versions(),
                "total_ms": round((time.perf_counter() - start) * 1000, 2),
                "nodes": final.get("trace", []),
            },
        )
    )
    db.commit()
    return final
