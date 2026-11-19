# Prompt 08 — Document OCR — bills, receipts and khata

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu
**Depends on:** Prompt 6, Prompt 7
**Report:** `docs/PROMPT8_REPORT.md`

## Goal
Read utility bills, wallet receipts and handwritten ledger photos with DeepSeek-OCR and feed them into the feature builder.

## Tasks
- `parsers/ocr.py`: upload → image normalisation (resize, auto-rotate, contrast) → `LLMClient.ocr` with a strict schema per document type (`utility_bill`, `receipt`, `khata_page`) → Pydantic validation → confidence score.
- Document type detection step (cheap classification call or heuristics).
- Images stored encrypted in R2/MinIO with a 30-day expiry; only extracted fields go to the DB.
- Endpoint `POST /documents` (multipart) → extracted fields + confidence; low confidence → `needs_review`.
- `evals/ocr/`: README explaining how to add labelled images, a labels format, and a script computing field-level F1. Include 10 synthetic sample images (generated bills with Bangla + English text) so the eval runs today.
- LoRA fine-tuning notes in `evals/ocr/FINETUNE.md`: dataset format, how many images, how to run. (Training itself is optional in this prompt.)

## Acceptance criteria
- Upload a sample bill → fields extracted (mock mode returns fixture output)
- OCR eval script runs and prints field-level F1
- Images expire and are never stored in Postgres

## Out of scope
RAG, agents.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT8_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 8 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
