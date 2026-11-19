# Prompt 06 — LLM client and SMS parser

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu
**Depends on:** Prompt 2
**Report:** `docs/PROMPT6_REPORT.md`

## Goal
Create the single LLM gateway and the SMS parser that turns raw bKash/Nagad/bank/utility SMS into structured transactions.

## Tasks
- `llm/client.py`: `LLMClient` protocol with `chat(messages, schema=None)` and `ocr(image_bytes, schema)`. Implementations: `DeepSeekClient` (OpenAI-compatible API, JSON mode, timeout, 3 retries with backoff, token usage logging, context caching where supported) and `MockClient` (deterministic fixtures). Select via `LLM_MODE`.
- `parsers/sms.py`: two stages — fast regex rules for known formats first, LLM fallback for unknown formats. Output `Transaction` (date, amount_bdt, direction in|out, type: income|bill|recharge|remittance|savings|transfer|other, counterparty, raw_hash). Handle Bangla digits, English, mixed script.
- Dedupe by transaction id / raw hash. Never store raw text.
- Redact PII with Presidio before any LLM call (add a basic Bangladeshi phone-number recognizer).
- Fixtures: `backend/tests/fixtures/sms/` with ≥ 60 **synthetic** SMS covering cash-in, send money, payment, bill pay, recharge, salary, remittance, failed transactions, Bangla and English. Labelled expected outputs in JSON.
- Prompt file `backend/app/parsers/prompts/sms_parser.md` (XML-structured role prompt, few-shot examples). Version it.

## Acceptance criteria
- Parser F1 ≥ 0.95 on the fixture set in mock mode (regex + mock LLM)
- No raw SMS persisted anywhere (test checks DB and logs)
- Presidio redaction proven by a test
- Live mode works when `DEEPSEEK_API_KEY` is set (mark BLOCKED if no key)

## Out of scope
Feature building, OCR.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT6_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 6 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
