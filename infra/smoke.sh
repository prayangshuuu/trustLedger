#!/usr/bin/env bash
# Shathi's demo flow against a deployed (or local) TrustLedger API.
#   infra/smoke.sh https://trustledger-<id>.herokuapp.com <API_KEY> [MCP_URL]
set -euo pipefail
BASE="${1:-http://localhost:8000}"; KEY="${2:-${API_KEY:-dev-key}}"; MCP="${3:-${MCP_URL:-}}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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

echo "TrustLedger smoke test → $BASE"
[ "$(req GET /health)" = 200 ] && [ "$(jq_ "d['status']")" = ok ] && ok "health ($(jq_ "d['database']"))" || fail health
[ "$(req GET /version)" = 200 ] && ok "version model=$(jq_ "d['model_version']")" || fail version
[ "$(req GET /demo/personas)" = 200 ] || fail "demo personas (DEMO_MODE=true and seeded?)"
UID_="$(jq_ "[p['user_id'] for p in d if p['key']=='shathi'][0]")"; ok "Shathi = $UID_"
body=$(printf '{"user_id":"%s"}' "$UID_")
[ "$(req POST /auth/session "$body")" = 200 ] || fail session
AUTH="Authorization: Bearer $(jq_ "d['token']")"; ok "borrower session"
for s in sms bills recharge ocr; do
  body=$(printf '{"user_id":"%s","source":"%s"}' "$UID_" "$s")
  [ "$(req POST /consent "$body" "$AUTH")" = 201 ] || fail "consent $s"
done; ok "consent sms, bills, recharge, ocr"
[ "$(req GET /me "" "$AUTH")" = 200 ] && ok "profile consents $(jq_ "d['consents']")" || fail me
python3 -c "import json;print(json.dumps({'user_id':'$UID_','amount_bdt':56000,'sms':json.load(open('$ROOT/apps/mobile/assets/demo/shathi_sms.json'))['sms']}))" > "$TMP/apply.json"
[ "$(req POST /apply "@$TMP/apply.json")" = 200 ] || fail "apply $(cat "$TMP/body")"
STATUS="$(jq_ "d['status']")"; SCORE="$(jq_ "d['decision']['score']")"
[ "$STATUS" = approved ] || fail "Shathi status $STATUS"
[ "$SCORE" -ge 650 ] || fail "score $SCORE"
[ "$(jq_ "len(d['decision']['good'])")" -ge 1 ] || fail "no Bangla reasons"
ok "apply: $STATUS, score $SCORE, reasons: $(jq_ "', '.join(d['decision']['good'])")"
DEC="$(jq_ "d['decision']['decision_id']")"; APP="$(jq_ "d['decision']['application_id']")"; TRACE="$(jq_ "d['trace_id']")"
[ "$(req GET "/traces/$TRACE")" = 200 ] && ok "trace $TRACE ($(jq_ "len(d['details']['nodes'])") nodes)" || fail trace
[ "$(req GET "/explain/$DEC")" = 200 ] && ok "explain decision" || fail explain
[ "$(req POST "/loans/$APP/disburse")" = 200 ] && ok "disbursed" || fail disburse
for i in 1 2 3; do
  body=$(printf '{"amount_bdt":18667,"on_time":true,"idempotency_key":"smoke-%s"}' "$i")
  [ "$(req POST "/loans/$APP/repayments" "$body")" = 200 ] || fail "repay $i"
done; ok "3 on-time repayments"
[ "$(req POST "/loans/$APP/limit-upgrade" '{}')" = 200 ] && ok "limit → $(jq_ "d['credit_limit_bdt']") BDT" || fail upgrade
[ "$(req GET /fairness/report)" = 200 ] && ok "fairness gap $(jq_ "d['approval_rate_gap']") ok=$(jq_ "d['fairness_ok']")" || fail fairness
[ "$(req GET /inclusion-lift)" = 200 ] && ok "inclusion: newly included $(jq_ "d['newly_included_rate']")" || fail inclusion
if [ -n "$MCP" ]; then
  code=$(curl -s -o /dev/null -w '%{http_code}' "$MCP/health"); [ "$code" = 200 ] && ok "MCP health" || fail "MCP health $code"
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$MCP/mcp" -H 'Content-Type: application/json' -d '{}'); [ "$code" = 401 ] && ok "MCP rejects missing key" || fail "MCP auth $code"
fi
echo "PASS ($pass checks)"
