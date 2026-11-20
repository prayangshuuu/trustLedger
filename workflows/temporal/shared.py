"""Data classes shared by the loan workflow, its activities and the CLI."""

from dataclasses import dataclass, field

TASK_QUEUE = "trustledger-loans"


@dataclass
class LoanInput:
    user_id: str
    amount_bdt: float = 15000.0
    installments: int = 3
    interval_days: int = 30
    reminder_days_before: int = 2
    review_timeout_days: int = 2
    grace_days: int = 30


@dataclass
class ApplyResult:
    status: str
    trace_id: str
    application_id: str | None = None
    decision_id: str | None = None
    score: int | None = None


@dataclass
class RepaymentArgs:
    application_id: str
    amount_bdt: float
    on_time: bool
    idempotency_key: str


@dataclass
class ReminderArgs:
    user_id: str
    installment: int
    amount_bdt: float
    due_date: str
    channel: str = "sms"


@dataclass
class LoanState:
    status: str = "started"
    application_id: str | None = None
    decision_id: str | None = None
    trace_id: str | None = None
    score: int | None = None
    paid: int = 0
    on_time: int = 0
    reminders_sent: int = 0
    credit_limit_bdt: float | None = None
    events: list[str] = field(default_factory=list)
