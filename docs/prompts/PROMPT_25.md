# Prompt 25 — Live AI layer, real user uploads and model-validated decisions

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu + Daniel
**Depends on:** Prompt 6, Prompt 7, Prompt 8, Prompt 9, Prompt 11, Prompt 22, Prompt 24
**Report:** `docs/PROMPT25_REPORT.md`

## Goal
Move from demo mode to real use: any user can upload their own data in the web app and the Android app, the AI layer runs live on DeepSeek, and every AI output is validated before it reaches the credit model.

## Tasks
**A. DeepSeek live configuration**
- The API key is provided by the team in `.env` as `DEEPSEEK_API_KEY`. **Never** write it into code, prompts, docs, tests, commits, logs or images. `.env.example` keeps it empty.
- Read https://api-docs.deepseek.com at implementation time and record in the report: base URL, current model names, JSON output support, function/tool calling, context caching, file/image input, rate limits and pricing. Do not rely on older names from earlier prompts.
- Config (all env, with defaults set from the docs): `DEEPSEEK_BASE_URL` (OpenAI-compatible `https://api.deepseek.com`), `DEEPSEEK_CHAT_MODEL` (fast model for parsing, Bhorsha turns, explanations), `DEEPSEEK_REASONER_MODEL` (stronger model for Bhorsha scoring and hard parsing cases), `LLM_MODE=live` by default when a key exists, `mock` for tests/CI.
- `GET /health/ai`: tiny live call, returns model names, latency and status — never the key.
- Every call: timeout, retries with backoff, temperature 0 for extraction/scoring, JSON-mode or tool-calling with Pydantic validation and one automatic repair retry, token usage + estimated cost logged per request and per user session, request-hash cache in Redis for identical inputs, a per-session token budget.
- If DeepSeek is down: clear Bangla error in the UI, retry option, regex-only parsing with `confidence=low` — **never** silently fall back to mock in live mode.

**B. OCR that actually works**
- Test whether the current DeepSeek API accepts image input (per the docs). If yes, use it for bills/receipts/khata with strict schemas.
- If not, implement `OCR_BACKEND` with automatic selection:
  - `deepseek-ocr-local`: open-weights DeepSeek-OCR served in the `ocr` docker profile (vLLM or transformers; GPU optional, document CPU speed)
  - `tesseract`: Tesseract with `ben+eng` language data, then DeepSeek text model structures the raw text into the schema
- Report which backend is active in `/health/ai` and in each decision trace.

**C. Real user upload flow (web at `http://localhost:8000/app/` and Flutter Android)**
- Real mode is the default; demo personas stay behind a clearly labelled "Try a demo" switch.
- "Use my own data" flow: consent per source → upload any combination of:
  - SMS export: `.txt`, `.csv`, and the XML format of common Android SMS backup apps; or paste text
  - bill / receipt / khata photos (JPG, PNG, HEIC) and PDFs, multiple files, drag-and-drop on web, camera on Android
  - Android only: optional on-device inbox read (`READ_SMS` permission, explicit consent) filtered to financial senders
- Per-file progress, then a **review screen**: extracted transactions and bill fields in a table the user can correct, remove or confirm. Low-confidence rows are highlighted.
- Only after the user confirms → features → `/apply` → decision with Bangla reasons and tips.
- If history is too short → route to Bhorsha automatically.
- Uploaded raw content is processed in memory, redacted before any LLM call, never persisted (images: encrypted R2 with 30-day expiry as per Prompt 8). Update `docs/privacy.md` for real-mode uploads.

**D. Validate AI output with the model**
- `core/validation.py` runs between the AI layer and scoring:
  - schema + type checks on every extracted transaction and document field
  - **range check** against `models/feature_ranges.json` from training; out-of-range values clipped and flagged
  - **out-of-distribution check**: z-score / PSI of the feature vector vs the training data; too many OOD features → `needs_review`
  - **sufficiency**: < 3 months of wallet data and no Bhorsha → ask for more data or Bhorsha, never score on nothing
  - **cross-checks**: bill amounts from OCR vs bill payments in SMS; duplicate transactions across sources; impossible dates
  - **confidence propagation**: low-confidence extractions are excluded or down-weighted, and the decision says so
- Decision response gets a `data_quality` block (sources used, months covered, transactions counted, flags, confidence) shown in the app as simple Bangla notes.
- **Explanation guard**: the live Explainer writes Bangla text from SHAP + RAG; a validator rejects any text that mentions a feature not in the SHAP output, numbers that don't match, or promises of approval; regenerate once, else fall back to the template reasons from `trustledger_meta.json`.
- **Bhorsha guard**: LLM rubric scores must be in range, consistent across paired questions and stable across two runs (temperature 0); otherwise the session is flagged.
- **Model sanity**: the scoring service refuses vectors that fail validation, and logs model version + feature hash for every decision.

**E. Prove it end to end**
- `evals/live/`: generate 20 synthetic users whose **true features are known**, render them into realistic SMS exports and bill images, run them through the live pipeline, and compare:
  - SMS parsing F1, OCR field F1
  - per-feature error between extracted and true features
  - decision agreement between "features from AI pipeline" and "true features" (target ≥ 95%)
  - explanation guard violations (target 0)
  - tokens and cost per user
  Save `evals/live/live_report.json` and a markdown summary.
- Tests: all unit tests run in mock mode; live tests marked `@pytest.mark.live` and skipped without a key.
- Update `PLAN_CONTEXT.md`: §4 runtime-LLM row with the verified DeepSeek model names and the active OCR backend; §7 env vars (`DEEPSEEK_CHAT_MODEL`, `DEEPSEEK_REASONER_MODEL`, `OCR_BACKEND`, `LLM_SESSION_TOKEN_BUDGET`); §6 privacy rules for real-mode uploads.
- Keep the Prompt 24 docker stack working: pass the new env vars through compose, add the `ocr` profile if a local OCR backend is used.

## Acceptance criteria
- A real user (no demo persona) uploads their own SMS export and a bill photo at `http://localhost:8000/app/` and in the Android app, reviews and corrects the extracted data, and gets a decision with Bangla reasons, tips and a data-quality block — in live mode
- `/health/ai` is green with the real DeepSeek models listed
- OCR works on real phone photos of a Bangladeshi utility bill (state which backend)
- `evals/live/live_report.json` meets: SMS F1 ≥ 0.90, decision agreement ≥ 95%, 0 explanation-guard violations
- Validation rejects or flags bad AI output (tests for out-of-range, OOD, insufficient data, mismatched bills, hallucinated explanation)
- The API key appears nowhere in git history, logs, images or the frontend bundle (grep + `docker history` + built JS check)
- `make docker-up` and `make docker-smoke` still pass

## Out of scope
New product features beyond upload, live AI and validation.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT25_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 25 in `PROMPT.md`.
4. Commit: `prompt 25: live ai layer, real user uploads and model-validated decisions`
