"""Loan servicing schemas (repayments and credit-limit ladder)."""

from datetime import datetime

from pydantic import BaseModel, Field


class RepaymentRequest(BaseModel):
    amount_bdt: float = Field(..., gt=0, le=500000)
    on_time: bool = True
    idempotency_key: str | None = Field(default=None, max_length=64)


class RepaymentItem(BaseModel):
    id: str
    amount_bdt: float
    on_time: bool
    paid_at: datetime


class LimitUpgradeRequest(BaseModel):
    reason: str = Field(default="3 on-time repayments", max_length=120)
    factor: float = Field(default=1.2, gt=1.0, le=2.0)


class LoanResponse(BaseModel):
    application_id: str
    user_id: str
    status: str
    amount_bdt: float
    credit_limit_bdt: float
    on_time_repayments: int
    late_repayments: int
    repayments: list[RepaymentItem]
