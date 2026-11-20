# Prompt 23 — Web app polish, design parity QA and deployment

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Soniya + Daniel
**Depends on:** Prompt 16, Prompt 22
**Report:** `docs/PROMPT23_REPORT.md`

## Goal
Make the web app production-quality, prove it matches the mobile design, and put it online next to the dashboard.

## Tasks
- **Design parity tests:** golden (screenshot) tests for the key screens — welcome, consent, score reveal (final frame), reasons, loan offer, Bhorsha chat, settings — rendered at mobile size and at desktop size. Store goldens in `apps/mobile/test/goldens/`. CI fails on unexpected visual changes.
- **Shared design with the dashboard:** make `apps/dashboard` read `apps/design_tokens.json` (CSS variables generated at build time) so the lender dashboard and the borrower web app share colours, type and spacing. Remove any duplicated hard-coded values.
- **PWA:** manifest, icons, offline fallback page in Bangla, "Add to home screen" support.
- **Performance:** first load under 3 s on a mid-range phone over 4G (Lighthouse mobile run, results in the report); defer heavy assets; compress images; tree-shake icons; cache static assets.
- **Accessibility:** semantic labels on all interactive widgets, keyboard navigation and visible focus on desktop, contrast AA for text, screen-reader labels in Bangla and English, respects reduced-motion (score reveal animation shortens).
- **Cross-browser check:** Chrome, Safari (macOS + iOS), Firefox, Edge — checklist with screenshots in `docs/media/parity/`.
- **Deploy:** host the web build (Vercel, or Heroku static buildpack) at `app.<domain>` / a public URL; dashboard stays at its own URL; update CORS, `infra/smoke.sh` (adds a web smoke step with Playwright: open web app → run Moon → see score), README and `/docs` links.
- Update `PLAN_CONTEXT.md` §4 and §5 if anything changed, and note it in the report.

## Acceptance criteria
- Golden tests pass in CI for mobile and desktop sizes
- Lighthouse mobile: Performance ≥ 80, Accessibility ≥ 90 (scores in the report)
- Public web app URL works and is linked in README and `/docs`
- Web smoke test passes against production
- Dashboard and web app visibly use the same tokens (screenshot pair in the report)

## Out of scope
New features.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT23_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 23 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
