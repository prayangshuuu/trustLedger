# Prompt 14 — Federated learning with Flower

> **Before you start:** read `PLAN_CONTEXT.md` fully, then `PROMPT.md` and every existing `docs/PROMPT*_REPORT.md`. Follow PLAN_CONTEXT.md §8 (how every prompt is run). If this prompt conflicts with PLAN_CONTEXT.md, PLAN_CONTEXT.md wins — note it in the report.

**Owner:** Prayangshu
**Depends on:** Prompt 3
**Report:** `docs/PROMPT14_REPORT.md`

## Goal
Turn the notebook's FedAvg simulation into a real Flower setup with differential privacy.

## Tasks
- `federated/`: Flower server (FedAvg with clipping + Gaussian noise / DP strategy), Flower client that trains the logistic scorer on local data, simulation runner with 8 clients split by division from `datasets/trustledger_synthetic_bd.csv`.
- Report test AUC per round and compare with the notebook's federated AUC and the central XGBoost AUC from `training_files/metrics.json`.
- Save the plot to `training_files/flower_federated.png` and weights to `models/flower_weights.npy`.
- Document how a phone client would participate (data stays on device, only clipped noisy updates leave).

## Acceptance criteria
- `uv run python -m federated.simulate` completes and reaches AUC within 0.02 of the notebook's federated AUC
- Plot and weights saved

## Out of scope
On-device mobile integration.

## When finished
1. Run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest` (plus any checks above) and fix failures. Skip a tool only if it isn't set up yet, and say so in the report.
2. Write `docs/PROMPT14_REPORT.md` using the template in PLAN_CONTEXT.md §9. Include real command output numbers, not estimates.
3. Tick Prompt 14 in `PROMPT.md`.
4. Commit: format :feat: fix: oneliner no description
