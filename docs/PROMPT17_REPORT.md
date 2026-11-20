# Prompt 17 report — Evaluation suite and quality gates

**Date:** 2026-11-20
**Status:** done (live-only metrics — LLM-as-judge, live RAGAS, live OCR — are BLOCKED until keys are set)

## Summary
`evals/run_all.py` runs model, fairness, SMS, OCR, RAG, explanation, Bhorsha and prompt-regression evaluations
offline in about 4 s. It writes `training_files/eval_report.json` and `evals/EVAL_REPORT.md`, and exits 1 if any of 8 gates fails.
CI now has three jobs (backend + evals, dashboard, Flutter). The backend job runs the evals, and a test proves a biased threshold breaks the fairness gate.

## Changes
| File | Change |
|---|---|
| `evals/run_all.py` | All suites, gates, JSON + Markdown report, `--update-golden` |
| `evals/sms/evaluate.py` | Real macro-F1 over transaction type (+ direction / amount accuracy) |
| `evals/prompts/golden/*.json` | 6 golden cases: prompt versions, explainer, Bhorsha rubric + interviewer, SMS LLM fallback, full pipeline for 4 personas |
| `evals/data/test_split.csv.gz` | Notebook test split (20,000 synthetic rows, 1 MB), so CI evaluates the same data as the notebook |
| `backend/tests/test_evals_gate.py` | Fair thresholds pass; F_rural threshold 0.85 → gate fails |
| `federated/data.py` | Generated fallback includes group and bank-rule columns |
| `.github/workflows/ci.yml` | backend (lint, mypy, pytest, evals), dashboard (tsc, vitest, build), mobile (analyze, test) |
| `evals/README.md`, `evals/EVAL_REPORT.md` | Docs and latest results |

## How to run / verify
```bash
uv run python evals/run_all.py
uv run pytest backend/tests/test_evals_gate.py
```

## Tests and checks
- ruff pass · mypy pass · pytest 183 passed, 1 skipped, coverage 93%
- `evals/run_all.py` (mock): **all 8 gates PASS**

| Area | Result |
|---|---|
| Model (20,000 test) | AUC **0.7644**, KS **0.3901**, Brier **0.168**, ECE **0.0057** (matches `metrics.json`) |
| Fairness | approval gap 0.0996 → **0.0131**, equalized-odds gap 0.0972 → **0.034** |
| Inclusion | bank rule 11.7% → TrustLedger 59.0%, newly included 50.3% |
| SMS parser (65) | type macro-F1 1.0, direction 1.0, amount 1.0 |
| OCR (10) | field F1 1.0 (mock returns labelled fields) |
| RAG (30) | precision 0.95, recall 0.972, hit rate 1.0, faithfulness 1.0 (extractive) |
| Explanations (300) | 300/300 summaries mention only SHAP features |
| Bhorsha | responsible 100.0 vs careless 21.0, stable |
| Prompt regression | 6/6 goldens match |

## Acceptance criteria
- [x] `uv run python evals/run_all.py` completes offline
- [x] CI fails if the fairness gate is broken (`test_biased_threshold_fails_the_gate`; `run_all.py` exits 1)
- [x] Numbers summarised in the report

## Decisions and deviations
- **Committed test split.** `datasets/` is git-ignored, and regenerating the data in CI gave an equalized-odds gap of 0.073 from noise and drift. CI therefore evaluates the exact notebook test split (synthetic, no personal data).
- **Ceiling scores.** The OCR and SMS-fallback numbers in mock mode reflect fixtures, and the report says so. Real accuracy needs live keys.

## Known issues / follow-ups
- BLOCKED (keys): LLM-as-judge for explanations, live RAGAS, live DeepSeek-OCR F1 on real bill photos.
