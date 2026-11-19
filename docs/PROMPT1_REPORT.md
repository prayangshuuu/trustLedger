# Prompt 1 report — Repository audit and baseline

**Date:** 2026-11-20  
**Status:** done  

## Summary
Completed an exhaustive repository audit and asset inventory, verifying Git LFS tracking across all benchmark datasets (totaling 6.16 GB) and confirming all data files are fully materialized. Verified the production machine learning model contract in `models/trustledger_meta.json` against `PLAN_CONTEXT.md` §2 with zero discrepancies, and verified offline scoring on the Shathi persona (`p_repay` = 0.934, score = 691, approved under `F_urban`). Established reproducible dependency management with `uv`, adding `scikit-learn`, `notebook`, `ruff`, and `pytest` to `pyproject.toml`, configured `.env.example` with all 14 required environment variables, and secured `.gitignore` to prevent secret leakage.

## Changes
| File | Change |
|---|---|
| `.env.example` | Created template defining all 14 required environment variables from `PLAN_CONTEXT.md` §7 with empty values and descriptive comments. |
| `.gitignore` | Added `.env`, `.env.*`, and `!.env.example` exclusion rules, along with test and linter cache directories (`.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`). |
| `pyproject.toml` | Added `scikit-learn>=1.9.1` and `notebook` to dependencies; added `ruff>=0.5.0` and `pytest>=8.0.0` to dev dependency group; configured `[tool.ruff]` and `[tool.pytest.ini_options]`. |
| `uv.lock` | Updated deterministic lockfile resolving 119 packages for the Python 3.12 environment. |
| `docs/PROMPT1_REPORT.md` | Created Prompt 1 audit and baseline report. |
| `docs/PROMPT.md` | Marked Prompt 1 complete and updated prompt tracking status table. |

## How to run / verify
Commands a teammate can paste to reproduce the baseline checks and scoring:

```bash
# 1. Synchronize virtual environment with uv
uv sync

# 2. Run linter and formatting checks
uv run ruff check .
uv run ruff format --check .

# 3. Verify Git LFS tracking and materialized files
git lfs ls-files
ls -lh datasets/

# 4. Verify model scoring on Shathi benchmark persona
.venv/bin/python -c '
import json, numpy as np, pandas as pd, xgboost as xgb

with open("models/trustledger_meta.json") as f:
    meta = json.load(f)

FEATURES = meta["features"]
model = xgb.XGBClassifier()
model.load_model("models/trustledger_xgb.json")

shathi = {
    "monthly_inflow_bdt": 14000,
    "income_volatility": 0.10,
    "months_on_wallet": 30,
    "txn_per_month": 18,
    "bills_on_time": 0.97,
    "recharge_regularity": 0.90,
    "savings_ratio": 0.04,
    "sends_money_home": 1,
    "bhorsha_score": np.nan,
    "loan_to_income": 4.0
}
x = pd.DataFrame([shathi])[FEATURES].astype(float)
p = float(model.predict_proba(x)[0, 1])
scale = meta["score_scale"]
odds = (p / (1.0 - p)) / 4.0
score_raw = scale["points_at_4_to_1"] + (scale["points_to_double_odds"] / np.log(2)) * np.log(odds)
score = int(np.clip(round(score_raw), scale["range"][0], scale["range"][1]))
thr = meta["group_thresholds"]["F_urban"]
approved = bool(p >= thr)

print(json.dumps({
    "p_repay": round(p, 6),
    "odds": round(odds, 6),
    "score": score,
    "F_urban_threshold": round(thr, 6),
    "approved": approved
}, indent=2))
'

# 5. Verify .env exclusion in git
touch .env && git status --porcelain | grep "^?? .env$" || echo ".env correctly ignored"
rm -f .env
```

## Tests and checks
- **ruff check:** pass (`uv run ruff check .` -> `All checks passed!`)
- **ruff format:** pass (`uv run ruff format --check .` -> `24 files already formatted`)
- **mypy:** skipped (not yet installed; backend application directory `backend/app` scheduled for creation in Prompt 2)
- **pytest:** pass with 0 collected (`uv run pytest` -> `collected 0 items`, test suite to be created in Prompt 2)
- **Git LFS verification:** pass (12 files tracked via Git LFS, 6,141,677,047 bytes, all confirmed as real data files on disk, not pointer stubs)
- **Gitignore verification:** pass (`.env` and `.env.*` ignored; `.env.example` tracked)

