# Prompt 4 report — Database, consent and persistence

**Date:** 2026-11-20
**Status:** done

## Summary
Created the data persistence layer for TrustLedger adhering strictly to the privacy and fairness architecture. Implemented SQLAlchemy 2 models (`users`, `consents`, `feature_snapshots`, `applications`, `decisions`, `repayments`, `audit_log`), Alembic migrations with the `pgvector` extension enabled for future RAG embedding lookups, consent validation and gating helpers in `app/privacy/consent.py`, GDPR-compliant cascading data deletion in `app/privacy/deletion.py`, and an idempotent seed script in `backend/scripts/seed_demo.py` creating the three demo personas (Shathi, Student, Homemaker). Proved through automated tests that no table or column stores raw SMS data and that deleting a user completely cascades across all related child tables.

## Changes
| File | Change |
|---|---|
| `pyproject.toml`, `uv.lock` | Added `sqlalchemy>=2.0.0`, `alembic>=1.13.0`, `psycopg[binary]>=3.1.0`, and `pgvector>=0.2.5` to project dependencies. |
| `backend/app/config.py` | Configured default `DATABASE_URL` with psycopg driver (`postgresql+psycopg://...`). |
| `backend/app/db/base.py` | Defined SQLAlchemy 2 `Base` declarative base class. |
| `backend/app/db/models.py` | Created domain entity models: `User`, `Consent`, `FeatureSnapshot`, `Application`, `DecisionRecord`, `Repayment`, and `AuditLog` with foreign key CASCADE deletion and portable JSON/JSONB types. |
| `backend/app/db/session.py` | Engine initialization with SQLite foreign-key pragma listener, database URL normalization, session factory, and table creation utilities. |
| `backend/app/db/__init__.py` | Exported database models and session helpers. |
| `backend/alembic/env.py`, `alembic.ini`, `backend/alembic.ini` | Configured Alembic migration environment with dynamic URL resolution and metadata binding. |
| `backend/alembic/versions/0001_initial_schema.py` | Initial schema migration enabling `vector` extension on PostgreSQL and defining all 7 core tables. |
| `backend/app/privacy/consent.py` | Consent operations (`grant_consent`, `revoke_consent`, `has_consent`, `get_active_consents`, `require_consent`) with `ConsentMissingError` gating. |
| `backend/app/privacy/deletion.py` | Cascading user data removal function `delete_user_data` for user deletion / "Right to be Forgotten". |
| `backend/app/privacy/__init__.py` | Exported privacy and consent management interfaces. |
| `backend/scripts/seed_demo.py` | Idempotent demo persona seeding script populating Shathi, Student, and Homemaker personas with synthetic data and core scoring decisions. |
| `backend/tests/test_db_models.py` | Database model relationships, driver URL normalization, and programmatic Alembic migration upgrade/downgrade test. |
| `backend/tests/test_consent.py` | Consent granting, revocation, re-granting, validation, and gating assertion tests. |
| `backend/tests/test_deletion.py` | Verification proving user deletion cascades and completely purges all related rows across all 6 child tables. |
| `backend/tests/test_seed.py` | Test verifying seed script creates the 3 personas with accurate features, consents, and decisions. |
| `backend/tests/test_no_raw_sms.py` | Schema reflection test asserting no table or column contains raw SMS or message text. |
| `docs/PROMPT.md` | Marked Prompt 4 complete in checklist and updated status table. |

## How to run / verify
Commands to verify migrations, database seeding, privacy logic, and tests:

```bash
# 1. Run Alembic migrations against target database
uv run alembic upgrade head

# 2. Run demo persona seed script
uv run python backend/scripts/seed_demo.py

# 3. Run linting, format check, and static type checking
uv run ruff check .
uv run ruff format --check .
uv run mypy backend/app

# 4. Run test suite covering models, consent, cascading deletion, and privacy gates
uv run pytest backend/tests/test_db_models.py backend/tests/test_consent.py backend/tests/test_deletion.py backend/tests/test_seed.py backend/tests/test_no_raw_sms.py -v
```

## Tests and checks
- **ruff check:** pass (`uv run ruff check .` -> `All checks passed!`)
- **ruff format:** pass (`uv run ruff format --check .` -> `84 files already formatted`)
- **mypy:** pass (`uv run mypy backend/app` -> `Success: no issues found in 24 source files`)
- **pytest:** pass (`uv run pytest` -> 92 passed, 0 failed, 97% total coverage)
- **Alembic migration test:** pass (`backend/tests/test_db_models.py::test_alembic_upgrade_head_and_downgrade` verified clean upgrade and downgrade)
- **Cascading deletion test:** pass (`backend/tests/test_deletion.py::test_delete_user_data_cascades_all_tables` verified zero orphaned rows remain in any table)
- **Privacy compliance (no raw SMS):** pass (`backend/tests/test_no_raw_sms.py::test_no_raw_sms_table_or_column` verified 0 forbidden communication columns/tables)

## Acceptance criteria
- [x] `alembic upgrade head` works on a clean DB — verified on both PostgreSQL 16 and SQLite test environments.
- [x] Seed script creates the 3 personas — verified Shathi (garment worker), Student (freelancer), and Homemaker (zero-history) created with active consents, features, applications, and model decisions.
- [x] Deleting a user removes every related row (test proves it) — verified by `test_delete_user_data_cascades_all_tables`.
- [x] No column stores raw SMS text — verified by `test_no_raw_sms_table_or_column`.

## Decisions and deviations
- **pgvector compilation for PostgreSQL 16:** Installed and compiled pgvector 0.8.0 locally for `postgresql@16`, allowing `CREATE EXTENSION IF NOT EXISTS vector;` to succeed natively on local development databases.
- **SQLite Foreign Key Pragmas:** Added automatic event listener `PRAGMA foreign_keys=ON;` in `create_app_engine()` for SQLite URLs to guarantee relational parity between development SQLite in-memory tests and production PostgreSQL.

## Known issues / follow-ups
- Ready for Prompt 05 to build the FastAPI REST API v1 exposing health, consent, score, decision explainability, and fairness/inclusion audit endpoints.
