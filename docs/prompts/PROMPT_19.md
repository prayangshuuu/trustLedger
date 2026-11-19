# Prompt 19 — Deployment — Heroku and demo environment

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Daniel
**Depends on:** Prompt 5, Prompt 11, Prompt 12, Prompt 15, Prompt 16, Prompt 18
**Report:** `docs/PROMPT19_REPORT.md`

## Goal
Put TrustLedger online with a stable demo for judges.

## Tasks
- Heroku apps: `trustledger-api` (FastAPI + Uvicorn, Procfile, release phase runs Alembic), `trustledger-mcp` (MCP HTTP server). Heroku Postgres (pgvector) + Heroku Redis. Config vars documented.
- Model files shipped with the slug or downloaded at release from a pinned location.
- Dashboard on Vercel (or Heroku static) pointing to the API.
- Flutter app: release APK built and attached to a GitHub release.
- Seed the 3 personas on deploy; `DEMO_MODE=true`, `LLM_MODE=live` if keys exist, else mock.
- Smoke test script `infra/smoke.sh` that runs Shathi's flow against the deployed URL.
- Staging + production apps; a short `docs/deploy.md`.

## Acceptance criteria
- Public URLs for API, MCP and dashboard work
- `infra/smoke.sh` passes against production
- APK downloadable

## Out of scope
Docs site.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT19_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 19 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
