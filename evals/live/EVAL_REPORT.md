# Live AI Pipeline & Model Validation Evaluation Report

**Cohort Size:** 20 synthetic applicants  
**Date:** 1795182139.4067206

## Executive Summary
| Metric | Result | Target | Status |
| :--- | :--- | :--- | :--- |
| **SMS Parsing F1** | `100.00%` | ≥ 90.0% | ✅ PASS |
| **OCR Field F1** | `100.00%` | ≥ 90.0% | ✅ PASS |
| **Decision Agreement** | `100.00%` | ≥ 95.0% | ✅ PASS |
| **Explanation Guard Violations** | `0` | 0 | ✅ PASS |
| **Avg Tokens / User** | `1,597` | < 50,000 | ✅ PASS |
| **Avg Cost / User** | `$0.00025` | < $0.05 | ✅ PASS |

## Per-Feature Mean Absolute Error (MAE)
| Feature | MAE |
| :--- | :--- |
| `monthly_inflow_bdt` | `0.0000` |
| `income_volatility` | `0.0000` |
| `months_on_wallet` | `0.0000` |
| `txn_per_month` | `0.0000` |
| `bills_on_time` | `0.0000` |
| `recharge_regularity` | `0.0000` |
| `savings_ratio` | `0.0000` |
| `sends_money_home` | `0.0000` |
| `bhorsha_score` | `0.0000` |
| `loan_to_income` | `0.0000` |

## Token and Cost Economics
- **Total Pipeline Tokens:** 31,944
- **Total Pipeline Cost:** $0.0050 USD
- **Average Cost per Decision:** $0.00025 USD
