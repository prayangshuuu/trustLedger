"""Decision persistence and the per-decision fairness sign-off."""

import math
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.decision import Decision
from app.core.model import load_meta
from app.db.models import Application, AuditLog, DecisionRecord, User
from app.observability import record_decision

# Sensitive attributes may drive thresholds and audits but must never reach the model.
SENSITIVE_ATTRIBUTES: tuple[str, ...] = ("gender", "region", "division", "age")


class FairnessCheck(BaseModel):
    """Result of the Fairness Agent's sign-off for one decision."""

    ok: bool
    group: str
    threshold_used: float | None
    checks: dict[str, bool]
    blocked_reason: str | None = None


def fairness_check(
    decision: Decision | None, group: str, features: dict[str, Any]
) -> FairnessCheck:
    """Sign off a decision: group threshold exists, was applied, and no sensitive input leaked."""
    thresholds: dict[str, float] = load_meta().get("group_thresholds", {})
    threshold = thresholds.get(group)
    checks = {
        "threshold_present": threshold is not None,
        "no_sensitive_inputs": not any(k in features for k in SENSITIVE_ATTRIBUTES),
        "threshold_applied": False,
        "reasons_present": False,
    }
    if decision is not None and threshold is not None:
        checks["threshold_applied"] = math.isclose(decision.threshold_used, float(threshold)) and (
            decision.approved == (decision.p_repay >= float(threshold))
        )
        checks["reasons_present"] = len(decision.reasons) > 0

    blocked: str | None = None
    if not checks["threshold_present"]:
        blocked = f"No calibrated threshold for group '{group}'"
    elif not checks["no_sensitive_inputs"]:
        blocked = "Sensitive attribute found in model inputs"
    elif not checks["threshold_applied"]:
        blocked = "Decision does not match the calibrated group threshold"
    elif not checks["reasons_present"]:
        blocked = "Decision has no SHAP reasons"

    return FairnessCheck(
        ok=blocked is None,
        group=group,
        threshold_used=float(threshold) if threshold is not None else None,
        checks=checks,
        blocked_reason=blocked,
    )


def persist_decision(
    db: Session,
    decision: Decision,
    features: dict[str, Any],
    user: User | None,
    amount_bdt: float,
    fairness: FairnessCheck,
    status: str | None = None,
    event: str = "credit_scored",
    extra_audit: dict[str, Any] | None = None,
) -> DecisionRecord:
    """Store application, decision and a complete audit entry. Caller commits.

    An explicit status other than "approved" (needs_review, blocked) is never stored as approved.
    """
    approved = decision.approved and fairness.ok and status in (None, "approved")
    app_id: str | None = None
    if user is not None:
        final_status = status or ("approved" if approved else "rejected")
        application = Application(user_id=user.id, amount_bdt=amount_bdt, status=final_status)
        db.add(application)
        db.flush()
        app_id = application.id

    reasons = [r.model_dump() for r in decision.reasons]
    record = DecisionRecord(
        application_id=app_id,
        user_id=user.id if user else None,
        p_repay=decision.p_repay,
        score=decision.score,
        band=decision.band,
        approved=approved,
        reasons=reasons,
        tips=decision.tips,
        group=decision.group,
        threshold_used=decision.threshold_used,
        model_version=decision.model_version,
        fairness_ok=fairness.ok,
    )
    db.add(record)
    db.flush()
    record_decision(decision.band, approved)

    details: dict[str, Any] = {
        "p_repay": round(decision.p_repay, 6),
        "score": decision.score,
        "band": decision.band,
        "approved": record.approved,
        "group": decision.group,
        "threshold": decision.threshold_used,
        "model_version": decision.model_version,
        "features": {k: v for k, v in features.items() if k not in SENSITIVE_ATTRIBUTES},
        "reasons": reasons,
        "fairness": fairness.model_dump(),
    }
    if extra_audit:
        details.update(extra_audit)
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            event=event,
            entity_type="decision",
            entity_id=record.id,
            details=details,
        )
    )
    return record
