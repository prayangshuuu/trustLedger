"""Loan lifecycle activities. Each calls the TrustLedger API and is safe to retry."""

import logging
import os
from typing import Any

import httpx
from temporalio import activity

from workflows.temporal.shared import ApplyResult, ReminderArgs, RepaymentArgs

logger = logging.getLogger("trustledger.temporal")

# Bangla reminder text; the sender is a mock (no real SMS/WhatsApp gateway in the demo)
REMINDER_BN = (
    "প্রিয় গ্রাহক, আপনার কিস্তি {n} ({amount:.0f} টাকা) {due} তারিখের মধ্যে পরিশোধ করুন। ধন্যবাদ, ট্রাস্টলেজার।"
)


class MockSender:
    """Records messages instead of sending them. Swap for a real SMS/WhatsApp provider."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, user_id: str, channel: str, text: str) -> None:
        self.sent.append({"user_id": user_id, "channel": channel, "text": text})
        logger.info("reminder queued channel=%s", channel)


class LoanActivities:
    def __init__(self, api: Any | None = None, sender: MockSender | None = None) -> None:
        self.api = api or httpx.Client(
            base_url=os.getenv("TRUSTLEDGER_API_URL", "http://localhost:8000"),
            headers={"X-API-Key": os.getenv("TRUSTLEDGER_API_KEY", "")},
            timeout=60.0,
        )
        self.sender = sender or MockSender()

    def _post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = self.api.post(path, json=json or {})
        if resp.status_code >= 500:
            resp.raise_for_status()  # transient: Temporal retries
        if resp.status_code >= 400:
            # Business errors are not retryable
            from temporalio.exceptions import ApplicationError

            raise ApplicationError(f"{path} -> {resp.status_code}: {resp.text}", non_retryable=True)
        data: dict[str, Any] = resp.json()
        return data

    @activity.defn(name="apply_for_loan")
    def apply_for_loan(self, user_id: str, amount_bdt: float) -> ApplyResult:
        body = self._post("/apply", {"user_id": user_id, "amount_bdt": amount_bdt})
        decision = body.get("decision") or {}
        return ApplyResult(
            status=body["status"],
            trace_id=body["trace_id"],
            application_id=decision.get("application_id"),
            decision_id=decision.get("decision_id"),
            score=decision.get("score"),
        )

    @activity.defn(name="disburse_loan")
    def disburse_loan(self, application_id: str) -> str:
        return str(self._post(f"/loans/{application_id}/disburse")["status"])

    @activity.defn(name="send_reminder")
    def send_reminder(self, args: ReminderArgs) -> bool:
        text = REMINDER_BN.format(n=args.installment, amount=args.amount_bdt, due=args.due_date)
        self.sender.send(args.user_id, args.channel, text)
        return True

    @activity.defn(name="record_repayment")
    def record_repayment(self, args: RepaymentArgs) -> int:
        body = self._post(
            f"/loans/{args.application_id}/repayments",
            {
                "amount_bdt": args.amount_bdt,
                "on_time": args.on_time,
                "idempotency_key": args.idempotency_key,
            },
        )
        return int(body["on_time_repayments"])

    @activity.defn(name="upgrade_limit")
    def upgrade_limit(self, application_id: str) -> float:
        return float(self._post(f"/loans/{application_id}/limit-upgrade")["credit_limit_bdt"])

    def all(self) -> list[Any]:
        return [
            self.apply_for_loan,
            self.disburse_loan,
            self.send_reminder,
            self.record_repayment,
            self.upgrade_limit,
        ]
