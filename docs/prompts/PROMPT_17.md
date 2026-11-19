# Prompt 17 — Evaluation suite and quality gates

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu + Fariha
**Depends on:** Prompt 6, Prompt 8, Prompt 9, Prompt 10, Prompt 11
**Report:** `docs/PROMPT17_REPORT.md`

## Goal
Prove quality with numbers and stop regressions automatically.

## Tasks
- `evals/run_all.py` producing `training_files/eval_report.json` and a markdown summary:
  - model: AUC, KS, Brier, calibration on held-out synthetic data (reuse notebook logic)
  - fairness gate: approval gap and equalized-odds gap ≤ 0.05
  - SMS parser F1, OCR field F1
  - RAG: RAGAS faithfulness, context precision
  - explanations: LLM-as-judge faithfulness to SHAP (live mode) + rule check that every mentioned feature is in SHAP output (always)
  - Bhorsha: score stability and persona ordering
  - prompt regression: fixed inputs for each agent prompt, compare outputs to golden JSON
- CI runs the offline subset on every push and fails on gate violations.

## Acceptance criteria
- `uv run python evals/run_all.py` completes offline
- CI fails if the fairness gate is broken (prove with a deliberately biased threshold in a test)
- Numbers summarised in the report

## Out of scope
New features.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT17_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 17 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
