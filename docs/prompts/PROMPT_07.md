# Prompt 07 — Feature builder

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu
**Depends on:** Prompt 3, Prompt 6
**Report:** `docs/PROMPT7_REPORT.md`

## Goal
Convert parsed transactions into the 10 model features so real phone data feeds the trained model.

## Tasks
- `parsers/features.py`: from a list of `Transaction` (and optional OCR'd bills) compute: `monthly_inflow_bdt` (median monthly income inflow), `income_volatility` (coefficient of variation of monthly inflow), `months_on_wallet` (months between first and last transaction), `txn_per_month`, `bills_on_time` (bills paid by due date / bills seen; due date from OCR or a default day of month), `recharge_regularity` (1 − normalised std of days between recharges), `savings_ratio` (savings out / income in), `sends_money_home` (1 if remittance in ≥ 50% of months), `loan_to_income` (requested amount / monthly inflow).
- Users with < 3 months of history → wallet features `None` (model handles missing), flag `needs_bhorsha=True`.
- Clip every feature to the training ranges seen in `datasets/trustledger_synthetic_bd.csv` (compute and store ranges in `models/feature_ranges.json`).
- Endpoint `POST /parse/sms` (DEMO_MODE only) → transactions + features; `POST /features` → store a feature snapshot.
- Test: synthetic 12-month SMS history for Shathi → features close to her notebook profile → approved.

## Acceptance criteria
- Shathi's synthetic SMS history produces features that score her as approved
- Short history correctly sets `needs_bhorsha`
- Every feature formula has a unit test

## Out of scope
OCR.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT7_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 7 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
