# Privacy at TrustLedger

TrustLedger scores people without a credit history from habits on their phone. That data is personal, so
the system is built to collect as little as possible, keep it for as short as possible, and let the borrower
switch it off or erase it at any time.

## What we collect and why

| Data | Source | Why | Stored on the server? | Retention |
|---|---|---|---|---|
| Phone number | App sign-up | Identify the account | **No.** Only a SHA-256 hash (`users.phone_hash`) | Until deletion |
| Gender, region (urban/rural), division | App sign-up | **Fairness only**: group thresholds and audits. Never a model input | Yes (`users`) | Until deletion |
| Transaction SMS (wallet, bank, utility) | Phone, with `sms` consent | Derive 10 habit features | **No.** In production SMS is parsed on the device. In the demo (`DEMO_MODE=true`) raw SMS is parsed in memory and dropped; only the features are kept | Features until deletion |
| Bill / receipt / khata photos | Upload, with `ocr` or `bills` consent | Read due dates, amounts and paid stamps | Encrypted image (Fernet) in R2/MinIO, **never in Postgres**; extracted fields in `documents` | Image **30 days** (bucket lifecycle + nightly purge); fields until deletion |
| Bhorsha chat answers | App, with `bhorsha` consent | 0–100 `bhorsha_score` for people with no history | **No** transcript is stored, only the score and dimension scores | Score until deletion |
| Derived features | Computed | Model input | `feature_snapshots` (numbers only) | Until deletion |
| Decisions | Computed | Explain and audit every decision | `decisions` + `audit_log` (score, SHAP reasons, group, threshold, fairness checks, model and prompt versions) | Until deletion |
| Repayments | Lender / wallet webhook | Servicing and limit ladder | `repayments` | Until deletion |

No column stores raw SMS text (`backend/tests/test_no_raw_sms.py`). All repository data, fixtures and demo
personas are synthetic.

## Consent

- One consent record per source: `sms`, `bills`, `recharge`, `ocr`, `bhorsha` (`consents` table).
- Every data path checks consent first. `/score`, `/apply`, `/documents` and `/bhorsha` return **403 CONSENT_MISSING** without it.
- Revoking (`DELETE /consent/{source}`, or the switch in app Settings) takes effect immediately, and the source is no longer used.
- Consent calls need the borrower's own signed session token, or a lender API key acting for that borrower.

## Deletion ("delete my data")

`DELETE /me` (Settings → "আমার সব তথ্য মুছুন") removes the user row and, by cascade, every consent, snapshot,
application, decision, repayment, document record and audit row linked to them. It also deletes their encrypted images
from object storage (`backend/app/privacy/deletion.py`, tests `test_deletion.py`, `test_storage.py`).

## External AI services

- Every LLM call goes through `LLMClient` (`backend/app/llm/client.py`) with timeouts, retries and schema validation.
- Before any text is sent to DeepSeek, Microsoft Presidio redacts Bangladeshi phone numbers, NIDs, emails, card and IBAN numbers (`backend/app/privacy/redaction.py`). Bhorsha answers and SMS fallbacks are redacted the same way.
- With `LLM_MODE=mock` (tests, CI, offline demo) nothing leaves the server.

## Security controls

| Control | Where |
|---|---|
| API keys for lenders/partners (constant-time compare), signed 12 h borrower tokens (HMAC-SHA256) | `api/deps.py`, `security.py` |
| Rate limit per key/token/IP (default 300/min), 1 MB JSON and 8 MB upload limits | `observability.py` |
| Uploads accepted only if the bytes are JPEG/PNG/WebP (magic-byte check) | `api/routers/documents.py` |
| CORS limited to configured dashboard origins, no cookies | `main.py`, `CORS_ORIGINS` |
| Logs scrubbed of phone numbers, IDs, emails and bearer tokens at record creation | `observability.py`, `test_security.py::test_logs_never_contain_pii` |
| Secrets only from environment variables; `.env` git-ignored; `.env.example` lists every variable (test) | `config.py`, `test_env_example.py` |
| Document images encrypted at rest (Fernet), 30-day expiry | `storage.py` |

## Rule-by-rule check (PLAN_CONTEXT §6)

| Rule | Evidence |
|---|---|
| gender/region/division/age never model inputs | `FeatureVector(extra="forbid")`, `test_sensitive_attributes_cannot_be_model_inputs`, Fairness Agent `no_sensitive_inputs` check |
| Every decision logged with model version, features, SHAP reasons, group, threshold, fairness result | `services/decisions.py::persist_decision`, `test_seed_population_and_full_audit` |
| Approval and equalized-odds gaps ≤ 0.05, CI fails otherwise | `evals/run_all.py`, `test_evals_gate.py`, CI job |
| Raw SMS never leaves the device in production; demo only with `DEMO_MODE`, never persisted | `/parse/sms` and `/apply` 403 without DEMO_MODE (`test_sms_rejected_outside_demo_mode`), `test_no_raw_sms.py`, PII-free logs test |
| PII redacted before external LLM calls | `test_presidio_pii_redaction`, `test_rubric_scoring_goes_through_llm_client` |
| Consent per source; `DELETE /me` removes all data | `test_api_consent.py`, `test_deletion.py`, `test_storage.py` |
| No real personal data in repo | Written check: fixtures in `backend/tests/fixtures`, `evals/` and personas are generated; phone numbers in fixtures are fake |
| Every score has Bangla reasons and tips | Fairness Agent blocks a decision without reasons (`reasons_present`) |
| Explainer mentions only SHAP features | Rule check in `agents/explainer.py`; eval: 300/300 |
| LLM calls: timeout, retries, schema, mock | `llm/client.py`, `test_sms_parser.py` (retry/backoff tests) |
| No bank, bKash or Nagad logos | Written check: apps use Material icons and a generic wallet icon only |

## What is still the team's responsibility before going live

- Set `STORAGE_ENCRYPTION_KEY`, `SESSION_SECRET` and `API_KEYS` in production (dev fallbacks exist only for local use).
- Add an R2 lifecycle rule that deletes objects after 30 days (`infra/r2-lifecycle.json`).
- Put `POST /auth/session` behind phone OTP (today it requires the app's API key only).
- Run a data protection impact assessment against Bangladesh's data protection rules before handling real users.
