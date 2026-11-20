# Prompt 04 — Database, consent and persistence

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Daniel
**Depends on:** Prompt 2, Prompt 3
**Report:** `docs/PROMPT4_REPORT.md`

## Goal
Create the data model for users, consent, applications, decisions and audit logs, following the privacy rules.

## Tasks
- SQLAlchemy 2 models + Alembic migrations: `users` (id, phone_hash, gender, region, division, created_at), `consents` (user_id, source: sms|bills|recharge|ocr|bhorsha, granted_at, revoked_at), `feature_snapshots` (user_id, features JSON, source summary, created_at), `applications` (user_id, amount_bdt, status), `decisions` (application_id, p_repay, score, band, approved, reasons JSON, tips JSON, group, threshold_used, model_version, fairness_ok, created_at), `repayments`, `audit_log`.
- Store only derived features. No raw SMS table.
- pgvector extension enabled in a migration (used later by RAG).
- `privacy/consent.py`: helpers to grant/revoke/check consent; scoring must refuse if required consent is missing.
- `privacy/deletion.py`: delete-all-user-data function (cascades), used later by `DELETE /me`.
- Seed script `backend/scripts/seed_demo.py` creating the 3 demo personas (Moon, a student, a zero-history homemaker) with synthetic data.
- Tests with a Postgres test container or SQLite fallback for unit tests.

## Acceptance criteria
- `alembic upgrade head` works on a clean DB
- Seed script creates the 3 personas
- Deleting a user removes every related row (test proves it)
- No column stores raw SMS text

## Out of scope
API endpoints.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT4_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 4 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
