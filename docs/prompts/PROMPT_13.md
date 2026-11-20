# Prompt 13 — Workflows — Temporal and Airflow

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Daniel
**Depends on:** Prompt 5, Prompt 11
**Report:** `docs/PROMPT13_REPORT.md`

## Goal
Make the loan lifecycle durable and automate scheduled audits.

## Tasks
- `workflows/temporal/`: `LoanWorkflow` — apply → score (calls `/apply`) → approve/review → disburse (mock) → repayment schedule → reminders (timers, mock SMS/WhatsApp sender) → on-time repayment → limit upgrade (+20% after 3 on-time payments). Activities idempotent, retries configured.
- Worker + a CLI to start a workflow for a persona.
- `workflows/airflow/dags/`: `weekly_fairness_audit` (calls `/fairness/report`, fails loudly if gaps > 0.05), `nightly_drift_check` (PSI on feature distributions vs training ranges), `federated_round` (triggers Prompt 14's aggregation — stub until then).
- Docker compose services for the Temporal worker; document how to run Airflow locally (standalone).
- Tests: Temporal workflow test environment (time-skipping) covering approve → 3 repayments → limit upgrade.

## Acceptance criteria
- Moon's loan runs through the full lifecycle in the Temporal test env
- Fairness DAG fails when given biased decisions (test)

## Out of scope
UI.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT13_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 13 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
