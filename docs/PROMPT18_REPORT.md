# Prompt 18 report — Security, privacy hardening and observability

**Date:** 2026-11-20
**Status:** done

## Summary
The API is now safe to demo publicly. It has per-client rate limits, body/upload size limits, magic-byte image checks, CORS locked to
configured origins, signed borrower tokens (from Prompt 15) and PII-scrubbed logs. A Prometheus `/metrics` endpoint
reports latency, errors, decisions by band, LLM calls/tokens and 429s. A provisioned Grafana dashboard loads live metrics locally
(screenshot `docs/media/grafana_api.png`). `docs/privacy.md` covers what is collected, why, retention, deletion and consent, plus a rule-by-rule check of PLAN §6.

## Changes
| File | Change |
|---|---|
| `backend/app/observability.py` | Prometheus metrics, `GuardMiddleware` (413 / 429 / metrics), PII-scrubbing log-record factory |
| `backend/app/main.py`, `config.py` | CORS from `CORS_ORIGINS` (no credentials, limited methods/headers); `/metrics`; new settings |
| `backend/app/api/routers/documents.py` | 8 MB bound read, JPEG/PNG/WebP magic-byte check (415) |
| `backend/app/schemas/bhorsha.py` | Answer length ≤ 2,000 |
| `backend/app/services/decisions.py` | Decision counter by band/approval |
| `infra/prometheus/prometheus.yml`, `infra/grafana/**`, `docker-compose.yml` | Prometheus + Grafana (profile `monitoring`) with a provisioned 11-panel dashboard |
| `infra/r2-lifecycle.json` | 30-day bucket expiry rule |
| `docs/privacy.md` | Privacy document + rule-by-rule evidence |
| `.env.example` | Rewritten: every variable the code reads, with comments |
| `backend/tests/test_security.py`, `test_env_example.py` | 7 + 1 tests |

## How to run / verify
```bash
make api &
docker compose -f infra/docker-compose.yml --profile monitoring up -d prometheus grafana
open http://localhost:3000/d/trustledger-api          # anonymous viewer
uv run pytest backend/tests/test_security.py backend/tests/test_env_example.py
```

## Tests and checks
- ruff pass · mypy pass (90 files) · pytest **191 passed**, 1 skipped, coverage 93% · evals: all gates PASS
- Grafana: Prometheus target `host.docker.internal:8000` **up**; after 40 requests the dashboard showed p95 474 ms, 0.136 req/s and 19.4 decisions (Fair band, approved)

## Security checklist
- [x] Rate limiting per API key (and per borrower token / IP): 429 + `Retry-After` (test)
- [x] Input size limits: JSON 1 MB, uploads 8 MB (413, test), SMS list ≤ 2,000, answers ≤ 2,000 chars
- [x] File-type checks on uploads by magic bytes (415, test)
- [x] CORS locked to known origins (test: allowed vs disallowed origin)
- [x] Secrets review: `git log -p --all` grep for keys/secrets/tokens and `sk-…`/`AKIA…`/`ghp_…` patterns found only code references (`settings.SESSION_SECRET`, header parsing); no committed secrets. `.env` is git-ignored
- [x] `.env.example` complete (test enforces it)
- [x] Every privacy rule in PLAN §6 has a test or written check (`docs/privacy.md`)
- [x] Prometheus metrics endpoint + Grafana dashboard JSON
- [x] Structured logs never include PII (test with phone numbers, raw SMS, email and bearer token)
- [x] Borrower identity uses signed, expiring tokens; raw user ids are rejected (Prompt 15)

## Acceptance criteria
- [x] `docs/privacy.md` complete
- [x] Grafana dashboard loads with live metrics locally
- [x] Security checklist all ticked or explained

## Decisions and deviations
- **In-memory rate limiter.** It works per process. With several Heroku dynos, move the counters to Redis (`REDIS_URL` is already configured). Noted as a follow-up.
- **Log scrubbing** runs in the log-record factory, so it covers every logger and handler, including uvicorn and third-party libraries.

## Known issues / follow-ups
- `POST /auth/session` should sit behind phone OTP in production. The token design already supports that.
