# Prompt 03 — Scoring core package

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu
**Depends on:** Prompt 1, Prompt 2
**Report:** `docs/PROMPT3_REPORT.md`

## Goal
Build the pure scoring library in `backend/app/core/` that turns a feature dict into a full, explained, fairness-checked decision. This is the heart of the product.

## Tasks
- `core/model.py`: load XGBoost model and meta from `MODEL_DIR` once (cached). Expose model version (hash of model file).
- `core/features.py`: `FeatureVector` Pydantic model with the 10 features (all optional floats, validated ranges). Function to convert to a 1-row DataFrame in the exact training order.
- `core/score.py`: `predict(features) -> p_repay`, `to_score(p)`, `band(score)` per PLAN_CONTEXT.md §2.
- `core/explain.py`: SHAP TreeExplainer, top-2 good / top-2 bad, skip missing and |impact| < 0.02, Bangla text + tips from meta, English label too.
- `core/fairness.py`: `decide(p_repay, group)` using `group_thresholds`; `audit(decisions)` returning approval rate, TPR, FPR per group and the gaps.
- `core/decision.py`: `score_applicant(features, group) -> Decision` combining all the above. `Decision` includes p_repay, score, band, approved, reasons, tips, threshold_used, model_version.
- Tests: Shathi case (approved, score in Good band, "বিল সময়মতো পরিশোধ" among good reasons), a zero-history user with only `bhorsha_score`, all-missing input rejected with a clear error, score monotonic in p, thresholds read from meta (not hard-coded).
- A golden test that reproduces the notebook's Shathi numbers within ±0.01.

## Acceptance criteria
- `score_applicant` returns a complete `Decision` for Shathi and for a zero-history user
- Coverage of `app/core` ≥ 90%
- mypy strict passes on `app/core`
- No network or DB access in `core/`

## Out of scope
HTTP API, database.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT3_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 3 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
