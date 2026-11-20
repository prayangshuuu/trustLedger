# Deploying TrustLedger

One repository, one Heroku app for the web, plus an optional MCP app and the APK:

| Piece | Where | How |
|---|---|---|
| `trustledger`: FastAPI API + lender dashboard | Heroku, `TL_ROLE=api` | Node buildpack builds `apps/dashboard` (root `package.json` → `heroku-postbuild`), Python buildpack installs the API. `Procfile` → `infra/heroku/web.sh`; release phase `infra/heroku/release.sh` (Alembic, RAG ingest, demo seed) |
| `trustledger-mcp` (optional, MCP streamable HTTP) | Heroku, `TL_ROLE=mcp` | same slug, `web.sh` starts `mcp_server` on `$PORT`, path `/mcp` |
| Borrower app | GitHub release | `flutter build apk --release` |

On `trustledger` the API serves the built dashboard from the same origin, so no CORS setup is needed:

| Path | Serves |
|---|---|
| `/`, `/distribution`, `/fairness`, `/map`, `/feed`, `/applicant/:id`, `/reports` | dashboard (React, client-side routes) |
| `/docs` | public docs site (`docs/site`) |
| `/api/docs`, `/api/redoc`, `/openapi.json` | Swagger, ReDoc, OpenAPI schema |
| everything else (`/health`, `/apply`, `/score`, ...) | the API, unchanged |

API routes always win, and unknown paths still get a JSON 404 (`backend/app/web.py`). The dashboard build uses the
page's own origin for API calls, so `VITE_API_BASE_URL` is not needed. The Python buildpack installs from `uv.lock`
(`.python-version` = 3.12) without the dev and notebook groups. Model files ship in the slug (`models/`, ~2 MB), so
nothing is downloaded at release. `.slugignore` drops the Flutter app and the notebook.

## 1. Heroku app

```bash
heroku login
heroku create trustledger --stack heroku-24
heroku buildpacks:add -a trustledger heroku/nodejs
heroku buildpacks:add -a trustledger heroku/python
heroku addons:create heroku-postgresql:essential-0 -a trustledger   # pgvector is available on Heroku Postgres
heroku addons:create heroku-redis:mini -a trustledger
heroku config:set -a trustledger \
  TL_ROLE=api DEMO_MODE=true LLM_MODE=mock SEED_POPULATION=4000 \
  API_KEYS="$(openssl rand -hex 24),$(openssl rand -hex 24)" \
  SESSION_SECRET="$(openssl rand -hex 32)" \
  STORAGE_ENCRYPTION_KEY="$(uv run python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')"
git push https://git.heroku.com/trustledger.git main
heroku open -a trustledger        # dashboard; sign in with one of the API_KEYS
```

Buildpack order matters: Node first (builds `apps/dashboard/dist`), then Python. The one-click `app.json` sets the same.

Optional MCP server, same code on a second app:

```bash
heroku create trustledger-mcp --stack heroku-24
heroku config:set -a trustledger-mcp TL_ROLE=mcp \
  TRUSTLEDGER_API_URL=https://trustledger-<id>.herokuapp.com \
  TRUSTLEDGER_API_KEY=<one of the API_KEYS> MCP_API_KEYS="$(openssl rand -hex 24)"
git push https://git.heroku.com/trustledger-mcp.git main
```

It stays a separate app because its tools call the API over HTTP with a blocking client, which would stall the API's
event loop if both ran in one process.

Optional live AI: `heroku config:set LLM_MODE=live DEEPSEEK_API_KEY=... DEEPSEEK_OCR_URL=...`.
Optional object storage: `R2_ENDPOINT R2_ACCESS_KEY R2_SECRET_KEY R2_BUCKET`, then apply `infra/r2-lifecycle.json` to the bucket (30-day expiry).
Without R2 the API stores encrypted images on the dyno filesystem, which Heroku wipes on restart. That is fine for a demo.

Config vars:

| Var | trustledger | trustledger-mcp | Notes |
|---|---|---|---|
| `DATABASE_URL`, `REDIS_URL` | auto | – | add-ons |
| `TL_ROLE` | `api` | `mcp` | selects the process |
| `API_KEYS` | ✓ | – | lender, app and partner keys |
| `SESSION_SECRET`, `STORAGE_ENCRYPTION_KEY` | ✓ | – | secrets |
| `DEMO_MODE`, `SEED_ON_RELEASE`, `SEED_POPULATION` | ✓ | – | demo data on every release |
| `LLM_MODE`, `DEEPSEEK_*` | ✓ | – | mock if no key |
| `CORS_ORIGINS` | optional | – | only for other browser origins; the bundled dashboard is same-origin |
| `DASHBOARD_DIR` | optional | – | defaults to `apps/dashboard/dist`; no build there means API only |
| `TRUSTLEDGER_API_URL`, `TRUSTLEDGER_API_KEY`, `MCP_API_KEYS` | – | ✓ | MCP → API |

Staging: create `trustledger-staging` the same way, then `heroku pipelines:create trustledger -a trustledger-staging`,
add `trustledger` as production and promote with `heroku pipelines:promote -a trustledger-staging`.

## 2. Dashboard

Nothing extra: it ships inside the `trustledger` app. To check the combined build locally:

```bash
(cd apps/dashboard && npm ci && npm run build)
make api                          # dashboard at http://localhost:8000, Swagger at /api/docs
```

## 3. Android APK

```bash
cd apps/mobile
flutter build apk --release \
  --dart-define=API_BASE_URL=https://trustledger-<id>.herokuapp.com \
  --dart-define=API_KEY=<app key from API_KEYS>
gh release create v1.0.0 build/app/outputs/flutter-apk/app-release.apk --title "TrustLedger v1.0.0"
```

The default Flutter template signs `--release` builds with the debug key. That is fine for a sideloaded demo APK.
For Play Store distribution, add a keystore (`android/key.properties`).

## 4. Smoke test

```bash
infra/smoke.sh https://trustledger-<id>.herokuapp.com <API_KEY> https://trustledger-mcp-<id>.herokuapp.com
```

It runs Moon's flow: health → personas → session → consents → `/apply` with 72 SMS (approved, Bangla reasons) → trace →
explanation → disburse → 3 repayments → limit upgrade → fairness and inclusion → MCP health and auth.

## Local stand-in (verified)

```bash
docker compose -f infra/docker-compose.yml --profile app up --build         # API + Temporal worker + infra
docker compose -f infra/docker-compose.yml --profile monitoring up -d       # Prometheus + Grafana
```
