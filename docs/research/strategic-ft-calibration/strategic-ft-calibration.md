# Strategic Free Transfer Valuation Calibration (#229, #230, #231)

**Updated**: 2026-11-24T16:15:00+07:00  
**Data stamp**: `2025-26` (`S-1` Dev, seed `2024-25`), `2024-25` (`S-2` untuned Historical Filter, seed `2023-24`), and read-only pre-deadline `2026-27` `GW12–21` xP projections (no realized `2026-27` outcomes accessed)  
**Season**: Multi-season (`2025-26` `S-1` & `2024-25` `S-2`) + live `GW12–21` (`H=10`) sensitivity  
**Status**: Adopted (#231)  
**Purpose**: Empirical rolling-replay calibration and out-of-sample evaluation comparing unscaled flat Strategic Free Transfer plateaus (`#229`), `GW1–8` vs `GW9+` two-phase regimes (`#230`), and read-only live `GW12–21` (`H=10`) sensitivity (`#230`–`#231`, governed by Map `#227` and settled Q1–Q10 in `#228`).  
**Scope**: Unscaled static FT grid + Stage 2 certification (`#229`), upper-plateau static vs `GW1–8` two-phase certified shootout + live `GW12–21` sensitivity (`#230`–`#231`, `decay_base = 0.85`, diminishing ratio `1.0 : 0.6 : 0.3 : 0.1`, WC/FH + 5-FT overflow `gw_ft_hold` waivers); production implementation landed in `#231`; `2026-27` realized outcomes remain sealed.  
**Related**: [Map #227](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/227) · [Scope #228 (Closed)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/228) · [Grid Search #229 (Closed)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/229) · [Prototype #230 (Closed)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/230) · [Approval #231 (Closed)](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/231) · [ADR 0065](../../adr/0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md) · [ADR 0066](../../adr/0066-backtesting-and-promotion-foundation.md) · [ADR 0069](../../adr/0069-annual-rolling-validation-and-dual-tier-promotion.md) · [ADR 0071](../../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md)  
**Artifact**: [stage1_s1_grid.csv](stage1_s1_grid.csv) · [stage2_certified_finalists.csv](stage2_certified_finalists.csv) · [stage2_gw_trajectories.csv](stage2_gw_trajectories.csv) · [proto230_static_vs_twophase.csv](proto230_static_vs_twophase.csv) · [proto230_gw_trajectories.csv](proto230_gw_trajectories.csv) · [live_gw12_21_sensitivity.csv](live_gw12_21_sensitivity.csv) · [live_gw12_21_weekly.csv](live_gw12_21_weekly.csv) · [live_gw12_21_b2_cap_guard.csv](live_gw12_21_b2_cap_guard.csv) · [live_gw12_21_b2_cap_guard_weekly.csv](live_gw12_21_b2_cap_guard_weekly.csv) · [runner.py](runner.py) · [prototype_230.py](prototype_230.py)

## Sources

- **Primary (Code & Spec)**: [solver/scenarios.py](../../../solver/scenarios.py), [solver/solver.py](../../../solver/solver.py), [backtesting/rolling_replay.py](../../../backtesting/rolling_replay.py), [backtesting/native_transfer_solver.py](../../../backtesting/native_transfer_solver.py), [docs/adr/0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md](../../adr/0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md), [docs/adr/0066-backtesting-and-promotion-foundation.md](../../adr/0066-backtesting-and-promotion-foundation.md), [docs/adr/0069-annual-rolling-validation-and-dual-tier-promotion.md](../../adr/0069-annual-rolling-validation-and-dual-tier-promotion.md), [docs/adr/0071-certified-solver-budget-and-milp-qualification-calibration.md](../../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md).
- **Repository data**: `2025-26` Dev archive + admitted mirror (`docs/research/candidate-ideation/historical_replay_inputs.py`, seed `2024-25`); `2024-25` Historical Filter archive + kickoff amendments (`docs/research/candidate-ideation/s2_historical_replay_inputs.py`, seed `2023-24`, `position_id != 5`); Champion model `def_xg_shrink_challenger`.

**Source boundary**: All historical backtest results come strictly from the unsealed `2025-26` (`S-1`) and `2024-25` (`S-2`) evaluation pipelines; `2026-27` (`S`) realized outcomes were never accessed (`validate_calibration_season` enforces fail-closed exclusion). Calibration scripts isolated research runs under `docs/research/strategic-ft-calibration/` during `#229`–`#230`, and production `solver/` / `backtesting/` / ADR updates landed only after `#231` sign-off.

## Agent Prompt

```text
Full redo docs/research/strategic-ft-calibration/strategic-ft-calibration.md

1. Re-read settled governance in docs/adr/0065-0071 and issues #228/#231.
2. Run uv run pytest tests/test_strategic_ft_calibration_runner.py -v to verify hurdle math, FT waste accounting, WC/FH hold waiver, two-phase switching, live H=10 options, and sealed-season guards.
3. Execute #229 grid + Stage 2: uv run python docs/research/strategic-ft-calibration/runner.py --stage all --workers 6.
4. Execute #230 live + historical shootout: uv run python docs/research/strategic-ft-calibration/prototype_230.py --mode all --workers 5 and uv run python docs/research/strategic-ft-calibration/prototype_230.py --mode b2_guard.
5. Refresh all companion figures strictly from stage1_s1_grid.csv, stage2_certified_finalists.csv, proto230_static_vs_twophase.csv (total_net_points, delta_vs_baseline_net, q9_twophase_parsimony_pass), live_gw12_21_sensitivity.csv / live_gw12_21_weekly.csv, and live_gw12_21_b2_cap_guard.csv (horizon_egs, total_xp, wasted_fts, delay1_h10).
6. Remove all temporary caches under .tmp/agent/strategic-ft-calibration/ before finishing.
```

## Method

**Method type**: Empirical two-stage rolling-replay parameter sweep and out-of-sample cross-check.

**Inputs**:
- Neutral £100.0m opening GW1 ownership anchors and shared chip calendars for `2025-26` (`S-1`) and `2024-25` (`S-2`).
- Frozen Champion (`def_xg_shrink_challenger`) issue-time `6`-GW wide forecasts across `GW1–38` and settled native outcomes.

**Procedure**:
1. **Unscaled FT Formulation & WC/FH Parity**: Keep `effective_horizon_scale(H)` on one-off `hit_friction` and `gk_transfer_friction`, remove `scale(H)` from `ft_value_list` and `ft_hold_weights` across `1 <= H <= 10`, waive `gw_ft_hold` on Wildcard and Free Hit weeks inside `experimental_native_solve`, and lock `decay_base = 0.85` with diminishing ratios `1.0 : 0.6 : 0.3 : 0.1` (`ft_value_list = {2: v2, 3: 0.6*v2, 4: 0.3*v2, 5: 0.1*v2}`).
2. **Stage 1 Fast Screen (`2025-26` `S-1`)**: Sweep all `36` grid cells (`v2 ∈ {1.2, 1.6, 2.0, 2.4}` × `spare_ft_hold_weight ∈ {0.0, 0.08, 0.15}` × `ft_use_penalty ∈ {0.2, 0.4, 0.6}`) plus `baseline_adr0065` at `target_gap = 0.005` (`90s` per-deadline safety cap so `GW02` triple-captain lookahead completes cleanly). Record results in `stage1_s1_grid.csv`.
3. **Stage 2 Certified Confirmation (`2025-26` `S-1` & untuned `2024-25` `S-2`)**: Select top `5` hard-gate passers from Stage 1 by `(total_net_points, early_gw2_12_net, -total_paid_hits)` plus `baseline_adr0065`, and re-solve both seasons from `GW1–38` at `target_gap = 0.0`, `time_limit_seconds = 600.0`, `require_optimal = True`. Record summaries in `stage2_certified_finalists.csv` and weekly traces in `stage2_gw_trajectories.csv`.

**Definitions and assumptions**:
- **Hard gate 1 (`gate_hurdle_lt4`)**: Permanent `2 -> 1 FT` discounted xP hurdle `< 4.0` raw hit cost at both `H = 6` and `H = 10`, eliminating `H = 10` hit-cost inversion.
- **Hard gate 2 (`gate_zero_wasted_ft`)**: Zero 5-FT cap waste across all in-season non-chip deadlines `2 <= gw <= 37` (excluding `2025-26` GW15 AFCON topup).

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Total Net Points** | `total_net_points` | $\sum_{t=1}^{38} (\text{gross}_t + \text{cap\_inc}_t - \text{hit}_t)$ | Higher is better $\uparrow$ | Beat `baseline_adr0065` (`2,167` S-1 / `2,299` S-2) | Primary rolling 6-GW Strategic transfer replay estimand (`ADR 0066`). |
| **Early Net Points** | `early_gw2_12_net` | $\sum_{t=2}^{12} \text{net\_points}_t$ | Higher is better $\uparrow$ | $\ge$ baseline (`663` S-1 / `560` S-2) | Captures early-season high-variance transfer responsiveness window. |
| **Mid/Late Net Points** | `mid_late_gw13_38_net` | $\sum_{t=13}^{38} \text{net\_points}_t$ | Higher is better $\uparrow$ | $\ge$ baseline (`1,446` S-1 / `1,676` S-2) | Post-stabilization mid- and late-season cumulative net score. |
| **Permanent 2->1 FT Hurdle** | `perm_hurdle_h6` / `perm_hurdle_h10` | $V_2(H) + h_2 \sum_{k=0}^{H-2} \delta^k + p_{\text{use}}$ | Diagnostic ($< 4.0$ pre-`#231` ceiling; $< 6.60$ Strategic hit hurdle) | `< 6.60` (`H=10` hit hurdle) | Discounted xP threshold to drop permanently from `2` FT to `1` FT vs `-4` hit cost. |
| **1-GW Timing Delay Hurdle** | `delay1_h6` / `delay1_h10` | $(1 - \delta)\left(V_2(H) + \frac{h_2}{1-\delta} + p_{\text{use}}\right)$ | Diagnostic balance | Positive filter (`~0.5–0.9` xP) | Minimum 1-GW xP gain needed to justify accelerating a `2 -> 1` FT transfer by one week instead of waiting. |
| **Live 10-GW Expected GW Score** | `horizon_egs` ($\Sigma$ EGS) | $\sum_{t=12}^{21} \left(\text{EGS}(\text{lineup}_t, \text{bench}_t, \text{cap}_t) - 4 \cdot \text{hits}_t\right)$ | Higher is better $\uparrow$ *(projected)* | Beat baseline (`658.00`) | Forward `10`-GW live Transfer Plan Expected GW Score including auto-sub expected bench contributions. |
| **Live 10-GW Expected Points** | `total_xp` ($\Sigma$ xP) | Solver projected lineup `xP` sum across `GW12–21` (undiscounted) | Higher is better $\uparrow$ *(projected)* | Beat baseline (`649.83`) | Unweighted sum of starting lineup expected points over the live `10`-GW horizon. |
| **Q9 Two-Phase Parsimony Gate** | `q9_twophase_parsimony_pass` | $\Delta_{S-1}(\text{two-phase} - \text{best strict static}) \ge +10$ AND $\Delta_{S-2} > 0$ with hard gates passed | Boolean (`True` needed to adopt) | `True` (exceeded flat static bar) | Pre-committed parsimony bar protecting against early-season regime overfitting (`#228` Q9). |
| **Wasted Free Transfers** | `wasted_fts` | $\sum_{t=2}^{37} \max(0, \max(\text{ft}_t - n_t, 0) + 1 - 5)$ (non-WC/FH, non-AFCON-GW15) | Lower is better $\downarrow$ | `0` (hard gate) | Transfers lost at the 5-FT cap due to excessive hoarding. |
| **Average Pre-Transfer FT Bank** | `avg_ft_bank` | Mean pre-transfer FT over non-WC/FH deadlines `GW2–38` | Diagnostic band | `1.6–2.2` | Measures emergency buffer depth without drifting into 5-FT hoarding. |
| **Non-Chip Transfers / GW** | `non_chip_transfers_per_gw` | Total non-WC/FH transfers divided by non-WC/FH deadlines `GW2–38` | Diagnostic band | `0.85–1.05` | Weekly portfolio turnover rate (benchmark ~1 FT/GW). |
| **Mean 4-GW Realized Transfer Gain** | `mean_4gw_transfer_gain` | Mean $\sum_{t=g}^{\min(g+3,38)} (\text{pts}_{\text{in},t} - \text{pts}_{\text{out},t})$ across non-WC/FH transfers | Higher is better $\uparrow$ | Maximized (positive post-hits) | Realized 4-GW point gain per transfer executed. |

**Validation boundary**: Stage 1 (`0.5%` MIP gap) exhibits `±23–36` pt path sensitivity relative to exact certified `gap = 0.0` (e.g., `baseline_adr0065` screened at `2,190` in Stage 1 vs exact `2,167` in Stage 2). Only Stage 2 (`gap = 0.0`, `100% OPTIMAL`) results should inform final policy decisions.

## Project interpretation

### Decision rules

- Do **not** promote a Stage 1 `gap = 0.005` winner directly without Stage 2 `gap = 0.0` two-season certification.
- Retain `baseline_adr0065` only as the historical Stage 2 benchmark in companion CSVs (`2,167` `S-1` / `2,299` `S-2`), having superseded production defaults with Option B2 + 5-FT overflow guard under `#231`.

### Practical implications

- Removing `spare_ft_hold_weight` (`w_hold = 0.0`) drops `perm_hurdle` to `1.60–2.40` and pushes `avg_ft_bank` down to `1.26–1.44` (below the `1.6–2.2` target band), hurting cumulative `GW13–38` net points on both seasons.
- Conversely, raising the hurdle toward `~3.5–4.0` preserves `0` wasted FTs, restores 4-GW transfer efficiency (`mean_4gw_transfer_gain = 7.0714` in `2024-25` for `v2_2p0_h_0p15_u_0p4`), and beats baseline out-of-sample on `2024-25` (`+19` pts).

## Findings

### Evidence

1. **Stage 1 Screen (`2025-26` `S-1`, 37 configs at `gap = 0.005`, [stage1_s1_grid.csv](stage1_s1_grid.csv))**:
   - **`30/36` experimental cells passed both hard gates** (`gate_hurdle_lt4 = True` and `wasted_fts = 0`).
   - Six cells failed hard gates: four with `perm_hurdle_h10 >= 4.0` (`v2=2.0, w_hold=0.15, u=0.6` -> `4.14`; all three `v2=2.4, w_hold=0.15` cells -> `4.44–4.84`) and two with `wasted_fts = 1` (`v2=1.2, w_hold=0.15, u=0.6` and `v2=2.4, w_hold=0.0, u=0.6`). Notably, non-gate cell `v2_2p4_h_0p15_u_0p6` (`perm_h6 = 4.3351`, `perm_h10 = 4.8441`, `avg_ft_bank = 1.7576`) topped raw Stage 1 net points at `2,208` (`+18` vs Stage 1 baseline `2,190`).
   - Top 5 Stage 1 hard-gate passers advanced to Stage 2: `v2_1p2_h_0p00_u_0p4` (`2,170`), `v2_2p0_h_0p00_u_0p4` (`2,161`), `v2_1p6_h_0p00_u_0p2` (`2,160`), `v2_2p0_h_0p15_u_0p4` (`2,159`), and `v2_1p6_h_0p00_u_0p4` (`2,153`).

2. **Stage 2 Certified Verification (`gap = 0.0`, `600s` cap, `100% OPTIMAL` across all `456` GW solves, [stage2_certified_finalists.csv](stage2_certified_finalists.csv))**:
   - Frozen `baseline_adr0065` reproduced exact certified baseline totals on both seasons: **`2,167`** (`2025-26` `S-1`) and **`2,299`** (`2024-25` `S-2`), `0` wasted FTs.

| Config | `perm_h6` / `perm_h10` | `2025-26` Net ($\Delta$) | `2024-25` Net ($\Delta$) | 2-Season $\Delta$ | Early `GW2–12` (`S-1` / `S-2`) | Mid/Late `GW13–38` (`S-1` / `S-2`) | Avg FT Bank (`S-1` / `S-2`) | Tr/GW (`S-1` / `S-2`) | Paid Hits (`S-1` / `S-2`) | 4-GW Gain/Tr (`S-1` / `S-2`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`baseline_adr0065`** *(fails H10 gate)* | `5.15` / `6.72` | **`2,167`** (`0`) | `2,299` (`0`) | `0` | `663` / `560` | `1,446` / `1,676` | `1.94` / `1.53` | `1.24` / `1.24` | `5` / `8` | `3.66` / `3.48` |
| **`v2_2p0_h_0p15_u_0p4`** | `3.51` / `3.94` | `2,123` (`-44`) | **`2,318`** (`+19`) | **`-25`** | `663` / `531` | `1,402` / **`1,724`** | `1.48` / `1.41` | `1.21` / `1.24` | **`4`** / `9` | `3.63` / **`7.07`** |
| `v2_2p0_h_0p00_u_0p4` | `2.40` / `2.40` | `2,131` (`-36`) | `2,260` (`-39`) | `-75` | `662` / `550` | `1,411` / `1,647` | `1.33` / `1.38` | `1.27` / `1.26` | `5` / `10` | `1.57` / `3.60` |
| `v2_1p6_h_0p00_u_0p2` | `1.80` / `1.80` | `2,144` (`-23`) | `2,231` (`-68`) | `-91` | `662` / `540` | `1,424` / `1,628` | `1.30` / `1.26` | `1.27` / `1.15` | `7` / `6` | `3.50` / `4.41` |
| `v2_1p6_h_0p00_u_0p4` | `2.00` / `2.00` | `2,131` (`-36`) | `2,170` (`-129`) | `-165` | `662` / `541` | `1,411` / `1,566` | `1.33` / `1.44` | `1.27` / `1.15` | `5` / `5` | `1.57` / `3.64` |
| `v2_1p2_h_0p00_u_0p4` | `1.60` / `1.60` | `2,136` (`-31`) | `2,154` (`-145`) | `-176` | `662` / `541` | `1,416` / `1,550` | `1.39` / `1.38` | `1.24` / `1.15` | `5` / `5` | `2.83` / `3.33` |

*(Every Stage 2 trajectory recorded `wasted_fts = 0`, `time_limit_gws = 0`, `max_relative_gap = 0.0`, `gw1_net = 58` on `2025-26`, and `gw1_net = 63` on `2024-25`.)*

3. **Early-Season (`GW1–8`, `GW2–12`) vs. Mid/Late (`GW13–38`) Insights**:
   - **`GW1–8` is nearly invariant** across all 6 certified trajectories: exact **`498`** (`GW1–4 = 220`) for all 6 configs on `2025-26`, and `420–422` (`GW1–4 = 251–257`) on `2024-25`. Divergence occurs predominantly in **`GW13–38`** as cumulative squad trajectories and FT buffers compound.
   - **Out-of-sample gradient favors higher hurdle inside the `< 4.0` ceiling**: On untuned `2024-25`, cumulative net score climbs monotonically with `perm_hurdle` from `2,154` (`1.60`) -> `2,170` (`2.00`) -> `2,260` (`2.40`) -> **`2,318` (`3.51` / `3.94`, beating baseline by `+19` and doubling mean 4-GW transfer gain to `+7.07` pts/transfer)**.
   - **Turnover & FT bank behavior**: All certified configs had `0` wasted FTs and `non_chip_transfers_per_gw` of `1.15–1.27` (`~39–43` transfers over `33–34` non-chip GWs, slightly above the `0.85–1.05` diagnostic band); `avg_ft_bank` averaged `1.26–1.48` vs `1.94`/`1.53` on baseline.

4. **`#230` Certified Static Plateau vs. Two-Phase `GW1–8` Shootout (`gap = 0.0`, `600s` cap, `100% OPTIMAL` across all `14` runs / `532` GWs, [proto230_static_vs_twophase.csv](proto230_static_vs_twophase.csv))**:
   - **Q9 Parsimony Verdict — FAIL for two-phase `GW1–8` regime**: Neither two-phase schedule passed Q9 (`>= +10` over best strict static on `2025-26` `S-1` AND `> 0` on `2024-25` `S-2`, `q9_twophase_parsimony_pass = False`). Although `twophase_early_hi_late_mid` topped `2025-26` at `2,172` (`+5` vs baseline, `+49` vs `v2_2p0_h_0p15_u_0p4`), it dropped to `2,277` (`-22` vs baseline, `-48` vs best strict `< 4.0` static `2,325`) on untuned `2024-25` while taking `12` paid hits. Meanwhile `twophase_early_lo_late_hi` scored `2,123` / `2,239` (`-104` combined).

| Config | Regime | `perm_h6` / `perm_h10` | `< 4.0` Gate | `2025-26` Net ($\Delta$) | `2024-25` Net ($\Delta$) | 2-Season $\Delta$ | Early `GW2–12` (`S-1` / `S-2`) | Mid/Late `GW13–38` (`S-1` / `S-2`) | Avg FT Bank (`S-1` / `S-2`) | Paid Hits (`S-1` / `S-2`) | 4-GW Gain/Tr (`S-1` / `S-2`) | Q9 Pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `v2_2p4_h_0p15_u_0p6` | Static | `4.34` / `4.84` | False | `2,138` (`-29`) | **`2,336`** (`+37`) | **`+8`** | `663` / `531` | `1,417` / **`1,742`** | `1.85` / `1.53` | `4` / `9` | `3.64` / **`7.15`** | — |
| `baseline_adr0065` | Baseline | `5.15` / `6.72` | False | `2,167` (`0`) | `2,299` (`0`) | `0` | `663` / `560` | `1,446` / `1,676` | `1.94` / `1.53` | `5` / `8` | `3.66` / `3.48` | — |
| `twophase_early_hi_late_mid` | `GW1–8` (`3.51/3.94`) $\to$ `GW9+` (`2.99/3.22`) | `2.99` / `3.22` | True | **`2,172`** (`+5`) | `2,277` (`-22`) | `-17` | `662` / `550` | **`1,452`** / `1,664` | `1.48` / `1.38` | `5` / `12` | **`4.10`** / `3.80` | **False** |
| `v2_2p0_h_0p15_u_0p4` | Static | `3.51` / `3.94` | True | `2,123` (`-44`) | `2,318` (`+19`) | `-25` | `663` / `531` | `1,402` / `1,724` | `1.48` / `1.41` | `4` / `9` | `3.63` / `7.07` | — |
| `v2_2p4_h_0p08_u_0p6` | Static | `3.71` / `3.98` | True | `2,094` (`-73`) | `2,325` (`+26`) | `-47` | `663` / `531` | `1,373` / `1,731` | `1.52` / `1.41` | `5` / `9` | `3.03` / `7.07` | — |
| `v2_3p2_h_0p00_u_0p5` | Static (`w_hold=0`) | **`3.70` / `3.70`** | True | `2,094` (`-73`) | `2,325` (`+26`) | `-47` | `663` / `531` | `1,373` / `1,731` | `1.52` / `1.41` | `5` / `9` | `3.03` / `7.07` | — |
| `twophase_early_lo_late_hi` | `GW1–8` (`1.80`) $\to$ `GW9+` (`3.51/3.94`) | `3.51` / `3.94` | True | `2,123` (`-44`) | `2,239` (`-60`) | `-104` | `663` / `543` | `1,402` / `1,633` | `1.48` / `1.53` | `4` / `5` | `3.63` / `4.69` | **False** |

   - *(Note: `v2_3p2_h_0p00_u_0p5` and `v2_2p4_h_0p08_u_0p6` produced bit-for-bit identical 38-GW trajectories across both historical `H=6` seasons — `2,094` `S-1` / `2,325` `S-2` — because their `H=6` permanent hurdles `3.70` and `3.71` coincide closely, yet their behavior diverges cleanly at `H=10` below.)*

5. **`#230` Read-Only Live `GW12–21` (`H=10`, `180s` cap) Sensitivity ([live_gw12_21_sensitivity.csv](live_gw12_21_sensitivity.csv), [live_gw12_21_weekly.csv](live_gw12_21_weekly.csv))**:
   - Solved pre-deadline live `GW12–21` (`H=10`, starting `2 FT`, `£0.6m` ITB, `def_xg_shrink_challenger`, `data/solution.json` left untouched):

| Config | `perm_h10` (`delay1`) | `< 4.0` Gate | $\Sigma$ EGS | $\Sigma$ xP | `10`-GW Tr / Hits | Avg / Min / Max FT Bank | Wasted FTs (`5`-FT Cap) | MIP Gap (`180s`) | `GW12` Moves |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| `v2_3p2_h_0p00_u_0p5` | **`3.70`** (`0.555`) | True | **`667.59`** | **`659.54`** | `7 / 0` | `1.80 / 1 / 4` | **`0`** | **`0.34%`** | `+Van Hecke, Gomez / -F.Kadıoğlu, Palmer` |
| `v2_2p0_h_0p15_u_0p4` | `3.94` (`0.660`) | True | `660.73` | `652.61` | `7 / 0` | `3.00 / 1 / 5` | `2` (`GW19–20`) | `0.88%` | `+Vuskovic, Ødegaard / -F.Kadıoğlu, Palmer` |
| `v2_2p4_h_0p15_u_0p6` | `4.84` (`0.810`) | False | `658.58` | `650.18` | `5 / 0` | `3.10 / 1 / 5` | `2` (`GW20–21`) | `0.70%` | `+Van Hecke, Gomez / -F.Kadıoğlu, Palmer` |
| `baseline_adr0065` | `6.72` (`1.158`) | False | `658.00` | `649.83` | `7 / 0` | `2.80 / 1 / 4` | `0` | `1.75%` | `+Tarkowski, Dewsbury-Hall / -Egan, Palmer` |
| `v2_2p4_h_0p08_u_0p6` | `3.98` (`0.642`) | True | `655.31` | `647.99` | `6 / 0` | `3.00 / 1 / 5` | `1` (`GW19`) | `1.30%` | `+Vuskovic, Ahoka / -F.Kadıoğlu, Palmer` |

   - **Root-cause finding on live `H=10` FT hoarding**: Every experimental config with `spare_ft_hold_weight > 0` (`0.08`, `0.15`) accumulated to `5 FT` by `GW18–20` and wasted **`1–2` FTs** into the 5-FT cap because `gw_ft_hold` awards recurring weekly credit on `fts_state[w+1, 5]` even when incoming weekly accrual overflows the 5-FT cap. On unscaled `w_hold > 0` at `H=10` (unlike `baseline_adr0065`, whose `ft_hold_weights` was shrunk by `1 / 1.4731`), holding at `4–5 FT` becomes profitable enough to sit idle (`avg_ft_bank = 3.00–3.10`) instead of spending down FTs before overflowing. Only **`v2_3p2_h_0p00_u_0p5`** (`w_hold = 0.0`, horizon-invariant `perm = 3.70`) kept `0` wasted FTs, stayed centered in the `1.6–2.2` bank guardrail (`avg_ft_bank = 1.80`), beat baseline by **`+9.59` EGS / `+9.71` xP**, and achieved the tightest live MIP gap (`0.34%`).

### Alternatives

- None of the four `w_hold = 0.0` finalists reached baseline on either season (`-75` to `-176` combined).
- Notice the structural gap tested in `#229`: `v2 ∈ {1.2..2.4}` + `w_hold ∈ {0.0, 0.08, 0.15}` left two promising upper-plateau regimes untested at Stage 2 certified precision:
  1. Higher `ft_use_penalty` / `w_hold = 0.08` upper cells just under `perm_h10 < 4.0` (e.g., `v2_2p4_h_0p08_u_0p6` with `perm_h6 = 3.71`, `perm_h10 = 3.98`, plus un-probed `w_hold = 0.0` horizon-invariant `v2 ∈ {2.8, 3.2}` + `p_use = 0.6` where `perm_h6 == perm_h10 = 3.4–3.8` identically across all horizons!), and
  2. Two-phase `GW1–8` higher early-season jitter protection (`#230`) vs `v2_2p0_h_0p15_u_0p4` and baseline.

## Decision

**Verdict (`#231` Approved)**: Adopted **Option B2 (`v2_2p4_h_0p15_u_0p6`: `ft_value_list = {"2": 2.4, "3": 1.44, "4": 0.72, "5": 0.24}`, `spare_ft_hold_weight = 0.15`, `ft_use_penalty = 0.6`, unscaled across `1 <= H <= 10`) + 5-FT cap-overflow hold waiver** across both live Transfer Planner (`solver/`) and 6-GW promotion replay (`backtesting/`). Rejected two-phase `GW1–8` regime under Q9 parsimony (`q9_twophase_parsimony_pass = False`).

**Post-`#230` B2 Overflow-Guard Check ([live_gw12_21_b2_cap_guard.csv](live_gw12_21_b2_cap_guard.csv))**:
- Adding the `1 - ft_above_ub[w]` waiver lifted `v2_2p4_h_0p15_u_0p6` on live `GW12–21` (`H=10`) from `658.58` → **`659.82` EGS** (`+1.82` vs baseline `658.00`), reduced wasted FTs (`2` → `1` terminal `GW21`), lowered `avg_ft_bank` (`3.10` → `2.70`), and cleared `GW12–20` with `0` wasted FTs while delivering `2,138` pre-waiver (`proto230`) / **`2,120`** post-PR `#234` `S-1` and **`2,336`** `S-2` (`0` wasted FTs across all 76 historical GWs, `perm = 4.34`/`4.84` vs `6.60` `H=10` Strategic hit hurdle).
- Production changes landed in `#231` (and PR `#234` 5-FT overflow hold waiver): amended `ADR 0065` & `ADR 0066 §7`, synced WC/FH + 5-FT overflow `gw_ft_hold` waivers into `backtesting/native_transfer_solver.py` and `solver/solver.py`, updated `def_xg_shrink_challenger` certified references (`S-1 = 2,120` on `main @ 3b6a183e`, `S-2 = 2,336`), preserved all `101` `candidate_ledger.csv` `dead` locks, and kept `2026-27` sealed.

## Risks and unknowns

- Stage 1 (`0.5%` gap) re-ordering: `v2_2p0_h_0p15_u_0p4` finished 4th in Stage 1 (`2,159`) and 1st combined among strict passers in Stage 2 (`4,441`), while Stage 1's #1 (`v2_1p2_h_0p00_u_0p4`, `2,170`) dropped to last in Stage 2 (`4,290`) — confirming that `0.5%` approximate MIP solves reorder close trajectories across 38 sequential GWs.
- **No strict `< 4.0` flat static schedule beat `baseline_adr0065` (`2,167`) on `2025-26` (`S-1`)** (`-29` to `-73`), even though every upper-plateau config beat baseline by `+19` to `+37` on untuned `2024-25` (`S-2`).
- **Live `H = 10` `5`-FT cap waste under `w_hold > 0`**: Removing `horizon_scale` from `ft_hold_weights` increases late-horizon holding bonus by `~1.47x` at `H = 10` (`effective_horizon_scale(10, 0.85) = 1.4731`), causing `w_hold = 0.08` and `0.15` to waste `1–2` FTs at `post_ft = 5` in `GW19–21` unless `w_hold = 0.0` or `gw_ft_hold` is explicitly zeroed on cap-overflow transitions.
- **2-season `H = 10` live gap**: `live_gw12_21_sensitivity.csv` hit the `180s` cap on all 5 schedules (`0.34%–1.75%` gap), though relative rankings match clear economic mechanics (`w_hold = 0.0` avoids 5-FT overflow).

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
