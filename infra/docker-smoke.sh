#!/usr/bin/env bash
# TrustLedger Docker Full-Stack Smoke Test
# Usage: bash infra/docker-smoke.sh [BASE_URL] [API_KEY]
set -euo pipefail

BASE="${1:-http://localhost:8000}"
KEY="${2:-${API_KEYS:-dev-key}}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0

ok() { pass=$((pass + 1)); printf '  \033[32m✓\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗ %s\033[0m\n' "$1"; exit 1; }

req() { # method path [json] [extra header]
  local args=(-sS -o "$TMP/body" -w '%{http_code}' -X "$1" "$BASE$2" -H "X-API-Key: $KEY" -H 'Content-Type: application/json')
  [ -n "${4:-}" ] && args+=(-H "$4")
  [ -n "${3:-}" ] && args+=(--data-binary "$3")
  curl "${args[@]}"
}

jq_() { python3 -c "import json,sys;d=json.load(open('$TMP/body'));print($1)"; }

echo "=========================================================="
echo "TrustLedger Docker Full-Stack Smoke Test → $BASE"
echo "=========================================================="

# 0. Wait for service readiness
echo "Waiting for API service readiness..."
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" || true)
  if [ "$code" = "200" ]; then
    break
  fi
  sleep 2
done

# 1. Health endpoint (Postgres & Redis connected)
CODE=$(req GET /health)
[ "$CODE" = "200" ] || fail "health endpoint returned $CODE"
DB_STATUS=$(jq_ "d['database']")
REDIS_STATUS=$(jq_ "d['redis']")
[ "$DB_STATUS" = "connected" ] || fail "database status is $DB_STATUS"
[ "$REDIS_STATUS" = "connected" ] || fail "redis status is $REDIS_STATUS"
ok "1. Health check: DB ($DB_STATUS), Redis ($REDIS_STATUS)"

# 2. Lender Dashboard (React + Vite) index served at /
DASH_CODE=$(curl -sS -o "$TMP/dash.html" -w '%{http_code}' "$BASE/")
[ "$DASH_CODE" = "200" ] || fail "Lender dashboard root returned $DASH_CODE"
grep -qEi "root|TrustLedger" "$TMP/dash.html" || fail "Lender dashboard HTML missing root div"
ok "2. React Lender Dashboard rendered at http://localhost:8000/"

# 3. Borrower Web App (React) index served at /app/
WEB_CODE=$(curl -sS -o "$TMP/web.html" -w '%{http_code}' "$BASE/app/")
[ "$WEB_CODE" = "200" ] || fail "Borrower web app returned $WEB_CODE"
grep -qEi "TrustLedger|HindSiliguri" "$TMP/web.html" || fail "Borrower web app HTML missing app assets"
ok "3. Borrower Web App rendered at http://localhost:8000/app/"

# 4. Interactive API documentation served at /docs and /api/docs
DOCS_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/docs")
[ "$DOCS_CODE" = "200" ] || fail "Public docs returned $DOCS_CODE"
API_DOCS_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/docs")
[ "$API_DOCS_CODE" = "200" ] || fail "Swagger API docs returned $API_DOCS_CODE"
ok "4. Documentation verified: Public docs (/docs: 200), Swagger (/api/docs: 200)"

# 5. Score Applicant via /api/v1/score and verify score and explanation payload
SCORE_PAYLOAD='{
  "features": {
    "monthly_inflow_bdt": 28000,
    "income_volatility": 0.12,
    "months_on_wallet": 24,
    "txn_per_month": 18,
    "bills_on_time": 0.95,
    "recharge_regularity": 0.90,
    "savings_ratio": 0.15,
    "sends_money_home": 1,
    "bhorsha_score": 75,
    "loan_to_income": 0.35
  },
  "group": "F_urban",
  "amount_bdt": 15000
}'
SCORE_CODE=$(req POST /api/v1/score "$SCORE_PAYLOAD")
[ "$SCORE_CODE" = "200" ] || fail "/api/v1/score returned $SCORE_CODE: $(cat "$TMP/body")"
SCORE_VAL=$(jq_ "d['score']")
SCORE_BAND=$(jq_ "d['band']")
SCORE_APP=$(jq_ "d['approved']")
REASONS_COUNT=$(jq_ "len(d['reasons'])")
[ "$SCORE_VAL" -ge 300 ] && [ "$SCORE_VAL" -le 900 ] || fail "invalid score $SCORE_VAL"
[ "$REASONS_COUNT" -ge 1 ] || fail "reasons count is $REASONS_COUNT"
ok "5. Scoring & Explanations (/api/v1/score): Score $SCORE_VAL ($SCORE_BAND), Approved: $SCORE_APP, $REASONS_COUNT reasons"

# 6. Observability: Prometheus (:9090) and Grafana (:3000)
PROM_CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:9090/-/healthy" || true)
[ "$PROM_CODE" = "200" ] || fail "Prometheus healthy returned $PROM_CODE"
GRAF_CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:3000/api/health" || true)
[ "$GRAF_CODE" = "200" ] || fail "Grafana health returned $GRAF_CODE"
ok "6. Observability suite: Prometheus (:9090 -> 200), Grafana (:3000 -> 200)"

# 7. MCP Server HTTP Transport (:8001)
MCP_CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:8001/health" || true)
[ "$MCP_CODE" = "200" ] || fail "MCP Server health returned $MCP_CODE"
ok "7. Model Context Protocol (MCP) server responding at http://localhost:8001/health"

echo "=========================================================="
echo "ALL DOCKER CHECKS PASSED ($pass / $pass checks)"
echo "=========================================================="
