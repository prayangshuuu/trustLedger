# TrustLedger lender dashboard (React + Vite + TypeScript)

Live view of risk, fairness and reach for lenders and judges. All numbers come from the API.

| Page | What it shows | Library |
|---|---|---|
| Overview | Applications, approval rate, on-time repayment rate, **Inclusion Lift**, bank rule vs TrustLedger gauges, fairness gate | Chart.js (gauges) |
| Score distribution | 25-point histogram, approved vs declined | Recharts |
| Fairness | Approval/TPR/FPR by group, gaps vs the 0.05 line with PASS/FAIL, notebook before/after | Recharts |
| Division map | Approval rate per division on a Bangladesh map | D3 (`d3-geo`) + geoBoundaries GeoJSON (CC0) |
| Live feed | Latest 50 decisions with Bangla reasons, polling every 5 s | — |
| Applicant detail | Score, p vs threshold, SHAP reasons, features, fairness checks, agent trace + prompt versions | — |
| Reports | Fairness CSV, Inclusion CSV, print / save as PDF | — |

API-key login (`X-API-Key`, kept in sessionStorage), dark and light themes, responsive down to phone width.

```bash
npm install
cp .env.example .env            # VITE_API_BASE_URL
npm run dev                     # http://localhost:5173
npm test                        # vitest: data hooks + CSV export
npm run build && npx playwright install chromium && npm run e2e   # smoke test (API must be running)
node tests/screenshots.mjs      # regenerate docs/media/dashboard_*.png
```

Demo data: `make seed` (3 personas + 4,000 synthetic applicants generated with the notebook formulas).
Deploy: ships inside the `trustledger` Heroku app. The Node buildpack builds `dist/` and the FastAPI app serves it at `/`
(same origin, so no `VITE_API_BASE_URL` or CORS setup). See [`docs/deploy.md`](../../docs/deploy.md).
Production builds call the page's own origin; set `VITE_API_BASE_URL` only to point a build at another API.
