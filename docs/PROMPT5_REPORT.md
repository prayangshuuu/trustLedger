# Prompt 5 report — FastAPI backend v1

**Date:** 2026-11-20
**Status:** done

## Summary
Exposed the TrustLedger scoring core, privacy gates, and persistence engines through a production-grade FastAPI REST API v1. Implemented modular routers for health/version introspection, consent management and Right-to-be-Forgotten deletion (`/consent`, `/me`), demographic parity-calibrated scoring and explainability (`/score`, `/explain/{decision_id}`), and live database-backed fairness and inclusion lift reporting (`/fairness/report`, `/inclusion-lift`). Configured dual-tier authentication supporting institutional API keys (`X-API-Key`) and borrower session credentials, request correlation tracing via `X-Request-ID` middleware, structured JSON request logging, uniform error envelopes, and comprehensive OpenAPI documentation documented in `docs/api.md`.

## Changes
| File | Change |
|---|---|
| `backend/app/schemas/` | Defined Pydantic models: `ErrorResponse`, `ConsentRequest`, `ConsentResponse`, `ConsentRevokeResponse`, `ScoreRequest` (with Moon example payload), `ScoreResponse`, `ExplainResponse`, `FairnessReportResponse`, `InclusionLiftResponse`. |
| `backend/app/api/deps.py` | Built FastAPI dependencies: database session injection (`get_db`), institutional API key validation (`verify_api_key`), and borrower session extraction (`get_current_user_id`). |
| `backend/app/api/routers/health.py` | Implemented `GET /health` with live database ping and `GET /version` exposing model version hash, git commit SHA, and semver. |
| `backend/app/api/routers/consent.py` | Implemented `POST /consent` (grant/reactivate), `DELETE /consent/{source}` (immediate revocation), and `DELETE /me` (cascading user data deletion). |
| `backend/app/api/routers/score.py` | Implemented `POST /score` handling raw features or stored snapshot by user_id with mandatory consent enforcement (403 if absent), persisting decisions and audit entries, and `GET /explain/{decision_id}` returning SHAP attributions. |
| `backend/app/api/routers/fairness.py` | Implemented `GET /fairness/report` (live demographic audit across stored decisions) and `GET /inclusion-lift` (quantifying approval lift over legacy bank account + salary slip rules). |
| `backend/app/main.py` | Application factory `create_app()` with CORS middleware, `RequestLoggingAndIDMiddleware` generating `X-Request-ID` and structured JSON logs, custom exception handlers (`ConsentMissingError` -> 403, `AllFeaturesMissingError` -> 400), and router registrations. |
| `docs/api.md` | Comprehensive REST API documentation including authentication headers, uniform error formats, endpoint specifications, and Moon request/response examples. |
| `backend/tests/test_api_health_version.py` | Integration tests for `GET /health`, `GET /version`, and correlation headers. |
| `backend/tests/test_api_consent.py` | Integration tests for granting, revoking, and deleting user data via `/consent` and `/me`. |
| `backend/tests/test_api_score.py` | Integration tests for Moon scoring, stored decision validation, consent missing gating (403), snapshot fallback, and explain endpoint. |
| `backend/tests/test_api_fairness_inclusion.py` | Integration tests verifying live calculation of fairness gaps and inclusion lift over seeded database records. |
| `backend/tests/test_api_auth.py` | Integration tests verifying `X-API-Key` enforcement and borrower header authentication. |
| `docs/PROMPT.md` | Marked Prompt 5 complete in checklist and updated status table. |

## How to run / verify
Commands to verify the REST API, OpenAPI docs, and test suite:

```bash
# 1. Start local API server
make api

# 2. In another terminal, verify health and version endpoints
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/version | jq

# 3. Score Moon persona via HTTP POST
curl -s -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "group": "F_urban",
    "amount_bdt": 15000.0,
    "features": {
      "monthly_inflow_bdt": 14000.0,
      "income_volatility": 0.10,
      "months_on_wallet": 30.0,
      "txn_per_month": 18.0,
      "bills_on_time": 0.97,
      "recharge_regularity": 0.90,
      "savings_ratio": 0.04,
      "sends_money_home": 1.0,
      "loan_to_income": 4.0
    }
  }' | jq

# 4. View live fairness audit and inclusion lift reports
curl -s http://localhost:8000/fairness/report | jq
curl -s http://localhost:8000/inclusion-lift | jq

# 5. Run full test suite with coverage
uv run pytest
```

## Tests and checks
- **ruff check:** pass (`uv run ruff check .` -> `All checks passed!`)
- **ruff format:** pass (`uv run ruff format --check .` -> `101 files already formatted`)
- **mypy:** pass (`uv run mypy backend/app` -> `Success: no issues found in 34 source files`)
- **pytest:** pass (`uv run pytest` -> 107 passed, 0 failed, 98% statement coverage)
- **Moon scoring test:** pass (`test_score_moon_payload_approved_and_stored` verified approved=True, score=691, band=Good, Bangla reasons present, decision record persisted)
- **Consent gating test:** pass (`test_score_consent_missing_forbidden` verified 403 Forbidden with `CONSENT_MISSING` error code)
- **Offline test execution:** pass (all 107 integration and unit tests execute completely offline using isolated SQLite in-memory databases)

## Acceptance criteria
- [x] `make api` serves `/docs` (Swagger) with Moon examples — verified OpenAPI spec generated with tags, examples, and descriptions.
- [x] `POST /score` for Moon returns approved + Bangla reasons, and the decision is stored — verified by `test_score_moon_payload_approved_and_stored`.
- [x] Fairness and inclusion endpoints return numbers from stored data — verified by `test_fairness_and_inclusion_endpoints_with_seeded_data`.
- [x] All endpoint tests pass offline — verified across all 107 test cases without network or external database dependencies.

## Decisions and deviations
- **Snapshot Resolution:** If `features` are omitted from `POST /score` but a valid `user_id` is supplied, the endpoint dynamically queries the user's latest `FeatureSnapshot` and infers demographic group `f"{user.gender}_{user.region}"` from the database.
- **Inclusion Lift Calculation:** Aligned traditional banking rule with the exact logic defined in notebook cell 4: `has_bank_account == 1 AND (has_salary_slip == 1 OR monthly_inflow_bdt >= 25000)`.

## Known issues / follow-ups
- Ready for Prompt 06 to build the LLM client gateway (`LLMClient`, `DeepSeekClient`, `MockClient`), Presidio PII redaction, and two-stage SMS transaction parser.
