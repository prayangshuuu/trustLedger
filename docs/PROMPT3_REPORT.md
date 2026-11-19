# Prompt 3 report — Scoring core package

**Date:** 2026-11-20
**Status:** done

## Summary
Built the pure scoring library in `backend/app/core/` that transforms applicant alternative financial features into an explainable, demographic parity-calibrated credit decision. Implemented cached model and metadata loading, Pydantic feature validation with training-order DataFrame transformation, probability prediction and 300–900 score scaling, SHAP TreeExplainer local attribution with bilingual Bangla/English reasons and actionable tips, group-calibrated decision gating and demographic fairness auditing, and the unified `score_applicant` pipeline. All modules strictly enforce zero network or database dependencies, achieving 100% statement coverage across `app/core` and passing strict static type checking.

## Changes
| File | Change |
|---|---|
| `backend/app/core/model.py` | Cached loading (`@lru_cache`) of production XGBoost model (`trustledger_xgb.json`) and metadata (`trustledger_meta.json`) from `MODEL_DIR`, deterministic model version hashing (SHA-256 hex string), directory resolution order, and cache invalidation. |
| `backend/app/core/features.py` | `FeatureVector` Pydantic model with validated bounds for 10 alternative features, NaN/None sanitization, all-missing input rejection (`AllFeaturesMissingError`), and `to_dataframe()` transformation matching metadata column ordering. |
| `backend/app/core/score.py` | `predict(features)` repayment probability calculation, `to_score(p)` log-odds scaling formula (`600 + (50/ln(2)) * ln(odds/4)`) bounded to [300, 900] for scalars and ndarrays, and `band(score)` risk tier mapping (Excellent, Good, Fair, Building). |
| `backend/app/core/explain.py` | SHAP `TreeExplainer` local attribution engine, filtering missing features and attributions with $|impact| < 0.02$, extracting top-2 positive and top-2 negative drivers, and generating bilingual Bangla text, actionable tips, and English labels via `Reason` and `Explanation` models. |
| `backend/app/core/fairness.py` | Dynamic calibrated threshold retrieval (`get_group_threshold`), group approval decision (`decide`), and multi-group demographic disparity audit (`audit`) computing approval rates, TPR, FPR, and verifying disparity gates ($\le 0.05$). |
| `backend/app/core/decision.py` | Unified `score_applicant(features, group) -> Decision` orchestrator combining prediction, score scaling, risk banding, SHAP explanations, fairness decision, and model audit metadata. |
| `backend/app/core/__init__.py` | Public package API exports for core classes, functions, and exceptions. |
| `backend/tests/test_model.py` | Unit tests for model directory resolution, model/metadata loading, LRU caching, version hashing, and error conditions. |
| `backend/tests/test_features.py` | Unit tests for feature names, vector validation, boundary constraints, NaN sanitization, ordering, and all-missing rejection. |
| `backend/tests/test_score.py` | Unit tests for probability prediction, exact log-odds score formula, monotonicity, array vectorized operations, and risk banding. |
| `backend/tests/test_explain.py` | Unit tests for SHAP feature attribution on Shathi profile, impact filtering, missing feature omission, Bangla translation, and tips. |
| `backend/tests/test_fairness.py` | Unit tests for metadata threshold extraction, dynamic thresholds, demographic audit metrics, and fairness disparity limits. |
| `backend/tests/test_decision.py` | Integration tests for Shathi persona, zero-history bhorsha-only applicant, missing input rejection, unknown group rejection, and zero-network assertions. |
| `backend/tests/test_golden.py` | Golden benchmark test reproducing the notebook's Shathi metrics within $\pm 0.01$ tolerance ($p_{repay} = 0.934$, score = 691, band = Good, approved = True). |
| `docs/PROMPT.md` | Marked Prompt 3 complete in checklist and updated status table. |

## How to run / verify
Commands to verify the scoring core package, type safety, and test suite:

```bash
# 1. Run Astral Ruff linter and formatting checks
uv run ruff check .
uv run ruff format --check .

# 2. Run static type checking with strict flags on app.core
uv run mypy backend/app
uv run mypy --strict backend/app/core

# 3. Run test suite with full branch/statement coverage
uv run pytest --cov=app.core --cov-report=term-missing

# 4. Verify golden benchmark test specifically
uv run pytest backend/tests/test_golden.py -v
```

## Tests and checks
- **ruff check:** pass (`uv run ruff check .` -> `All checks passed!`)
- **ruff format:** pass (`uv run ruff format --check .` -> `69 files already formatted`)
- **mypy:** pass (`uv run mypy backend/app` -> `Success: no issues found in 19 source files`; `uv run mypy --strict backend/app/core` -> `Success: no issues found in 7 source files`)
- **pytest:** pass (`uv run pytest` -> 78 passed, 0 failed, 95% total application coverage, 100% statement coverage across all `app/core` modules)
- **golden benchmark test:** pass (`backend/tests/test_golden.py::test_shathi_golden_benchmark` -> reproduces $p_{repay} = 0.934$, score = 691 within $\pm 0.01$ tolerance)
- **network/DB isolation check:** pass (socket connection and address lookup monkeypatched to raise errors; verified zero network or DB I/O in `app/core`)

## Acceptance criteria
- [x] `score_applicant` returns a complete `Decision` for Shathi and for a zero-history user — verified in `backend/tests/test_decision.py` and `test_golden.py`.
- [x] Coverage of `app/core` ≥ 90% — verified at 100% coverage (406/406 statements in `app/core`).
- [x] mypy strict passes on `app/core` — verified (`uv run mypy --strict backend/app/core` succeeded with 0 issues).
- [x] No network or DB access in `core/` — verified with pure functional design and explicit socket-blocking tests.

## Decisions and deviations
- **SHAP Explanation Array Dimension Handling:** In `core/explain.py`, SHAP's `TreeExplainer.shap_values()` output structure varies across XGBoost and shap package versions (returning either a list of ndarrays, a 2D ndarray, or a 3D ndarray). The implementation handles 2D, 3D, and multi-class list outputs robustly to ensure consistent feature attribution vectors without raising index errors.
- **Dynamic Threshold Reading:** No decision thresholds or score scale factors are hardcoded in Python code; all values are retrieved dynamically from `trustledger_meta.json` via `load_meta()`, allowing seamless model updates without code changes.

## Known issues / follow-ups
- Prompt 4 will build the persistence layer (PostgreSQL 16 + pgvector schemas, Alembic migrations, consent logging, and audit record storage) to persist `Decision` records generated by `score_applicant()`.
