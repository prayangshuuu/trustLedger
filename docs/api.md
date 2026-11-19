# TrustLedger REST API Documentation

This document describes the TrustLedger REST API v1 for fair, private, and explainable credit scoring in Bangladesh.

- **Base URL:** `http://localhost:8000` (Local) / `https://api.trustledger.org` (Production)
- **Interactive Documentation (Swagger UI):** `GET /docs`
- **ReDoc Documentation:** `GET /redoc`
- **OpenAPI JSON Specification:** `GET /openapi.json`

---

## 1. Authentication and Headers

TrustLedger uses two tiers of authentication:

1. **Lender & Partner API Key (`X-API-Key`):**
   - Passed in the HTTP header `X-API-Key: <api_key>`.
   - Used by institutional partners, banks, and MFIs accessing bulk scoring and reporting endpoints.
2. **Borrower Session Bearer Token (`Authorization`):**
   - Passed in the HTTP header `Authorization: Bearer <user_id_or_token>`.
   - Alternatively, `X-User-ID: <user_id>` can be passed during development and demo mode.
3. **Correlation ID (`X-Request-ID`):**
   - Automatically generated for every request if not supplied. Returned in response headers for distributed tracing and audit correlation.

---

## 2. Standard Error Envelope

All errors adhere to a uniform JSON envelope:

```json
{
  "error": "CONSENT_MISSING",
  "detail": "Applicant lacks active consent for required scoring sources (sms or bhorsha).",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

| HTTP Status | Error Code | Description |
|---|---|---|
| `400 Bad Request` | `ALL_FEATURES_MISSING` / `HTTP_400` | Malformed payload or all features are null. |
| `401 Unauthorized` | `HTTP_401` | Missing or invalid `X-API-Key` or Bearer token. |
| `403 Forbidden` | `CONSENT_MISSING` | Applicant has not granted or has revoked mandatory data consent. |
| `404 Not Found` | `HTTP_404` | Requested user, decision, or resource was not found. |
| `422 Unprocessable` | `VALIDATION_ERROR` | Schema validation error (e.g. out-of-bounds numeric field). |

---

## 3. Endpoints

### System Endpoints

#### `GET /health`
Verifies service availability and database connectivity.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "app": "trustledger",
  "database": "connected",
  "timestamp": "2026-11-20T06:30:00.000000Z"
}
```

#### `GET /version`
Introspects current production model artifact fingerprint and git commit SHA.

**Response `200 OK`:**
```json
{
  "app_version": "0.1.0",
  "model_version": "356d061e78fdf8cf",
  "git_sha": "132c75e"
}
```

---

### Privacy & Consent Endpoints

#### `POST /consent`
Grants or re-activates data processing consent for a specific data source.

**Request Body:**
```json
{
  "user_id": "ad037885-9fd2-4ac3-a1c3-07aace1eae3b",
  "source": "sms"
}
```
*Valid sources:* `sms`, `bills`, `recharge`, `ocr`, `bhorsha`.

**Response `201 Created`:**
```json
{
  "status": "granted",
  "user_id": "ad037885-9fd2-4ac3-a1c3-07aace1eae3b",
  "source": "sms",
  "granted_at": "2026-11-20T06:30:00.000000Z"
}
```

#### `DELETE /consent/{source}`
Revokes active consent for a data source. Immediately blocks automated scoring until re-granted.

**Parameters:** `source` in path (`sms` / `bills` / `recharge` / `ocr` / `bhorsha`); `user_id` in query or `X-User-ID` header.

**Response `200 OK`:**
```json
{
  "status": "revoked",
  "user_id": "ad037885-9fd2-4ac3-a1c3-07aace1eae3b",
  "source": "sms"
}
```

#### `DELETE /me`
Implements the GDPR / Bangladesh Data Protection Act "Right to be Forgotten". Permanently removes all records for the authenticated borrower across users, consents, feature snapshots, applications, decisions, and audit logs.

**Headers:** `Authorization: Bearer <user_id>` or `X-User-ID: <user_id>`.

**Response `200 OK`:**
```json
{
  "status": "deleted",
  "user_id": "ad037885-9fd2-4ac3-a1c3-07aace1eae3b"
}
```

---

### Scoring & Decision Endpoints

