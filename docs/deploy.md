# Deploying TrustLedger

One repository, three deployables:

| Piece | Where | How |
|---|---|---|
| `trustledger-api` (FastAPI) | Heroku, `TL_ROLE=api` | `Procfile` → `infra/heroku/web.sh`; release phase `infra/heroku/release.sh` (Alembic, RAG ingest, demo seed) |
| `trustledger-mcp` (MCP streamable HTTP) | Heroku, `TL_ROLE=mcp` | same slug, `web.sh` starts `mcp_server` on `$PORT`, path `/mcp` |
| Lender dashboard | Vercel (`apps/dashboard`, `vercel.json`) | static build with `VITE_API_BASE_URL` |
| Borrower app | GitHub release | `flutter build apk --release` |

The Python buildpack installs from `uv.lock` (`.python-version` = 3.12) without the dev and notebook groups.
Model files ship in the slug (`models/`, ~2 MB), so nothing is downloaded at release.

## 1. Heroku apps (staging and production)

```bash
heroku login
for env in staging prod; do
  heroku create trustledger-api-$env --stack heroku-24
  heroku addons:create heroku-postgresql:essential-0 -a trustledger-api-$env   # pgvector is available on Heroku Postgres
  heroku addons:create heroku-redis:mini -a trustledger-api-$env
  heroku config:set -a trustledger-api-$env \
    TL_ROLE=api DEMO_MODE=true LLM_MODE=mock SEED_POPULATION=4000 \
    API_KEYS="$(openssl rand -hex 24),$(openssl rand -hex 24)" \
    SESSION_SECRET="$(openssl rand -hex 32)" \
    STORAGE_ENCRYPTION_KEY="$(uv run python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')" \
    CORS_ORIGINS=https://trustledger-dashboard.vercel.app
  heroku create trustledger-mcp-$env --stack heroku-24
  heroku config:set -a trustledger-mcp-$env TL_ROLE=mcp \
    TRUSTLEDGER_API_URL=https://trustledger-api-$env.herokuapp.com \
    TRUSTLEDGER_API_KEY=<one of the API_KEYS> MCP_API_KEYS="$(openssl rand -hex 24)"
done
git push https://git.heroku.com/trustledger-api-staging.git main
git push https://git.heroku.com/trustledger-mcp-staging.git main
```

Optional live AI: `heroku config:set LLM_MODE=live DEEPSEEK_API_KEY=... DEEPSEEK_OCR_URL=...`.
Optional object storage: `R2_ENDPOINT R2_ACCESS_KEY R2_SECRET_KEY R2_BUCKET`, then apply `infra/r2-lifecycle.json` to the bucket (30-day expiry).
Without R2 the API stores encrypted images on the dyno filesystem, which Heroku wipes on restart. That is fine for a demo.

Config vars:

| Var | api | mcp | Notes |
|---|---|---|---|
| `DATABASE_URL`, `REDIS_URL` | auto | – | add-ons |
| `TL_ROLE` | `api` | `mcp` | selects the process |
| `API_KEYS` | ✓ | – | lender, app and partner keys |
| `SESSION_SECRET`, `STORAGE_ENCRYPTION_KEY` | ✓ | – | secrets |
| `DEMO_MODE`, `SEED_ON_RELEASE`, `SEED_POPULATION` | ✓ | – | demo data on every release |
| `LLM_MODE`, `DEEPSEEK_*` | ✓ | – | mock if no key |
| `CORS_ORIGINS` | ✓ | – | dashboard URL(s) |
| `TRUSTLEDGER_API_URL`, `TRUSTLEDGER_API_KEY`, `MCP_API_KEYS` | – | ✓ | MCP → API |

Promote: `heroku pipelines:create trustledger -a trustledger-api-staging`, add prod, then `heroku pipelines:promote -a trustledger-api-staging`.

## 2. Dashboard on Vercel

```bash
cd apps/dashboard
npx vercel link
npx vercel env add VITE_API_BASE_URL production   # https://trustledger-api-prod.herokuapp.com
npx vercel --prod
```

## 3. Android APK

```bash
cd apps/mobile
flutter build apk --release \
  --dart-define=API_BASE_URL=https://trustledger-api-prod.herokuapp.com \
  --dart-define=API_KEY=<app key from API_KEYS>
gh release create v1.0.0 build/app/outputs/flutter-apk/app-release.apk --title "TrustLedger v1.0.0"
```

The default Flutter template signs `--release` builds with the debug key. That is fine for a sideloaded demo APK.
For Play Store distribution, add a keystore (`android/key.properties`).

## 4. Smoke test

```bash
infra/smoke.sh https://trustledger-api-prod.herokuapp.com <API_KEY> https://trustledger-mcp-prod.herokuapp.com
```

It runs Shathi's flow: health → personas → session → consents → `/apply` with 72 SMS (approved, Bangla reasons) → trace →
explanation → disburse → 3 repayments → limit upgrade → fairness and inclusion → MCP health and auth.

## Local stand-in (verified)

```bash
docker compose -f infra/docker-compose.yml --profile app up --build         # API + Temporal worker + infra
docker compose -f infra/docker-compose.yml --profile monitoring up -d       # Prometheus + Grafana
```
