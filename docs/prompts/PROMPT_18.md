# Prompt 18 — Security, privacy hardening and observability

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Daniel
**Depends on:** Prompt 5, Prompt 11, Prompt 12
**Report:** `docs/PROMPT18_REPORT.md`

## Goal
Make the system safe to demo publicly and easy to debug.

## Tasks
- Rate limiting per API key, input size limits, file-type checks on uploads, CORS locked to known origins.
- Secrets review: nothing in git (`git log -p | grep -i key` check), `.env.example` complete.
- Verify every privacy rule in PLAN_CONTEXT.md §6 with a test or a written check; produce `docs/privacy.md` (what we collect, why, retention, deletion, consent).
- Prometheus metrics endpoint (latency, errors, decisions by band, LLM calls/tokens) and a Grafana dashboard JSON in `infra/grafana/`.
- Structured logs never include PII (test).

## Acceptance criteria
- `docs/privacy.md` complete
- Grafana dashboard loads with live metrics locally
- Security checklist in the report all ticked or explained

## Out of scope
Deployment.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT18_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 18 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
