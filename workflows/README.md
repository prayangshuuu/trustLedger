# Workflows

## Temporal — loan lifecycle (`workflows/temporal/`)

`LoanWorkflow`: apply (`POST /apply`) → approve / human review (signal `review`) → disburse (mock)
→ 3 monthly installments, each with a Bangla reminder 2 days before due (mock SMS/WhatsApp sender)
→ repayment (signal `repay`; on time if before the due date, late within a 30-day grace period,
otherwise `defaulted`) → credit limit +20% after 3 on-time payments.
Activities call the API, retry with exponential backoff (5 attempts), and are idempotent
(repayments carry `idempotency_key = <workflow_id>-<n>`, disbursement is a no-op when already done).

```bash
make compose-up                                       # Temporal dev server on :7233 (UI :8233)
DEMO_MODE=true make api                               # API with seeded personas
uv run python -m workflows.temporal.worker            # worker
uv run python -m workflows.temporal.cli start --persona moon
uv run python -m workflows.temporal.cli repay loan-xxxx
uv run python -m workflows.temporal.cli status loan-xxxx
```

Or run API + worker in Docker: `docker compose -f infra/docker-compose.yml --profile app up --build`.
Tests use Temporal's time-skipping environment: `uv run pytest backend/tests/test_temporal_workflow.py`.

## Airflow — scheduled jobs (`workflows/airflow/dags/`)

| DAG | Schedule | What it does |
|---|---|---|
| `weekly_fairness_audit` | Mon 02:00 | `GET /fairness/report`; fails the run if approval or equalized-odds gap > 0.05 |
| `nightly_drift_check` | daily 01:00 | PSI of recent feature snapshots vs `models/feature_baseline.json`; fails if PSI > 0.25 |
| `federated_round` | Sun 03:00 | Runs a Flower aggregation round (Prompt 14) |
| `purge_expired_documents` | daily 00:30 | Deletes document images past their 30-day expiry |

Task logic is plain Python in `workflows/airflow/tasks.py` (tested without Airflow).
Airflow is not a project dependency (it pins many packages). Run it locally standalone:

```bash
python3.12 -m venv ~/.airflow-venv && source ~/.airflow-venv/bin/activate
pip install "apache-airflow==2.10.*" httpx sqlalchemy psycopg[binary] pydantic-settings numpy pandas
export AIRFLOW_HOME=~/airflow AIRFLOW__CORE__DAGS_FOLDER=$PWD/workflows/airflow/dags
export TRUSTLEDGER_API_URL=http://localhost:8000 DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trustledger
airflow standalone          # UI on :8080; trigger DAGs from the UI or `airflow dags test weekly_fairness_audit`
```
