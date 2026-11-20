"""Generate docs/api.md from the FastAPI OpenAPI schema plus short notes.

uv run python backend/scripts/gen_api_docs.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import create_app

NOTES = """# TrustLedger API reference

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
"""


def main() -> None:
    schema = create_app().openapi()
    by_tag: dict[str, list[str]] = {}
    for path, ops in schema["paths"].items():
        for method, op in ops.items():
            tag = (op.get("tags") or ["Other"])[0]
            summary = op.get("summary", "")
            desc = (op.get("description") or "").strip().split("\n")[0]
            by_tag.setdefault(tag, []).append(
                f"| `{method.upper()}` | `{path}` | {summary} | {desc} |"
            )
    out = [NOTES]
    for tag, rows in by_tag.items():
        out += [f"\n### {tag}\n", "| Method | Path | Summary | Notes |", "|---|---|---|---|", *rows]
    out.append("\n## Example: `POST /score` response (Shathi)\n")
    example = {
        "decision_id": "…", "p_repay": 0.9337, "score": 691, "band": "Good", "approved": True, "fairness_ok": True,
        "good": ["বিল সময়মতো পরিশোধ", "নিয়মিত মোবাইল রিচার্জ"], "bad": ["সঞ্চয় কম"],
        "tips": ["প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।"], "group": "F_urban", "threshold_used": 0.7173,
    }  # fmt: skip
    out.append("```json\n" + json.dumps(example, ensure_ascii=False, indent=2) + "\n```\n")
    out.append(
        "\nMCP tools (`score_user`, `explain_score`, `fairness_audit`, `get_inclusion_lift`) wrap these endpoints: see `mcp_server/README.md`.\n"
    )
    (ROOT / "docs" / "api.md").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote docs/api.md ({sum(len(r) for r in by_tag.values())} endpoints)")


if __name__ == "__main__":
    main()
