# Document OCR Evaluation Suite

Evaluates field-level extraction precision, recall, and F1 score on Bangladeshi utility bills, retail receipts, and handwritten khata ledgers.

## Directory Structure
- `images/`: 10 synthetic evaluation images representing common document varieties (DESCO, DPDC, WASA, Titas, NESCO, POS receipts, and handwritten khata sheets).
- `labels.json`: Ground truth field labels for benchmarking.
- `evaluate.py`: Evaluation runner executing OCR extraction and printing field-level precision, recall, and F1 metrics.
- `generate_fixtures.py`: Fixture generator script to create new benchmark sample images.
- `FINETUNE.md`: LoRA fine-tuning playbook for DeepSeek-OCR / vision LLMs on local Bangladeshi document layouts.

## Adding Labelled Images
1. Save the document photo in `images/<filename>.jpg`.
2. Add an entry to `labels.json`:
```json
{
  "filename": "bill_06_breb.jpg",
  "type": "utility_bill",
  "expected": {
    "document_type": "utility_bill",
    "provider": "BREB",
    "amount_bdt": 1850.0,
    "due_date": "2026-12-05"
  }
}
```
3. Run evaluation:
```bash
uv run python evals/ocr/evaluate.py
```
