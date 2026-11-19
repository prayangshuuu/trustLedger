# Prompt 20 — Public /docs site, README and submission pack

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Fariha + Dipanwita
**Depends on:** Prompt 17, Prompt 19
**Report:** `docs/PROMPT20_REPORT.md`

## Goal
Give judges and the public one place to understand, verify and try TrustLedger.

## Tasks
- `docs/site/` (static site, e.g. MkDocs Material or a simple Vite page) deployed at `/docs`: problem, solution, Shathi's story, architecture diagram, agent pipeline, model + fairness + inclusion results (figures from `training_files/`), privacy, API reference (from `docs/api.md`), MCP usage, team, links.
- Update `README.md`: fill demo, docs, video and deck links; add eval numbers; keep it short.
- `docs/architecture.md` with a Mermaid diagram.
- `docs/DEMO_SCRIPT.md`: the 3-minute live demo click path (Shathi → zero-history user → dashboard), backup plan if network fails (local docker + recorded video).
- `docs/JUDGE_QA.md`: 15 likely judge questions with short answers (privacy, bias, business model, data access, why DeepSeek, scaling, regulation).

## Acceptance criteria
- `/docs` is public and every figure loads
- README has no placeholder links left
- Demo script rehearsed once and timed (time recorded in the report)

## Out of scope
New features.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT20_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 20 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