#### `POST /score`
Calculates an explainable credit decision, calibrated against demographic group thresholds.

**Request Payload (Shathi Benchmark Persona Example):**
```json
{
  "group": "F_urban",
  "amount_bdt": 15000.0,
  "features": {
    "monthly_inflow_bdt": 14000.0,
    "income_volatility": 0.10,
    "months_on_wallet": 30.0,
    "txn_per_month": 18.0,
    "bills_on_time": 0.97,
    "recharge_regularity": 0.90,
    "savings_ratio": 0.04,
    "sends_money_home": 1.0,
    "bhorsha_score": null,
    "loan_to_income": 4.0
  }
}
```

**Response `200 OK` (Approved with Bangla Reasons & Tips):**
```json
{
  "decision_id": "f8a927c3-3e19-4a0b-8d72-9118c728e9d0",
  "p_repay": 0.933661,
  "score": 691,
  "band": "Good",
  "approved": true,
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
  "reasons": [
    {
      "feature": "bills_on_time",
      "label": "Bills paid on time",
      "text": "বিল সময়মতো পরিশোধ",
      "impact": 0.938,
      "kind": "good"
    },
    {
      "feature": "recharge_regularity",
      "label": "Mobile recharge regularity",
      "text": "নিয়মিত মোবাইল রিচার্জ",
      "impact": 0.332,
      "kind": "good"
    },
    {
      "feature": "savings_ratio",
      "label": "Savings ratio",
      "text": "সঞ্চয় কম",
      "impact": -0.144,
      "kind": "bad"
    }
  ],
  "group": "F_urban",
  "threshold_used": 0.717315,
  "model_version": "356d061e78fdf8cf",
  "timestamp": "2026-11-20T06:30:00.000000Z"
}
```

#### `GET /explain/{decision_id}`
Retrieves the full explainability breakdown and actionable recommendations for a previously issued loan decision.

**Response `200 OK`:**
```json
{
  "decision_id": "f8a927c3-3e19-4a0b-8d72-9118c728e9d0",
  "score": 691,
  "band": "Good",
  "approved": true,
  "good": ["বিল সময়মতো পরিশোধ", "নিয়মিত মোবাইল রিচার্জ"],
  "bad": ["সঞ্চয় কম"],
  "tips": ["প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।"],
  "reasons": [
    {
      "feature": "bills_on_time",
      "label": "Bills paid on time",
      "text": "বিল সময়মতো পরিশোধ",
      "impact": 0.938,
      "kind": "good"
    }
  ],
  "model_version": "356d061e78fdf8cf",
  "timestamp": "2026-11-20T06:30:00.000000Z"
}
```

---

### Fairness & Inclusion Endpoints

#### `GET /fairness/report`
Computes a live demographic parity and equalized odds audit across all stored decisions in the database.

**Response `200 OK`:**
```json
{
  "total_decisions": 3,
  "by_group": {
    "F_urban": {
      "group": "F_urban",
      "count": 1,
      "approval_rate": 1.0,
      "tpr": null,
      "fpr": null
    },
    "M_urban": {
      "group": "M_urban",
      "count": 1,
      "approval_rate": 1.0,
      "tpr": null,
      "fpr": null
    },
    "F_rural": {
      "group": "F_rural",
      "count": 1,
      "approval_rate": 1.0,
      "tpr": null,
      "fpr": null
    }
  },
  "approval_rate_gap": 0.0,
  "tpr_gap": null,
  "fpr_gap": null,
  "equalized_odds_gap": null,
  "fairness_ok": true
}
```

#### `GET /inclusion-lift`
Evaluates the demographic reach and financial inclusion lift of TrustLedger compared to traditional legacy banking rules.

Traditional rule: Requires formal bank account and (salary slip OR monthly inflow >= 25,000 BDT).

**Response `200 OK`:**
```json
{
  "total_evaluated": 3,
  "bank_rule_approvals": 0,
  "bank_rule_approval_rate": 0.0,
  "trustledger_approvals": 3,
  "trustledger_approval_rate": 1.0,
  "newly_included_count": 3,
  "newly_included_rate": 1.0,
  "inclusion_lift_percentage": 100.0,
  "rule_description": "has_bank_account == 1 AND (has_salary_slip == 1 OR monthly_inflow_bdt >= 25000)"
}
```
