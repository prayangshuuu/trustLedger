# Prompt 01 — Repository audit and baseline

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu
**Depends on:** nothing
**Report:** `docs/PROMPT1_REPORT.md`

## Goal
Understand the current repository exactly as it is, make it reproducible, and record a baseline before any new code is written.

## Tasks
- Inventory the repo: list every top-level file/folder, sizes of `datasets/`, what is tracked by Git LFS (`.gitattributes`), and what `.gitignore` excludes.
- Verify `models/trustledger_meta.json` matches the model contract in PLAN_CONTEXT.md §2 (feature names and order, `threshold`, `group_thresholds` keys `F_rural F_urban M_rural M_urban`, `score_scale`, `reasons`, `tips`). Report any mismatch.
- Load `models/trustledger_xgb.json` with XGBoost and score the Moon example from the notebook. Record `p_repay` and score.
- Read `training_files/metrics.json` and copy the key numbers into the report (AUC, KS, fairness gaps before/after, inclusion numbers, federated AUC, Home Credit comparison, LendingClub AUC).
- Make `uv sync` work from a clean clone. Add any missing training dependencies to `pyproject.toml`.
- Add `.env.example` (empty values) with the variables from PLAN_CONTEXT.md §7.
- Add `ruff` and `pytest` as dev dependencies with a minimal config in `pyproject.toml`.
- Create `docs/` and `docs/prompts/` if missing. Do not create backend code yet.

## Acceptance criteria
- `uv sync` works from a fresh clone
- Meta contract verified (or mismatches listed)
- Moon scored with the saved model, numbers in the report
- Baseline metrics table in the report
- `.env.example` exists and `.env` is git-ignored

## Out of scope
Backend, frontend, retraining the model.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT1_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 1 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
