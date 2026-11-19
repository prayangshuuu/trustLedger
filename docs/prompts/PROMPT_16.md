# Prompt 16 — Lender dashboard (React)

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Soniya (design) + Daniel
**Depends on:** Prompt 5, Prompt 11
**Report:** `docs/PROMPT16_REPORT.md`

## Goal
Give lenders and judges a live view of risk, fairness and reach.

## Tasks
- `apps/dashboard`: React + Vite + TypeScript.
- Pages: Overview (KPIs: applications, approval rate, repayment rate, **Inclusion Lift**), Score distribution (Recharts histogram), Fairness (approval/TPR/FPR by group, before/after, gap vs 0.05 line), Map of approvals by division (D3 + Bangladesh division GeoJSON), Live decision feed with reasons, Applicant detail (score, reasons, trace), Reports (export fairness + inclusion as CSV/PDF).
- Chart.js for the small gauge widgets. All data from the API, with a demo seed.
- API-key login. Responsive. Dark and light theme.
- vitest tests for data hooks; Playwright smoke test for the overview page.

## Acceptance criteria
- Dashboard shows live numbers after running the 3 personas through `/apply`
- Fairness page shows gaps and passes/fails against 0.05
- CSV export works

## Out of scope
Deployment.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT16_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 16 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
