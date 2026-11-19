# Prompt 05 — FastAPI backend v1

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Daniel
**Depends on:** Prompt 3, Prompt 4
**Report:** `docs/PROMPT5_REPORT.md`

## Goal
Expose the scoring core and persistence through a clean, documented REST API.

## Tasks
- App factory in `main.py`, settings in `config.py`, CORS for the dashboard and app.
- Auth: API keys for lenders/partners (`X-API-Key`), simple bearer token per borrower session for the app.
- Endpoints:
  - `GET /health`, `GET /version` (model version, git sha)
  - `POST /consent`, `DELETE /consent/{source}`, `DELETE /me`
  - `POST /score` — body: features (or user_id to use latest snapshot) → full `Decision`; persists decision + audit log
  - `GET /explain/{decision_id}`
  - `GET /fairness/report` — audit over stored decisions (per group rates + gaps)
  - `GET /inclusion-lift` — bank-rule approvals vs TrustLedger approvals over stored decisions (same rule as the notebook)
- Consistent error format, request IDs, structured JSON logs.
- OpenAPI tags and examples (Shathi as the example payload). Write `docs/api.md` generated from OpenAPI plus short notes.
- Tests with httpx for every endpoint, including consent missing → 403 and delete-me.

## Acceptance criteria
- `make api` serves `/docs` (Swagger) with Shathi examples
- `POST /score` for Shathi returns approved + Bangla reasons, and the decision is stored
- Fairness and inclusion endpoints return numbers from stored data
- All endpoint tests pass offline

## Out of scope
LLM features, agents.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT5_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 5 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
