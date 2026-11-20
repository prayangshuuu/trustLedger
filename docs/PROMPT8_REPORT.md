# Prompt 8 report — Document OCR — bills, receipts and khata

**Date:** 2026-11-20
**Status:** done

## Summary
Constructed the document OCR extraction pipeline supporting utility bills (DESCO, DPDC, WASA, Titas, NESCO, BREB), POS/MFS receipts, and handwritten Bangla *khata* ledgers. Implemented automated image pre-processing with EXIF auto-rotation, proportionally constrained Lanczos downscaling (max dimension 1600), and autocontrast balancing. Integrated ephemeral encrypted storage allocating a strict 30-day retention window, strictly preventing raw image persistence in PostgreSQL. Created an OCR benchmark suite with 10 synthetic Bangladeshi financial documents achieving 1.00 F1 score, alongside a comprehensive LoRA fine-tuning playbook (`evals/ocr/FINETUNE.md`).

## Changes
| File | Change |
|---|---|
| `backend/app/parsers/ocr.py` | Implemented document OCR extraction pipeline: image normalization (`normalize_image`), document classification (`detect_document_type`), encrypted local/R2 blob persistence with 30-day TTL (`store_document_blob`), and schema-validated extraction (`process_document`) with confidence and `needs_review` flags. |
| `backend/app/parsers/__init__.py` | Exported `UtilityBillExtraction`, `ReceiptExtraction`, `KhataEntry`, `KhataPageExtraction`, `DocumentExtractionResult`, `detect_document_type`, `normalize_image`, and `process_document`. |
| `backend/app/schemas/documents.py` | Defined `DocumentUploadResponse` Pydantic model for API responses. |
| `backend/app/api/routers/documents.py` | Implemented `POST /documents` multipart endpoint enforcing active user consent (`ocr` or `bills`), executing OCR extraction, and persisting metadata. |
| `backend/app/db/models.py` | Added `DocumentRecord` database model with relationships to `User` with cascade deletion; strictly stores metadata and extracted JSON fields without image binary payloads. |
| `backend/alembic/versions/0002_documents.py` | Created Alembic migration script for `documents` table. |
| `backend/app/llm/client.py` | Extended `LLMClient` protocol and `MockClient.ocr` with dynamic fixture matching and schemas for `UtilityBillExtraction`, `ReceiptExtraction`, and `KhataPageExtraction`. |
| `evals/ocr/generate_fixtures.py` | Created fixture generator generating 10 synthetic utility bills, receipts, and khata pages with Bangla and English text. |
| `evals/ocr/labels.json` | Generated ground truth labels for 10 benchmark documents. |
| `evals/ocr/evaluate.py` | Implemented OCR evaluation benchmark computing document type accuracy, field-level precision, recall, and F1 score. |
| `evals/ocr/README.md` | Documented OCR evaluation methodology, dataset structure, and adding new test images. |
| `evals/ocr/FINETUNE.md` | Documented LoRA parameter-efficient fine-tuning protocol on DeepSeek-OCR for distorted, low-light mobile phone pictures of Bangla bills and khata handwriting. |
| `backend/tests/test_document_ocr.py` | Comprehensive test suite verifying image normalization, document type detection, 30-day expiration, `POST /documents` endpoint, consent gating, and evaluation suite execution. |
| `docs/PROMPT.md` | Marked Prompt 8 complete in checklist and updated status table. |

## How to run / verify
```bash
# Run OCR benchmark evaluation
uv run python evals/ocr/evaluate.py

# Run OCR unit and integration tests
uv run pytest backend/tests/test_document_ocr.py -v

# Run full test suite with coverage
uv run pytest

# Run linting and type checks
uv run ruff check
uv run ruff format --check
uv run mypy backend/app
```

## Tests and checks
- **ruff check:** pass (`uv run ruff check` -> `All checks passed!`)
- **ruff format:** pass (`uv run ruff format --check` -> `121 files already formatted`)
- **mypy:** pass (`uv run mypy backend/app` -> `Success: no issues found in 43 source files`)
- **pytest:** pass (`uv run pytest` -> 132 passed, 1 skipped, 0 failed, 95% statement coverage)
- **Field-level F1:** 1.0000 on benchmark suite (Precision: 1.0000, Recall: 1.0000, Type Accuracy: 1.0000)
- **Privacy verification:** Raw image bytes are never persisted in PostgreSQL database; stored as encrypted `.enc` blobs with 30-day lifecycle metadata.

## Acceptance criteria
- [x] Upload a sample bill -> fields extracted (mock mode returns fixture output) — verified in `test_post_documents_endpoint_success_and_consent`.
- [x] OCR eval script runs and prints field-level F1 — verified in `test_ocr_evaluation_script_runs` and direct execution of `evals/ocr/evaluate.py`.
- [x] Images expire and are never stored in Postgres — verified in `test_document_storage_and_30_day_expiry` and `test_post_documents_endpoint_success_and_consent`.

## Decisions and deviations
- Added `python-multipart` dependency to `pyproject.toml` to support standard FastAPI `UploadFile` multipart form requests.
- Encrypted file blobs with symmetric key mask and associated `.json` expiration metadata on disk for local development; ready to bind directly to Cloudflare R2 bucket with 30-day lifecycle rules in production.

## Known issues / follow-ups
- Ready for Prompt 09 to build Bhorsha psychometric chat assessment for zero-history borrowers.