## Acceptance criteria
- [x] `uv sync` works from a fresh clone — verified, locks 119 packages cleanly on Python 3.12.
- [x] Meta contract verified (or mismatches listed) — verified 10/10 features, float threshold, 4 demographic group thresholds, score scaling parameters, 10/10 dual Bangla reasons, and 7 actionable Bangla tips with 0 contract mismatches.
- [x] Shathi scored with the saved model, numbers in the report — verified `p_repay` = 0.933661 (~0.934), score = 691 (Good band [650–749]), approved (`p >= 0.717315`).
- [x] Baseline metrics table in the report — comprehensive metrics extracted from `training_files/metrics.json` documented below.
- [x] `.env.example` exists and `.env` is git-ignored — `.env.example` created with all 14 variables and `.gitignore` updated and tested.

## Audit and Baseline Details

### 1. Repository Inventory & File Sizes

Total top-level entries: 15 items (9 files, 6 directories).

| Entry | Type | Git Tracking | Size (Bytes) | Role & Description |
|---|---|---|---|---|
| `.git/` | directory | Git internal | 416 B | Git repository metadata, hooks, and Git LFS objects. |
| `.gitattributes` | file | Tracked | 199 B | Git LFS configuration declaring filter/merge rules for datasets > 100 MB. |
| `.gitignore` | file | Tracked | 161 B | Excludes virtualenvs, cache files, OS artifacts, and secrets (`.env`, `.env.*`). |
| `.env.example` | file | Tracked | 1,848 B | Environment variable specification template covering all 14 required keys. |
| `.idea/` | directory | Ignored | 288 B | JetBrains IDE project settings. |
| `.venv/` | directory | Ignored | 320 B | Python 3.12 virtual environment managed by `uv`. |
| `README.md` | file | Tracked | 7,028 B | Primary project overview, architecture diagram, and competition problem framing. |
| `datasets/` | directory | Tracked | 256 B | Raw and synthetic datasets (15 files, 6,156,534,681 bytes / 6.16 GB total). |
| `docs/` | directory | Tracked | 160 B | Documentation, architectural specs (`PLAN_CONTEXT.md`), and prompt specs (`docs/prompts/`). |
| `models/` | directory | Tracked | 256 B | Production model artifacts (`trustledger_xgb.json`, `trustledger_meta.json`, `federated_weights.npy`). |
| `pyproject.toml` | file | Tracked | 563 B | PEP 621 project configuration, dependencies, and tool settings (`ruff`, `pytest`). |
| `requirements.txt` | file | Tracked | 120 B | Legacy pip dependency freeze. |
| `training_files/` | directory | Tracked | 448 B | Visual training outputs (`*.png`) and serialized evaluation benchmarks (`metrics.json`). |
| `trustLedger_model_training.ipynb` | file | Tracked | 600,592 B | End-to-end model exploration, synthetic data generation, and training notebook. |
| `uv.lock` | file | Tracked | 291,933 B | Deterministic package lockfile. |

### 2. Datasets & Git LFS Audit

`datasets/` contains 15 total files across 2 directories with a total disk footprint of **6,156,534,681 bytes** (~5.73 GiB / 6.16 GB).

| File Path | Exact Bytes | Decimal Size | Git LFS Status | Role & Contents |
|---|---|---|---|---|
| `datasets/Findex_Microdata_2025_updateBangladesh.csv` | 360,603 | 360.6 kB | Git Blob | World Bank 2025 Global Findex survey microdata for Bangladesh financial inclusion baseline. |
| `datasets/LCDataDictionary.xlsx` | 23,582 | 23.6 kB | Git Blob | LendingClub attribute data dictionary. |
| `datasets/accepted_2007_to_2018Q4.csv` | 1,675,133,810 | 1.68 GB | Git LFS | LendingClub historical accepted loan applications (2007–2018Q4). |
| `datasets/rejected_2007_to_2018Q4.csv` | 1,782,281,620 | 1.78 GB | Git LFS | LendingClub historical rejected loan applications (2007–2018Q4). |
| `datasets/trustledger_synthetic_bd.csv` | 14,473,449 | 14.5 MB | Git Blob | Synthetic Bangladesh mobile wallet and micro-loan borrower dataset (100k records). |
| `datasets/home-credit-default-risk/HomeCredit_columns_description.csv` | 37,383 | 37.4 kB | Git LFS | Home Credit feature documentation. |
| `datasets/home-credit-default-risk/POS_CASH_balance.csv` | 392,703,158 | 392.7 MB | Git LFS | Monthly POS and cash loan payment history snapshots. |
| `datasets/home-credit-default-risk/application_test.csv` | 26,567,651 | 26.6 MB | Git LFS | Home Credit test evaluation split. |
| `datasets/home-credit-default-risk/application_train.csv` | 166,133,370 | 166.1 MB | Git LFS | Home Credit training split with loan default ground truth. |
| `datasets/home-credit-default-risk/bureau.csv` | 170,016,717 | 170.0 MB | Git LFS | Historical credit bureau records from other financial institutions. |
| `datasets/home-credit-default-risk/bureau_balance.csv` | 375,592,889 | 375.6 MB | Git LFS | Monthly credit bureau balance records. |
| `datasets/home-credit-default-risk/credit_card_balance.csv` | 424,582,605 | 424.6 MB | Git LFS | Historical credit card balance snapshots. |
| `datasets/home-credit-default-risk/installments_payments.csv` | 723,118,349 | 723.1 MB | Git LFS | Repayment schedule and payment timeliness data. |
| `datasets/home-credit-default-risk/previous_application.csv` | 404,973,293 | 405.0 MB | Git LFS | Past loan applications within Home Credit. |
| `datasets/home-credit-default-risk/sample_submission.csv` | 536,202 | 536.2 kB | Git LFS | Kaggle benchmark submission format. |

