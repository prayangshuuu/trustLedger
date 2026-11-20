# TrustLedger borrower web app (React)

React + Vite port of the Flutter borrower app (`apps/mobile`) for the web. Same screens, routes,
API calls, Bangla/English strings and session behaviour. The API serves the build at `/app/`.

```bash
npm install
npm run dev     # http://localhost:5174/app/ — proxies API calls to http://localhost:8000
npm run build   # dist/, picked up by the API (BORROWER_WEB_DIR=apps/borrower/dist)
```

Build-time env (see `.env.example`): `VITE_API_KEY` (X-API-Key, default `dev-key`) and
`VITE_API_BASE_URL` (empty = same origin). Strings live in `src/lib/l10n.ts`.

Routes: `/` welcome · `/consent` · `/connect` · `/review` · `/processing` · `/score` · `/reasons` ·
`/loan` · `/repay` · `/bhorsha` · `/settings`. Routes need a session (else `/`); score, reasons and
loan need a decision, repay needs an application (else `/connect`).
