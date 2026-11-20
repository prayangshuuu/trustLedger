"""Loan servicing: repayments and the limit ladder (+20% after 3 on-time payments)."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import ApiKeyAuth, DbSession
from app.db.models import Application, AuditLog, Repayment
from app.schemas.loans import LimitUpgradeRequest, LoanResponse, RepaymentItem, RepaymentRequest

router = APIRouter(prefix="/loans", tags=["Loans"])


def _limit(db: DbSession, app: Application) -> float:
    last = db.scalars(
        select(AuditLog)
        .where(AuditLog.entity_id == app.id, AuditLog.event == "limit_upgraded")
        .order_by(AuditLog.created_at.desc())
    ).first()
    return float(last.details["new_limit_bdt"]) if last else float(app.amount_bdt)


def _loan(db: DbSession, app: Application) -> LoanResponse:
    reps = list(
        db.scalars(
            select(Repayment).where(Repayment.application_id == app.id).order_by(Repayment.paid_at)
        )
    )
    return LoanResponse(
        application_id=app.id,
        user_id=app.user_id,
        status=app.status,
        amount_bdt=app.amount_bdt,
        credit_limit_bdt=round(_limit(db, app), 2),
        on_time_repayments=sum(r.on_time for r in reps),
        late_repayments=sum(not r.on_time for r in reps),
        repayments=[
            RepaymentItem(id=r.id, amount_bdt=r.amount_bdt, on_time=r.on_time, paid_at=r.paid_at)
            for r in reps
        ],
    )


def _get_app(db: DbSession, application_id: str) -> Application:
    app = db.get(Application, application_id)
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Loan '{application_id}' not found")
    return app


@router.get("/{application_id}", response_model=LoanResponse, summary="Loan status and limit")
def get_loan(application_id: str, db: DbSession, _api_key: ApiKeyAuth = None) -> LoanResponse:
    return _loan(db, _get_app(db, application_id))


@router.post(
    "/{application_id}/repayments", response_model=LoanResponse, summary="Record a repayment"
)
def add_repayment(
    application_id: str, payload: RepaymentRequest, db: DbSession, _api_key: ApiKeyAuth = None
) -> LoanResponse:
    """Idempotent when idempotency_key is given (Temporal activities may retry)."""
    app = _get_app(db, application_id)
    if app.status not in ("approved", "disbursed", "repaid"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Loan is '{app.status}', not repayable")
    if payload.idempotency_key:
        seen = db.scalars(
            select(AuditLog).where(
                AuditLog.event == "repayment_recorded",
                AuditLog.entity_id == f"{application_id}:{payload.idempotency_key}"[:64],
            )
        ).first()
        if seen:
            return _loan(db, app)
    rep = Repayment(application_id=app.id, amount_bdt=payload.amount_bdt, on_time=payload.on_time)
    db.add(rep)
    db.add(
        AuditLog(
            user_id=app.user_id,
            event="repayment_recorded",
            entity_type="loan",
            entity_id=f"{application_id}:{payload.idempotency_key or rep.id}"[:64],
            details={"amount_bdt": payload.amount_bdt, "on_time": payload.on_time},
        )
    )
    db.commit()
    return _loan(db, app)


@router.post(
    "/{application_id}/limit-upgrade", response_model=LoanResponse, summary="Raise credit limit"
)
def upgrade_limit(
    application_id: str, payload: LimitUpgradeRequest, db: DbSession, _api_key: ApiKeyAuth = None
) -> LoanResponse:
    """Raise the limit by `factor` (default +20%). Requires >= 3 on-time and no late repayments."""
    app = _get_app(db, application_id)
    loan = _loan(db, app)
    if loan.on_time_repayments < 3 or loan.late_repayments > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Limit upgrade needs 3 on-time repayments and none late"
        )
    db.add(
        AuditLog(
            user_id=app.user_id,
            event="limit_upgraded",
            entity_type="loan",
            entity_id=app.id,
            details={
                "old_limit_bdt": loan.credit_limit_bdt,
                "new_limit_bdt": round(loan.credit_limit_bdt * payload.factor, 2),
                "reason": payload.reason,
            },
        )
    )
    db.commit()
    return _loan(db, app)


@router.post("/{application_id}/disburse", response_model=LoanResponse, summary="Mark disbursed")
def disburse(application_id: str, db: DbSession, _api_key: ApiKeyAuth = None) -> LoanResponse:
    """Mock disbursement (no money moves). Idempotent: an already disbursed loan is returned."""
    app = _get_app(db, application_id)
    if app.status == "approved":
        app.status = "disbursed"
        db.add(
            AuditLog(
                user_id=app.user_id,
                event="loan_disbursed",
                entity_type="loan",
                entity_id=app.id,
                details={"amount_bdt": app.amount_bdt, "channel": "mock_wallet"},
            )
        )
        db.commit()
    elif app.status != "disbursed":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Loan is '{app.status}', cannot disburse")
    return _loan(db, app)
