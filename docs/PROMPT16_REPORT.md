# Prompt 16 report — Lender dashboard (React)

**Date:** 2026-11-20
**Status:** done

## Summary
`apps/dashboard` is a React 18 + Vite + TypeScript dashboard. It has Overview KPIs with Inclusion Lift, a Recharts score
histogram, a fairness page (live approval/TPR/FPR by group, gaps against a 0.05 reference line with PASS/FAIL, notebook
before/after), a D3 Bangladesh division map, a live decision feed with Bangla reasons, applicant detail (SHAP reasons,
features, fairness checks, agent trace with prompt versions) and Reports (CSV + print-to-PDF). Chart.js draws the gauges.
It has API-key login, dark/light themes and a responsive layout. Six new API endpoints serve the data.

## Changes
| File | Change |
|---|---|
| `backend/app/api/routers/stats.py` | `GET /stats/overview`, `/stats/score-distribution`, `/stats/divisions`, `/decisions`, `/decisions/{id}`, `/stats/model-metrics` |
| `backend/tests/test_api_stats.py` | 3 tests |
| `apps/dashboard/src/**` | Pages, `useApi` hook (polling, errors), typed client, CSV export, Chart.js gauge |
| `apps/dashboard/public/bd-divisions.geojson` | geoBoundaries BGD ADM1 (CC0), names normalised, rings rewound for d3 |
| `apps/dashboard/src/api/hooks.test.tsx`, `tests/overview.spec.ts` | vitest (4) + Playwright smoke |
| `apps/dashboard/tests/screenshots.mjs`, `docs/media/dashboard_*.png` | Screenshots (light + dark) |
| `apps/dashboard/vercel.json`, `.env.example`, `README.md` | Deploy config and docs |
| `Makefile`, `infra/Dockerfile` | Demo seed 4,000 applicants; image ships `training_files` for `/stats/model-metrics` |

## How to run / verify
```bash
DEMO_MODE=true API_KEYS=dev-key make seed && DEMO_MODE=true API_KEYS=dev-key make api
cd apps/dashboard && npm install && npm run dev
npm test && npm run build && npm run e2e
```

## Tests and checks
- Backend: ruff pass, mypy pass, pytest 182 passed / 1 skipped
- `tsc --noEmit`: pass · `vitest`: 4 passed · `vite build`: pass · Playwright smoke: 1 passed (API-key login → Overview KPIs → Fairness badge)
- Live numbers with personas + 4,000 synthetic applicants: approval 58.9%, bank rule 12.4%, newly included 49.5% (notebook: 59.0% / 11.7% / 50.3%), approval-rate gap **0.023 PASS**

## Acceptance criteria
- [x] Dashboard shows live numbers after running the personas through `/apply` (the overview polls; `/apply` decisions appear in the feed with traces)
- [x] Fairness page shows gaps and passes/fails against 0.05
- [x] CSV export works (fairness + inclusion; unit-tested CSV builder)

## Decisions and deviations
- **PDF export** uses the browser's print-to-PDF with a print stylesheet instead of a PDF library (no extra dependency, same result).
- **Live TPR/FPR** need outcomes for declined applicants too. Real lending never observes those, so the page shows live approval-rate parity and the notebook's held-out TPR/FPR (before/after).
- **Sample size:** with 200 synthetic applicants the live gap was noisy (0.157, a false FAIL). At 4,000 it is 0.023, so the demo seed uses 4,000. The page warns when any group has fewer than 500 decisions.

## Known issues / follow-ups
- The JS bundle is ~600 kB (Recharts + Chart.js + D3). Route-level code splitting would shrink it.
- Vercel deployment happens in Prompt 19.
