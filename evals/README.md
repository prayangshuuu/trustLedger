# Evaluations and quality gates

`uv run python evals/run_all.py` runs every offline evaluation and writes `training_files/eval_report.json`
and `evals/EVAL_REPORT.md`. It exits non-zero when a gate fails; CI runs it on every push.

| Suite | Folder | Gate |
|---|---|---|
| Model: AUC, KS, Brier, ECE + calibration on the notebook's 20,000-row test split | `run_all.py` (`data/test_split.csv.gz` in CI) | AUC ≥ notebook − 0.01 |
| Fairness: approval-rate and equalized-odds gaps with group thresholds | `run_all.py` | both ≤ 0.05 |
| SMS parser: type macro-F1, direction, amount | `sms/` | F1 ≥ 0.95 |
| OCR field F1 (10 synthetic images) | `ocr/` | ≥ 0.90 |
| RAG: context precision / recall / hit rate / faithfulness (30 Q/A) | `rag/` | hit rate ≥ 0.90 |
| Explanations: summary mentions only SHAP features (300 applicants); LLM-as-judge in live mode | `run_all.py` | 0 violations |
| Bhorsha: score stability and responsible > careless | `run_all.py` | stable and ordered |
| Prompt regression: fixed inputs per agent prompt vs golden JSON | `prompts/golden/` | exact match (mock mode) |

After an intended prompt or model change, review the diff and refresh goldens:
`uv run python evals/run_all.py --update-golden`.

Mock-mode caveats: OCR and the SMS LLM fallback return labelled or fixed outputs, so they measure the pipeline,
not model accuracy. Run with `LLM_MODE=live DEEPSEEK_API_KEY=... DEEPSEEK_OCR_URL=...` for real numbers.
`backend/tests/test_evals_gate.py` proves the fairness gate fails with a deliberately biased threshold.
