# Prompt 13 report — Workflows: Temporal and Airflow

**Date:** 2026-11-20
**Status:** done (Airflow verified through task tests; a full Airflow install is documented, not bundled)

## Summary
`LoanWorkflow` (Temporal) makes the loan lifecycle durable. It runs apply via `/apply`, then
auto-approval or human review (signal), mock disbursement, a 3-installment schedule with Bangla reminders
2 days before each due date (mock SMS/WhatsApp sender), and repayment signals with on-time/late/default handling.
After 3 on-time payments the credit limit rises 20%. Activities call new loan-servicing endpoints, retry with backoff and are idempotent.
Four Airflow DAGs cover the weekly fairness audit (fails loudly above 0.05), the nightly PSI drift check, a federated round and the 30-day document purge.

## Changes
| File | Change |
|---|---|
| `workflows/temporal/workflow.py`, `activities.py`, `shared.py` | Workflow, retry policy, signals `repay`/`review`, query `status`; idempotent activities |
| `workflows/temporal/worker.py`, `cli.py` | Worker (thread-pool activities) and CLI `start/repay/review/status` by persona |
| `backend/app/api/routers/loans.py`, `schemas/loans.py` | `GET /loans/{id}`, `POST /loans/{id}/disburse`, `/repayments` (idempotency key), `/limit-upgrade` (needs 3 on-time, 0 late) |
| `backend/app/api/routers/demo.py` | `GET /demo/personas`, `POST /demo/reset` (DEMO_MODE only) |
| `backend/app/demo_seed.py` | Seed logic moved into the app package so the deployed API can import it; `backend/scripts/seed_demo.py` is now the CLI |
| `backend/app/schemas/apply.py` | `application_id` in the `/apply` decision |
| `workflows/airflow/tasks.py`, `dags/*.py` | Fairness gate, PSI drift, purge, federated round; DAGs import without Airflow |
| `backend/scripts/build_feature_baseline.py`, `models/feature_baseline.json` | Decile baseline per feature from the 100k synthetic set |
| `infra/Dockerfile`, `.dockerignore`, `infra/docker-compose.yml` | Backend image; `api` and `temporal-worker` services (profile `app`) |
| `workflows/README.md` | How to run Temporal and Airflow standalone |
| `backend/tests/test_temporal_workflow.py`, `test_airflow_tasks.py` | 3 + 4 tests |

## How to run / verify
```bash
uv run pytest backend/tests/test_temporal_workflow.py backend/tests/test_airflow_tasks.py
docker compose -f infra/docker-compose.yml --profile app up --build   # API + worker + infra
uv run python -m workflows.temporal.cli start --persona shathi
```

## Tests and checks
- ruff: pass · mypy: pass for `backend/app`, `mcp_server`, `workflows` (one import of `federated.simulate` resolves in Prompt 14)
- pytest: 174 passed, 1 skipped
- Temporal time-skipping run (real API on SQLite): Shathi scored → disbursed → 3 reminders → 3 on-time repayments → limit 15,000 → **18,000 BDT**; with one late payment the limit stays 15,000
- Fairness DAG test: 90% vs 50% approvals → `FairnessGateError` (approval gap 0.40)
- PSI: stable sample < 0.1, shifted sample > 0.25 and flagged
- `docker compose --profile app config`: valid

## Acceptance criteria
- [x] Shathi's loan runs through the full lifecycle in the Temporal test env
- [x] Fairness DAG fails when given biased decisions (test)

## Decisions and deviations
- **Airflow is not a project dependency.** It pins dozens of packages that conflict with FastAPI/LangGraph. DAG logic lives in plain functions that are tested in CI, and `workflows/README.md` documents `airflow standalone` in a separate venv.
- Reminders use a `MockSender` (no SMS/WhatsApp gateway credentials). It is a single swap-in class.
- "On time" means the `repay` signal arrives before the due date. In production that signal comes from the wallet payment webhook.

## Known issues / follow-ups
- `federated_round` calls `federated.simulate.run_simulation` (Prompt 14).
