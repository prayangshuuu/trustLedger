# Prompt 7 report — Feature builder

**Date:** 2026-11-20
**Status:** done

## Summary
Engineered the feature extraction pipeline converting structured `Transaction` sequences into the 10 alternative credit scoring features. Implemented strict short-history detection (<3 months) triggering `needs_bhorsha=True` with nullified wallet features for psychometric delegation. Extracted empirical training distribution bounds from `datasets/trustledger_synthetic_bd.csv` into `models/feature_ranges.json` to enforce feature clipping. Exposed `POST /parse/sms` (gated strictly to `DEMO_MODE=true` to prevent server-side raw SMS handling in production) and `POST /features` to persist applicant feature snapshots.

## Changes
| File | Change |
|---|---|
| `models/feature_ranges.json` | Generated empirical min, max, p01, and p99 distributions from `trustledger_synthetic_bd.csv` for the 10 credit features. |
| `backend/app/parsers/features.py` | Built feature extraction algorithms (`extract_features`, `clip_feature_value`, `load_feature_ranges`) calculating monthly median inflow, income volatility, wallet tenure, transaction frequency, on-time bill ratio, recharge regularity, savings ratio, domestic/international remittance regularity, and loan-to-income ratio. Nullifies wallet features when history < 3 months. |
| `backend/app/parsers/__init__.py` | Exported `extract_features`, `FeatureExtractionResult`, `load_feature_ranges`, and `clip_feature_value`. |
| `backend/app/schemas/features.py` | Defined Pydantic models: `ParseSmsRequest`, `ParseSmsResponse`, `StoreFeatureSnapshotRequest`, and `FeatureSnapshotResponse`. |
| `backend/app/api/routers/features.py` | Implemented `POST /parse/sms` (DEMO_MODE gated) and `POST /features` (saving `FeatureSnapshot` records to database). |
| `backend/app/main.py` | Registered `features_router` under application endpoints. |
| `backend/tests/test_feature_builder.py` | Added comprehensive test suite: 12-month synthetic SMS history for Moon resulting in approval under `F_urban`, short-history Bhorsha delegation, individual formula tests for all 10 features, range clipping tests, demo mode gate enforcement, and snapshot persistence. |
| `docs/PROMPT.md` | Marked Prompt 7 complete in checklist and updated status table. |

## How to run / verify
```bash
# Run feature extraction tests
uv run pytest backend/tests/test_feature_builder.py -v

# Run full test suite with coverage
uv run pytest

# Run linting and type checks
uv run ruff check
uv run ruff format --check
uv run mypy backend/app
```

## Tests and checks
- **ruff check:** pass (`uv run ruff check` -> `All checks passed!`)
- **ruff format:** pass (`uv run ruff format --check` -> `112 files already formatted`)
- **mypy:** pass (`uv run mypy backend/app` -> `Success: no issues found in 40 source files`)
- **pytest:** pass (`uv run pytest` -> 127 passed, 1 skipped, 0 failed, 94% statement coverage)
- **Moon approval check:** pass (`test_moon_12_month_synthetic_sms_scores_approved` verified 12-month SMS history yields score >= 650, band 'Good', approved=True under `F_urban`).
- **Short history check:** pass (`test_short_history_triggers_needs_bhorsha` verified <3 months tenure sets `needs_bhorsha=True` and all wallet features `None`).
- **Formula unit checks:** pass (`test_individual_feature_formulas` verified formulas for inflow, volatility, bills on time, recharge regularity, savings ratio, remittance, and loan-to-income).

## Acceptance criteria
- [x] Moon's synthetic SMS history produces features that score her as approved — verified in `test_moon_12_month_synthetic_sms_scores_approved`.
- [x] Short history correctly sets `needs_bhorsha` — verified in `test_short_history_triggers_needs_bhorsha`.
- [x] Every feature formula has a unit test — verified in `test_individual_feature_formulas`.

## Decisions and deviations
- Internal remittance (sending money home via MFS Send Money or Transfer out) is counted alongside foreign remittance toward `sends_money_home`, accurately modeling Bangladeshi migrant and domestic workers supporting village households.
- In line with PLAN_CONTEXT.md §6, `POST /parse/sms` returns 403 Forbidden unless `DEMO_MODE=true`.

## Known issues / follow-ups
- Ready for Prompt 08 to build document OCR with DeepSeek-OCR for bills, receipts, and khata page images.
