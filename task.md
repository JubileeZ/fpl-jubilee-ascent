# Active Task: Statistical Overhaul of `metrics_component_hybrid` Model

- **Status:** Complete — Overhaul, component attribution, & multi-stage bias calibration implemented (clean sheet bias reduced -45% to +0.0739 via unplayed rate fillna, defcon bias calibrated to +0.0020, overall MAE 1.2701, Spearman rank correlation +0.4042, 82/82 pytest passing).
- **Objective:** Implement 5-step event-level Empirical Bayes statistical overhaul, component bias attribution, and calibrate player minutes/availability.
- **Acceptance:** `metrics_component_hybrid` model passes tests, backtests on GW1–38 show improved RMSE/Spearman correlation and reduced bias relative to baseline, and `--component_breakdown` table outputs per-component error metrics.
- **ADR Document:** [`docs/adr/0007-event-level-empirical-bayes-projection-engine.md`](file:///home/jubileez/fpl-jubilee-ascent/docs/adr/0007-event-level-empirical-bayes-projection-engine.md)


## Work Packet (SFDBN)

- **Status:** Complete & verified.
- **Files:** `models/metrics_component_hybrid.py`, `features/builder.py`, `backtesting/metrics.py`, `commands/backtest.py`, `tests/test_component_attribution.py`
- **Decisions:** See [ADR 0007](file:///home/jubileez/fpl-jubilee-ascent/docs/adr/0007-event-level-empirical-bayes-projection-engine.md).
- **Blocked:** None.
- **Next:** Commit changes to main.

## Todo
- [x] Pull API bootstrap data & export CSV spreadsheets.
- [x] Run baseline backtest on `metrics_component_hybrid` (GW1–38).
- [x] Finalize 5-step statistical overhaul plan & ADR 0007.
- [x] Step 1: Implement Dixon-Coles team multipliers in `features/builder.py`.
- [x] Step 2: Implement Two-Stage Empirical Bayes GLM in `models/metrics_component_hybrid.py`.
- [x] Step 3: Implement Defcon Pearson chi-square dispersion ratio diagnostics.
- [x] Step 4: Implement minutes-aware team goal exposure & Negative Binomial conceded penalties.
- [x] Step 5: Implement 2-state starter/sub minutes mixture model & +3/+2/+1 bonus tier allocation.
- [x] Implement component prediction export and `--component_breakdown` CLI reporting.
- [x] Calibrate `n_starts_historical`, remove `exp_mins_start` floor, and gate `chance_of_playing` by status in `builder.py`.
- [x] Run verification & comparison backtest against baseline.
