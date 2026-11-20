"""LoanWorkflow: apply -> score -> approve/review -> disburse -> schedule -> reminders ->
repayments -> +20% limit after 3 on-time payments."""

import functools
from dataclasses import asdict
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.temporal.shared import (
        ApplyResult,
        LoanInput,
        LoanState,
        ReminderArgs,
        RepaymentArgs,
    )

RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=5,
)
ACTIVITY_TIMEOUT = timedelta(seconds=60)
ON_TIME_FOR_UPGRADE = 3


@workflow.defn
class LoanWorkflow:
    def __init__(self) -> None:
        self.state = LoanState()
        self._repayments: list[bool] = []  # signal payloads: on_time flags, in order
        self._review: bool | None = None

    @workflow.signal
    def repay(self) -> None:
        """Borrower paid the current installment (wallet webhook or app)."""
        self._repayments.append(True)

    @workflow.signal
    def review(self, approve: bool) -> None:
        """Loan officer decision for a needs_review application."""
        self._review = approve

    @workflow.query
    def status(self) -> dict[str, Any]:
        return asdict(self.state)

    def _paid(self, n: int) -> bool:
        return len(self._repayments) > n

    def _log(self, event: str) -> None:
        self.state.events.append(event)

    async def _act(self, name: str, *args: Any) -> Any:
        return await workflow.execute_activity(
            name, args=list(args), start_to_close_timeout=ACTIVITY_TIMEOUT, retry_policy=RETRY
        )

    @workflow.run
    async def run(self, inp: LoanInput) -> dict[str, Any]:
        result = await workflow.execute_activity(
            "apply_for_loan",
            args=[inp.user_id, inp.amount_bdt],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            retry_policy=RETRY,
            result_type=ApplyResult,
        )
        self.state.trace_id = result.trace_id
        self.state.application_id = result.application_id
        self.state.decision_id = result.decision_id
        self.state.score = result.score
        self._log(f"scored:{result.status}")

        if result.status == "needs_review":
            self.state.status = "in_review"
            try:
                await workflow.wait_condition(
                    lambda: self._review is not None,
                    timeout=timedelta(days=inp.review_timeout_days),
                )
            except TimeoutError:
                self._review = False
            self._log(f"reviewed:{self._review}")
            if not self._review:
                self.state.status = "rejected"
                return self.status()
        elif result.status != "approved":
            self.state.status = result.status
            return self.status()

        if result.application_id is None:
            self.state.status = "error_no_application"
            return self.status()

        await self._act("disburse_loan", result.application_id)
        self.state.status = "disbursed"
        self.state.credit_limit_bdt = inp.amount_bdt
        self._log("disbursed")

        installment = round(inp.amount_bdt / inp.installments, 2)
        start = workflow.now()
        for i in range(inp.installments):
            due = start + timedelta(days=inp.interval_days * (i + 1))
            remind_at = due - timedelta(days=inp.reminder_days_before)
            await workflow.sleep(max(timedelta(0), remind_at - workflow.now()))
            await self._act(
                "send_reminder",
                ReminderArgs(inp.user_id, i + 1, installment, due.date().isoformat()),
            )
            self.state.reminders_sent += 1

            on_time = True
            try:
                await workflow.wait_condition(
                    functools.partial(self._paid, i),
                    timeout=max(timedelta(seconds=1), due - workflow.now()),
                )
            except TimeoutError:
                on_time = False
                self._log(f"installment_{i + 1}_late")
                try:
                    await workflow.wait_condition(
                        functools.partial(self._paid, i),
                        timeout=timedelta(days=inp.grace_days),
                    )
                except TimeoutError:
                    self.state.status = "defaulted"
                    self._log("defaulted")
                    return self.status()

            await self._act(
                "record_repayment",
                RepaymentArgs(
                    result.application_id,
                    installment,
                    on_time,
                    f"{workflow.info().workflow_id}-{i + 1}",
                ),
            )
            self.state.paid += 1
            self.state.on_time += on_time
            self._log(f"installment_{i + 1}_{'on_time' if on_time else 'late'}")

        if self.state.on_time >= ON_TIME_FOR_UPGRADE and self.state.on_time == self.state.paid:
            new_limit = await self._act("upgrade_limit", result.application_id)
            self.state.credit_limit_bdt = float(new_limit)
            self._log("limit_upgraded")
        self.state.status = "repaid"
        return self.status()
