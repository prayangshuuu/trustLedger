# Prompt 15 — Borrower app (Flutter)

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Soniya (design) + Daniel
**Depends on:** Prompt 5, Prompt 9, Prompt 11
**Report:** `docs/PROMPT15_REPORT.md`

## Goal
Build the Bangla-first borrower app that tells Moon's story in the demo.

## Tasks
- Screens: welcome (Bangla/English toggle), consent per data source (clear Bangla copy), connect data (demo: paste/import sample SMS, upload bill photo), processing (agent steps shown), **score reveal** (animated meter 300–900, band), reasons (✅/⚠️ Bangla cards), tips, loan offer + accept, repayment progress + limit ladder, Bhorsha chat, settings (revoke consent, delete my data).
- Hind Siliguri font, TrustLedger palette (teal #14B8A6, navy #0F172A, gold #F5B942), generic wallet icons — no real bank/bKash/Nagad logos.
- API client with retries; offline-friendly error states in Bangla.
- Demo mode switch that loads the 3 personas.
- Widget tests for score reveal and consent; a short screen recording in `docs/media/`.

## Acceptance criteria
- Moon flow works on an Android emulator against the local API
- Zero-history persona completes Bhorsha in the app
- Delete-my-data works from settings

## Out of scope
Lender dashboard.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT15_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 15 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
