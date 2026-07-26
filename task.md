# Active Task: Statistical Overhaul of `metrics_component_hybrid` Model

- **Status:** In Progress — Plan agreed & baseline backtested; ready for implementation.
- **Objective:** Implement 5-step statistical overhaul (Team multipliers, WLS+Ridge calibration, Negative Binomial goals conceded, Calibrated Bonus Softmax, and Start/Sub minutes mixture).
- **Acceptance Criteria:** `metrics_component_hybrid` model passes tests, backtests on GW1–38 show improved RMSE/Spearman correlation and reduced bias relative to baseline (`RMSE: 3.2230`, `Bias: +1.8220`).
- **Handoff Document:** [`docs/agents/handoff.md`](file:///Users/jubilee/fpl-jubilee-ascent/docs/agents/handoff.md)

## Work Packet (SFDBN)

- **Status:** Baseline backtested; 5-step plan finalized.
- **Files:** `models/metrics_component_hybrid.py`, `features/builder.py`, `commands/backtest.py`, `tests/test_metrics_component_hybrid.py`
- **Decisions:** Adopt WLS (weighted by minutes) + Ridge shrinkage; Negative Binomial for goals conceded; Dixon-Coles team multipliers in feature builder; +3/+2/+1 bonus tier allocation with calibrated temperature; 2-state minutes mixture model.
- **Blocked:** None.
- **Next:** Execute Step 1 (Team multipliers in `features/builder.py`) and Step 2 (WLS + Ridge in `models/metrics_component_hybrid.py`).

## Todo
- [x] Pull API bootstrap data & export CSV spreadsheets.
- [x] Run baseline backtest on `metrics_component_hybrid` (GW1–38).
- [x] Finalize 5-step statistical overhaul plan.
- [ ] Step 1: Implement Dixon-Coles team multipliers in `features/builder.py`.
- [ ] Step 2: Implement WLS & Ridge calibration in `models/metrics_component_hybrid.py`.
- [ ] Step 3: Implement Negative Binomial distribution for clean sheets & goals conceded.
- [ ] Step 4: Calibrate bonus Softmax temperature & +3/+2/+1 allocation.
- [ ] Step 5: Implement 2-state start/sub minutes mixture model.
- [ ] Run verification & comparison backtest against baseline.
