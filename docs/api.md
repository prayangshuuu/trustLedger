# TrustLedger API reference

Generated from the OpenAPI schema by `backend/scripts/gen_api_docs.py`. Interactive docs: `GET /api/docs` (Swagger),
`GET /api/redoc`, schema `GET /openapi.json`.

## Authentication

| Caller | Header | How to get it |
|---|---|---|
| Lender, partner, the apps | `X-API-Key: <key>` | One of the comma-separated `API_KEYS` (empty = local development without keys) |
| Borrower (app) | `Authorization: Bearer tl1.<user>.<expiry>.<hmac>` | `POST /auth/session` (needs the app's API key; behind phone OTP in production). 12 h, HMAC-SHA256 |

Every response carries `X-Request-ID`. Errors share one envelope:

```json
{"error": "CONSENT_MISSING", "detail": "…", "request_id": "…"}
```

Codes: `CONSENT_MISSING` 403, `ALL_FEATURES_MISSING` 400, `VALIDATION_ERROR` 422, `RATE_LIMITED` 429, `PAYLOAD_TOO_LARGE` 413, `HTTP_<status>`.
Limits: 300 requests/min per key, token or IP; JSON body 1 MB; uploads 8 MB (JPEG/PNG/WebP only).

## Main flow (Shathi)

```bash
H='X-API-Key: dev-key'
curl -X POST $API/auth/session -H "$H" -d '{"user_id":"<id>"}'                         # -> token
curl -X POST $API/consent -H "Authorization: Bearer $TOKEN" -d '{"user_id":"<id>","source":"sms"}'
curl -X POST $API/apply -H "$H" -d '{"user_id":"<id>","amount_bdt":15000}'           # agents -> decision + trace_id
curl $API/explain/<decision_id> -H "$H"
curl -X POST $API/score -H "$H" -d '{"group":"F_urban","features":{"bills_on_time":0.97,"monthly_inflow_bdt":14000}}'
```

`/apply` statuses: `approved`, `rejected`, `needs_review` (|p − threshold| ≤ 0.03), `blocked` (fairness check failed),
`bhorsha_required` (no wallet history; run `/bhorsha/*` first), `rejected_input` (consent or input problem).

## Endpoints


### System

| Method | Path | Summary | Notes |
|---|---|---|---|
| `GET` | `/health` | Service Health Check | Return application and database health status. |
| `GET` | `/version` | Model and API Version | Return model version hash, git commit SHA, and core version. |

### Privacy & Consent

| Method | Path | Summary | Notes |
|---|---|---|---|
| `POST` | `/auth/session` | Issue a borrower session | Issue a signed 12-hour borrower token. Requires the app's API key; in production this |
| `POST` | `/consent` | Grant Data Source Consent | Grant or reactivate consent for one source (sms, bills, recharge, ocr, bhorsha). |
| `DELETE` | `/consent/{source}` | Revoke Data Source Consent | Revoke consent for a data source. Scoring stops using it immediately. |
| `GET` | `/me` | Borrower profile, consents and latest decision |  |
| `DELETE` | `/me` | Delete All User Data (Right to be Forgotten) | Permanently delete the user and every related record and stored document image. |

### Bhorsha Psychometric Assessment

| Method | Path | Summary | Notes |
|---|---|---|---|
| `POST` | `/bhorsha/start` | Start Bhorsha Assessment Session | Initialize a psychometric dialogue for zero-history borrowers. |
| `POST` | `/bhorsha/{session_id}/answer` | Submit Scenario Answer | Record an answer to the current scenario and return next question or completion notification. |
| `GET` | `/bhorsha/{session_id}/result` | Get Bhorsha Assessment Outcome and Update Snapshot | Compute aggregate Bhorsha score and write bhorsha_score into applicant feature snapshot. |

### Documents & OCR

| Method | Path | Summary | Notes |
|---|---|---|---|
| `POST` | `/documents` | Upload Document and Extract Fields via OCR | Normalize uploaded document, perform DeepSeek-OCR extraction, and save encrypted blob with 30-day TTL. |

### Features & Parsers

| Method | Path | Summary | Notes |
|---|---|---|---|
| `POST` | `/parse/sms` | Parse SMS into Transactions and Features (DEMO_MODE only) | Parse raw SMS list, deduplicate transactions, and engineer the 10 credit scoring features. |
| `POST` | `/features` | Store Feature Snapshot | Persist an applicant feature snapshot for scoring evaluation. |

### Scoring & Decisions

| Method | Path | Summary | Notes |
|---|---|---|---|
| `POST` | `/score` | Score Applicant (Features or User ID) | Generate a fair, explainable credit decision for an applicant. |
| `GET` | `/explain/{decision_id}` | Get Decision Explanation | Retrieve full SHAP feature attributions and Bangla reasons for a decision. |

### Fairness & Inclusion

| Method | Path | Summary | Notes |
|---|---|---|---|
| `GET` | `/fairness/report` | Demographic Fairness Audit Report | Approval rate, TPR and FPR per group over stored decisions, with gaps vs the 0.05 gate. |
| `GET` | `/inclusion-lift` | Financial Inclusion Lift vs Traditional Bank Rules | Compare TrustLedger approvals against the legacy bank rule used in the notebook: |

### Agent Pipeline

| Method | Path | Summary | Notes |
|---|---|---|---|
| `POST` | `/apply` | Run the multi-agent pipeline | Data -> Bhorsha router -> Scoring -> Explainer -> Fairness. Returns the decision and trace id. |
| `GET` | `/traces/{trace_id}` | Get an agent run trace |  |

### Loans

| Method | Path | Summary | Notes |
|---|---|---|---|
| `GET` | `/loans/{application_id}` | Loan status and limit |  |
| `POST` | `/loans/{application_id}/repayments` | Record a repayment | Idempotent when idempotency_key is given (Temporal activities may retry). |
| `POST` | `/loans/{application_id}/limit-upgrade` | Raise credit limit | Raise the limit by `factor` (default +20%). Requires >= 3 on-time and no late repayments. |
| `POST` | `/loans/{application_id}/disburse` | Mark disbursed | Mock disbursement (no money moves). Idempotent: an already disbursed loan is returned. |

### Demo

| Method | Path | Summary | Notes |
|---|---|---|---|
| `GET` | `/demo/personas` | Demo persona user IDs |  |
| `POST` | `/demo/reset` | Re-seed the 3 demo personas |  |

### Dashboard

| Method | Path | Summary | Notes |
|---|---|---|---|
| `GET` | `/stats/overview` | Dashboard KPIs |  |
| `GET` | `/stats/score-distribution` | Histogram of scores |  |
| `GET` | `/stats/divisions` | Approvals by division (aggregate only) |  |
| `GET` | `/decisions` | Live decision feed |  |
| `GET` | `/decisions/{decision_id}` | Applicant decision detail with trace |  |
| `GET` | `/stats/model-metrics` | Offline model, fairness and federated metrics | Notebook test-set metrics (training_files/metrics.json) and Flower results. |

## Example: `POST /score` response (Shathi)

```json
{
  "decision_id": "…",
  "p_repay": 0.9337,
  "score": 691,
  "band": "Good",
  "approved": true,
  "fairness_ok": true,
  "good": [
    "বিল সময়মতো পরিশোধ",
    "নিয়মিত মোবাইল রিচার্জ"
  ],
  "bad": [
    "সঞ্চয় কম"
  ],
  "tips": [
    "প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।"
  ],
  "group": "F_urban",
  "threshold_used": 0.7173
}
```


MCP tools (`score_user`, `explain_score`, `fairness_audit`, `get_inclusion_lift`) wrap these endpoints: see `mcp_server/README.md`.
