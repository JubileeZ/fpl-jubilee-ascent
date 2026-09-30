# Projection Parity Invariant (CLI and Dashboard)

**Status**: Accepted (2026-10-01)

## Context
CLI Top-Picks Report (`commands.report` reading `data/club_def_prior_challenger.csv`) projected Haaland 83.20 xP GW6–15; Dashboard (`data/dashboard_data.json`) projected 96.14 xP.

Root cause:
1. CLI built features from operational target GW6 (`target_gw = resolve_horizon_start(processed_dir)`). `min(gameweek_id) == 6 >= 5` enabled `LearnedStartChallengerModel` dynamic starts (Haaland $P(\text{start}) \approx 0.857$).
2. Dashboard previously built features from GW1 (`SEASON_START_GW = 1`). `min(gameweek_id) == 1 < 5` silently gated off learned starts across GW1–38; fell back to nailed $P(\text{start}) = 1.0$ (93.6 min/match).
3. Dashboard frontend consumes `unfinished_gameweeks` (GW6–38) only; never renders or selects finished weeks.

## Decision
1. **Projection Parity Invariant**: For all unfinished Gameweeks $g \ge \text{target\_gw}$, projected points and minutes across all players in `data/{model_name}.csv` and `data/dashboard_data.json` strictly identical ($\Delta = 0.00$).
2. **Operational Horizon Origin**: Dashboard features and predictions start at `horizon_start = resolve_horizon_start(processed_dir)` through `SEASON_END_GW = 38`. Finished weeks not projected.
3. **Atomic Dual Emission**: `commands.export_dashboard` / `commands.dashboard` share canonical `run_dashboard_export()`. Single in-memory model predict pass emits both `data/{model_name}.csv` (`write_solver_projection_csvs`) and `dashboard_data.json` (`build_dashboard_dataset`).
4. **Defense-in-Depth Model Guard**: `models.base.resolve_asof_target_gw` advances `target_gw` past latest finished Gameweek in history if features start earlier.
5. **Continuous Verification**: Enforced via `tests/test_projection_parity.py` in standard pytest suite and pre-commit gate.
