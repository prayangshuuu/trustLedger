# Prompt 11 — LangGraph multi-agent pipeline

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu
**Depends on:** Prompt 3, Prompt 7, Prompt 8, Prompt 9, Prompt 10
**Report:** `docs/PROMPT11_REPORT.md`

## Goal
Orchestrate the five agents with a supervisor so one call goes from raw inputs to a fair, explained decision.

## Tasks
- `agents/graph.py`: LangGraph state with user, consents, transactions, documents, features, bhorsha, decision, audit. Nodes: `data_agent` (SMS + OCR → features), `bhorsha_router` (no history → Bhorsha required), `scoring_agent` (core), `explainer_agent` (SHAP reasons + RAG-grounded tips in Bangla, may only mention SHAP features), `fairness_agent` (thresholds, audit, can block), `supervisor`.
- Role prompts for each agent in `agents/prompts/*.md` (XML structure: role, objective, constraints, output schema). Version them.
- Borderline cases (p within ±0.03 of threshold) → `needs_review` instead of auto decision.
- Endpoint `POST /apply` that runs the graph and returns decision + trace id.
- Trace every run (node timings, model versions, prompt versions) into `audit_log`.
- Tests: Shathi end-to-end → approved; zero-history user → routed to Bhorsha; borderline → review; Fairness Agent blocks if a threshold is missing.

## Acceptance criteria
- `/apply` works end to end in mock mode for all 3 personas
- Each decision has a complete trace
- Prompt files exist and are referenced by version in traces

## Out of scope
MCP, workflows.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT11_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 11 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