**Git LFS Status:**
- Filter rules in `.gitattributes`:
  - `datasets/home-credit-default-risk/*.csv filter=lfs diff=lfs merge=lfs -text`
  - `datasets/*_2007_to_2018Q4.csv filter=lfs diff=lfs merge=lfs -text`
- Exactly 12 files are tracked by Git LFS (totaling 6,141,677,047 bytes).
- All 12 files verified to be complete on-disk datasets, not Git LFS text pointer stubs.

### 3. Model Contract Verification (`models/trustledger_meta.json`)

The metadata contract was verified against `PLAN_CONTEXT.md` §2:

1. **Features List & Order:** Exactly 10 features matching order 1-to-1:
   - `monthly_inflow_bdt`, `income_volatility`, `months_on_wallet`, `txn_per_month`, `bills_on_time`, `recharge_regularity`, `savings_ratio`, `sends_money_home`, `bhorsha_score`, `loan_to_income`.
2. **Global Threshold:** Value is `0.7050021886825562` (float).
3. **Group Calibrated Thresholds:** Demographic parity thresholds for 4 groups:
   - `F_rural`: `0.6848993015289307`
   - `F_urban`: `0.7173145866394043`
   - `M_rural`: `0.6861969936639071`
   - `M_urban`: `0.7448047395795584`
4. **Score Scale:**
   - `points_at_4_to_1`: `600`
   - `points_to_double_odds`: `50`
   - `range`: `[300, 900]`
5. **Bangla Reasons:** 10/10 features mapped to `[good, bad]` Bangla strings:
   - `monthly_inflow_bdt`: `["মাসিক আয় ভালো", "মাসিক আয় কম"]`
   - `income_volatility`: `["আয় স্থিতিশীল", "আয় অনিয়মিত"]`
   - `months_on_wallet`: `["দীর্ঘ ওয়ালেট ইতিহাস", "ওয়ালেট ইতিহাস কম"]`
   - `txn_per_month`: `["নিয়মিত লেনদেন", "লেনদেন কম"]`
   - `bills_on_time`: `["বিল সময়মতো পরিশোধ", "বিল পরিশোধে দেরি"]`
   - `recharge_regularity`: `["নিয়মিত মোবাইল রিচার্জ", "রিচার্জ অনিয়মিত"]`
   - `savings_ratio`: `["নিয়মিত সঞ্চয়", "সঞ্চয় কম"]`
   - `sends_money_home`: `["নিয়মিত পরিবারে টাকা পাঠান", "রেমিট্যান্স অনিয়মিত"]`
   - `bhorsha_score`: `["ভরসা মূল্যায়নে ভালো ফল", "ভরসা মূল্যায়নে উন্নতি দরকার"]`
   - `loan_to_income`: `["ঋণের পরিমাণ আয়ের সাথে মানানসই", "ঋণের পরিমাণ আয়ের তুলনায় বেশি"]`
6. **Bangla Tips:** 7 actionable features contain borrower recommendations:
   - `bills_on_time`: `"প্রতিটি বিল নির্ধারিত তারিখের আগে পরিশোধ করুন।"`
   - `income_volatility`: `"আয়ের একটি নিয়মিত উৎস দেখাতে ওয়ালেটে আয় জমা রাখুন।"`
   - `savings_ratio`: `"প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।"`
   - `loan_to_income`: `"ছোট অঙ্কের ঋণ দিয়ে শুরু করুন, সময়মতো পরিশোধে সীমা বাড়বে।"`
   - `months_on_wallet`: `"নিয়মিত ওয়ালেট ব্যবহার চালিয়ে যান।"`
   - `recharge_regularity`: `"নিয়মিত সময়ে মোবাইল রিচার্জ করুন।"`
   - `bhorsha_score`: `"ভরসা মূল্যায়ন আবার দিন।"`
   - Note: `monthly_inflow_bdt`, `txn_per_month`, and `sends_money_home` intentionally omit tips as they represent external economic conditions rather than immediate borrower habits.
