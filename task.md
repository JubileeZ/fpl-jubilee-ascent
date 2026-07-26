# Active Task: Statistical Overhaul of `metrics_component_hybrid` Model

- **Status:** Complete — Overhaul implemented, verified via backtest & pytest (80/80 passed).
- **Objective:** Implement 5-step event-level Empirical Bayes statistical overhaul (`builder.py` team multipliers, Empirical Bayes attacking GLM, Pearson Defcon dispersion, minutes-aware team goal exposure NB, and +3/+2/+1 bonus tier allocation).
- **Acceptance:** `metrics_component_hybrid` model passes tests, backtests on GW1–38 show improved RMSE/Spearman correlation and reduced bias relative to baseline (`RMSE: 2.8020` vs `3.2230`, `Spearman: +0.2447` vs `-0.0023`, `Bias: +1.6064` vs `+1.8220`).
- **ADR Document:** [`docs/adr/0007-event-level-empirical-bayes-projection-engine.md`](file:///home/jubileez/fpl-jubilee-ascent/docs/adr/0007-event-level-empirical-bayes-projection-engine.md)

## Work Packet (SFDBN)

- **Status:** Complete & verified.
- **Files:** `models/metrics_component_hybrid.py`, `features/builder.py`, `commands/backtest.py`, `tests/test_metrics_component_hybrid.py`
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
- [x] Run verification & comparison backtest against baseline.
