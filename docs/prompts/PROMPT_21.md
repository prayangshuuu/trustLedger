# Prompt 21 — Final QA and submission readiness

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Whole team
**Depends on:** Prompt 1, Prompt 2, Prompt 3, Prompt 4, Prompt 5, Prompt 6, Prompt 7, Prompt 8, Prompt 9, Prompt 10, Prompt 11, Prompt 12, Prompt 13, Prompt 14, Prompt 15, Prompt 16, Prompt 17, Prompt 18, Prompt 19, Prompt 20
**Report:** `docs/PROMPT21_REPORT.md`

## Goal
A full, honest check that everything promised in the submission forms actually exists and works.

## Tasks
- Re-read PLAN_CONTEXT.md §10 (definition of done) and check every item on the deployed system.
- Cross-check the AI usage and data lifecycle form answers against the code: every tool/framework claimed (DeepSeek, DeepSeek-OCR LoRA, LangGraph, MCP server, Flower, Temporal, Airflow, pgvector, BGE-M3, Presidio, Fairlearn, Recharts, Chart.js, D3, Grafana, Heroku) must have a file path that proves it. Produce a table: claim → evidence path → status. Anything missing is either built minimally now or flagged for the team to correct in the form.
- Run `evals/run_all.py`, `infra/smoke.sh`, full test suite; record results.
- Fresh-clone test: follow README from zero on a clean machine/container.
- Tag release `v1.0.0`, freeze `main`.

## Acceptance criteria
- Claim → evidence table complete with no unexplained gaps
- All tests, evals and smoke tests green
- Release tagged

## Out of scope
Anything new — only fixes.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT21_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 21 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description