7. **Contract Mismatches:** 0 discrepancies.

### 4. Shathi Benchmark Scoring

Scoring executed against production artifact `models/trustledger_xgb.json` using Shathi profile:
- Profile: `monthly_inflow_bdt: 14000`, `income_volatility: 0.10`, `months_on_wallet: 30`, `txn_per_month: 18`, `bills_on_time: 0.97`, `recharge_regularity: 0.90`, `savings_ratio: 0.04`, `sends_money_home: 1`, `bhorsha_score: NaN`, `loan_to_income: 4.0`.
- Demographic Group: `F_urban`
- Calibrated Threshold (`F_urban`): `0.717315`
- Prediction `p_repay`: **0.933661** (0.934)
- Odds calculation: `(0.933661 / (1 - 0.933661)) / 4 = 3.518542`
- Score calculation: `600 + (50 / ln(2)) * ln(3.518542) = 690.7489` -> **691** (Good band [650–749])
- Decision: **Approved** (`p_repay >= 0.717315`)
- SHAP explanations:
  - Top Positive: `bills_on_time` (+0.938), `recharge_regularity` (+0.332)
  - Top Negative: `savings_ratio` (-0.144)
  - Actionable Tip: `"প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।"`

### 5. Baseline Evaluation Metrics (`training_files/metrics.json`)

#### TrustLedger Production Model (Synthetic Bangladesh Dataset, N=100,000)
| Metric | Value |
|---|---|
| Central Model ROC AUC | **0.7644** |
| Kolmogorov-Smirnov (KS) Statistic | **0.3901** |
| Brier Score Loss | **0.1680** |
| Approval Gap (Before Fair Calibration) | **0.100** |
| Approval Gap (After Fair Calibration) | **0.013** (87% reduction) |
| Equalized Odds Gap (Before Fair Calibration) | **0.097** |
| Equalized Odds Gap (After Fair Calibration) | **0.034** (65% reduction, well below 0.05 gate) |
| Bank Traditional Rule Approval Rate | **11.7%** (0.117) |
| TrustLedger Fair Approval Rate | **59.0%** (0.590) |
| Newly Included Population | **50.3%** (0.503) |
| Repay Rate (Bank Traditional Approved) | **80.6%** (0.806) |
| Repay Rate (Newly Included by TrustLedger) | **83.6%** (0.836) |
| Federated Learning ROC AUC (FedAvg, 8 clients) | **0.7574** (retains 99.1% of central AUC 0.7644) |

#### Real-World Validation Benchmarks
| Benchmark Dataset | Metric | Value | Notes |
|---|---|---|---|
| **Home Credit** | ROC AUC / KS / Brier | **0.7031 / 0.2988 / 0.0706** | Alternative data model |
| Home Credit | Bureau Only ROC AUC | All: **0.7254**, Unbanked: **0.6669** | Bureau performance degrades on unbanked |
| Home Credit | Alternative Data ROC AUC | All: **0.7031**, Unbanked: **0.6932** | Alternative data outperforms bureau on unbanked |
| Home Credit | Combined (Both) ROC AUC | All: **0.7601**, Unbanked: **0.7203** | Best discrimination |
| Home Credit | True Positive Rate (TPR) Gap | **0.402 -> 0.018** | After demographic calibration |
| **LendingClub** | Total Analyzed Loans | **422,373** | US benchmark |
| LendingClub | ROC AUC / KS / Brier | **0.7366 / 0.3474 / 0.1425** | Unsecured consumer lending |

#### Global Findex (World Bank Bangladesh Microdata 2021)
| Metric | Ownership / Inclusion Rate |
|---|---|
| All Adults Account Ownership | **43.3%** (0.433) |
| Women Account Ownership | **33.3%** (0.333) |
| Men Account Ownership | **53.5%** (0.535) |
| Gender Ownership Gap | **20.2%** |
| Borrowed (any source) | **70.3%** (0.703) |

## Decisions and deviations
- **Ruff notebook exclusion:** Added `extend-exclude = ["*.ipynb"]` to `[tool.ruff]` in `pyproject.toml`. Jupyter notebooks contain exploratory data science code and cell magic; production linting and formatting standards will be strictly enforced across all Python source modules (`backend/app`, `tests`, `mcp_server`, etc.) starting in Prompt 2.
- **Gitignore additions:** Extended `.gitignore` beyond `.env` and `.env.*` to also ignore `.pytest_cache/`, `.ruff_cache/`, and `.mypy_cache/` so development testing does not generate untracked artifacts.

## Known issues / follow-ups
- Backend code directory `backend/app/` does not exist yet (as expected per Prompt 1 Out of Scope); to be constructed in Prompt 2 along with full CI workflow, type checking setup (`mypy`), and test harnesses.
