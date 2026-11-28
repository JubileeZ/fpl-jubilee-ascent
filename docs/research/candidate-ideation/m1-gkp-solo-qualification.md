# Pure-History M1 GKP Solo Qualification (Track C / #252)

**Updated**: 2026-11-28T19:08:00+07:00
**Data stamp**: 2025-26 GW1–38 (`S-1` Development, seed 2024-25)
**Season**: `2025-26` (`S-1` Dev); `2024-25` (`S-2`) unspent; `2026-27` (`S`) sealed
**Purpose**: Evaluate pure point-in-time history `M1` GKP solo (`m1_gkp_solo`, discrete `#1`/`#2` `89m`/`1m` allocation with 2-start available-rival handover routed through `scale_states_to_target`, zero FPL API `status`/`chance`/`news` reads) as a Layer 1 Candidate against Confirmed Champion `def_xg_shrink_challenger` under Track B split diagnostics and `ADR 0071` (`600s` `gap=0.0`) certified rolling-MILP qualification.
**Companions**: [Prototype](prototypes/m1_gkp_solo/prototypes.py) · [Split Diagnostics Runner](prototypes/m1_gkp_solo/run_split_diagnostics.py) · [S-1 Split xMins](prototypes/m1_gkp_solo/s1_split_minutes_diagnostics.csv) · [S-1 Oracle Parity](prototypes/m1_gkp_solo/s1_oracle_parity_check.json) · [S-1 Prefix Parity](prototypes/m1_gkp_solo/s1_prefix_parity.csv) · [S-1 Summary](prototypes/m1_gkp_solo/s1/summary.json) · [S-1 Paired Scores](prototypes/m1_gkp_solo/s1/paired_weekly_scores.csv) · [S-1 Projection Guards](prototypes/m1_gkp_solo/s1/projection_guards.csv) · [S-1 Guard Margins](prototypes/m1_gkp_solo/s1/guard_margins.json)

---

## Sources

- **Source separation:** Raw `S-1` inputs comprise `2025-26` admitted GW1–7 empirical mirrors (`config/dev_mirror_2025_26_manifest.json`), hourly official fixture captures (`s1_historical_fixture_sources.csv`), `2024-25` seed archive (`data/archive/2024-25/processed/`), and immutable `2025-26` archive outcomes (`data/archive/2025-26/processed/`). All project findings below synthesize observed execution outputs on these sources against `ADR 0071` / `ADR 0072` rules.
- Issue spec: [Track C #252](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/252) · [Wayfinder Map #249](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/249) · [ADR 0072](../../adr/0072-dashboard-minutes-cascade-and-split-backtesting.md) · [ADR 0071](../../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md).

## Agent Prompt

Run `uv run python .agents/skills/explore-candidate/smoke.py docs/research/candidate-ideation/prototypes/m1_gkp_solo/prototypes.py --audit_only`, then `uv run python docs/research/candidate-ideation/prototypes/m1_gkp_solo/run_split_diagnostics.py`, then certified `run_s1_replay.py`, `audit_historical_prefix.py`, and `compare_historical_replays.py` on `S-1` into `docs/research/candidate-ideation/prototypes/m1_gkp_solo/` (`s1/summary.json` `delta_net`, `s1/projection_guards.csv` `passed`, `s1_split_minutes_diagnostics.csv` `active_mae`). Remove `.tmp/agent/` scratch caches when complete.

## Method

1. **Pure-history Layer 1 prototype (`m1_gkp_solo`):** Implemented `PureHistoryM1GkpModel` outside `models/` (keeping `core_closure_hash()` invariant at `ccfe0a75ef68a0df4b895d7d6f934da50226ae56bfc7962300e9a4340258b986`, reviewed SHA-256 `d2110a9b8f47028bd586b48bb01f683802492808a8c6dc76d10a1c3f18d61adb`).
   - Strictly causal (`< target_gw`) club fixture recovery from `history_df` + `now_cost` + `n_starts_historical` prior-season seed proxy (`zero` `status`, `chance_of_playing`, or `news` reads; passes `smoke.py --audit_only` cleanly).
   - Discrete club GKP ranking (`2-start` handover, `1-game` unflagged starter retention without status read, `6-GW` form, total starts, price tie-break), assigning `89.0 / 1.0 / 0.0` minutes per fixture and routing native Champion GKP states through `scale_states_to_target`.
   - Outfielders (`position_id in {2, 3, 4}`), native `ADR 0010` hard-DNP overrides, and `Oracle Participation State` bypass compose cleanly without modifying outfield `preserve_mass`.
2. **Track B Split Diagnostics (`run_split_diagnostics.py`):** Evaluated `S-1` GW1–38 across `t+0..t+5` and `GKP` vs `all` slices via `commands/evaluate_minutes.py`, plus `Oracle Participation State` parity check on `GW1–5`.
3. **Certified `ADR 0071` Rolling-MILP Qualification (`S-1`):** Executed uncontended `threads=1` HiGHS `gap=0.0` `600s` rolling-MILP replays (`def_xg_shrink_challenger` vs `m1_gkp_solo`), `14/14` admitted GW1–7 prefix parity verification, and `15` GW-clustered substantive projection non-inferiority guards + `3` MILP segment floors (`-8.9 / -4.7 / -4.2` pts/GW).

### Metric Definitions & Direction

| Metric | Symbol / Column | Direction | Ideal / Benchmark | Description |
| --- | --- | --- | --- | --- |
| **Rolling Replay Net Delta** | `delta_net` (`s1/summary.json`) | Higher $\uparrow$ | `> 0` (`S-1` & `S-2`) | Certified `600s` `gap=0.0` 6-GW Strategic MILP net FPL points (`candidate_net - champion_net`). |
| **Saves MSE Non-Inferiority** | `saves_points_mse` (`s1/projection_guards.csv`) | Lower $\downarrow$ | 95% upper CI $\le$ `margin` (`0.000618`) | Paired GW-clustered MSE difference (`cand - champ`) on `xp_saves` across 6-GW forecast horizons (`GW1–38`). |
| **Active GKP Minutes MAE** | `active_mae` (`s1_split_minutes_diagnostics.csv`) | Lower $\downarrow$ | `< 8.198` (`t=0 GKP`) | Mean absolute minutes error where projected `> 0` or actual `> 0`. |
| **Overall GKP Minutes MAE** | `overall_mae` (`s1_split_minutes_diagnostics.csv`) | Lower $\downarrow$ | Minimize (`< 8.051`) | Mean absolute minutes error across all GKP player-fixtures (including `0m` backups). |
| **False-Start Rate** | `false_start_rate` (`s1_split_minutes_diagnostics.csv`) | Lower $\downarrow$ | `< 9.01%` (`t=0 GKP`) | Share of `p_start >= 0.5` GKPs who did not start (`0` mins/sub). |

## Findings

1. **Track B Split Diagnostics (`s1_split_minutes_diagnostics.csv`, `s1_oracle_parity_check.json`):**
   - **Oracle Participation State GW1–5 parity:** Exact equality (`df_eval_exact_equal=true`), confirming zero event-rate drift from Champion.
   - **Whole-pool noise suppression vs active GKP sharpness (`GKP` slice):** At `t+0`, `m1_gkp_solo` cut `overall_mae` nearly in half (**`4.248m`** vs **`8.051m`**) and lowered `active_bias` (**`+0.062`** vs **`+0.350`**) by zeroing `#3+` keepers (`active_count = 1,535` vs `3,665`). However, without pre-deadline availability `status`/`chance`, waiting `2` missed starts before demoting an absent `#1` regressed `GKP` `active_mae` (**`10.328m`** vs **`8.198m`**, `delta_mae = -2.129m`), `brier_score` (**`0.0866`** vs **`0.0693`**), `false_start_rate` (**`10.39%`** vs **`9.01%`**), `missed_starter_rate` (**`10.28%`** vs **`9.49%`**), and `xmins_if_start_mae` (**`2.267m`** vs **`0.633m`**). Horizon `GKP` `active_mae` widened to **`19.249m`** vs **`10.852m`** at `t+5`.
   - Across `all` positions at `t+0`, `active_mae` shifted `14.061m` vs `13.566m` (`overall_mae` improved `12.907m` vs `13.345m`).
2. **Certified `ADR 0071` S-1 Rolling-MILP Replay (`s1/summary.json`, `s1/projection_guards.csv`, `s1_prefix_parity.csv`):**
   - **Score & Segments PASS:** `m1_gkp_solo` scored **`2,191`** net points vs Champion **`2,120`** (**`+71.0`** net pts; shared `opening-anchor-809d4afb3e40c205`; `14/14` admitted `GW1–7` prefix checks exact `0.0` diff; `3/3` segment floors PASS: `cold_start -1.50` vs `-8.9`, `early_mid -0.73` vs `-4.7`, `late +4.63` vs `-4.2`; `L=5` MBB `95% CI [-0.79, +3.92]` pts/GW, `est +1.87`, `p_sup = 0.101`).
   - **Substantive Projection Guard FAIL (`14/15 PASS`):** `m1_gkp_solo` failed non-inferiority on **`saves_points_mse`** (`status=INCONCLUSIVE`, `passed=False`, `estimate = +0.000549`, `SE = 0.000149`, 95% upper CI **`0.000794 > margin 0.000618`**). All other `14/15` guards passed (`points_mse` `+0.029 <= 0.207`, `minutes_mae` `-0.322 <= 0.795`, `clean_sheet_points_mse` `+0.0034 <= 0.0243`, `minutes_points_mse` `+0.0062 <= 0.0187`, `bonus_points_mse` `+0.0016 <= 0.0092`).
3. **Why MILP gained `+71` while `saves_points_mse` failed:** Removing noise from `0m` third-string keepers improved solver squad selection (`2,191` vs `2,120`), while hard-clamping `#1` keepers to `89m` without availability `status`/`chance` or conditional save dampening inflated squared error on `xp_saves` when unflagged `#1` keepers missed games. In contrast, `SP_Soft_Shield_M1` (Layer 2 + Layer 3b) pairs `M1` GKP with pre-deadline `status`/`chance` overrides so injured `#1` keepers hand over to backups immediately (`S-1 = 2,207`, `2026-27 GW6–11` GKP MAE `2.61m`).

## Decision

- **`m1_gkp_solo` FAILS S-1 Dev Gate** (`projection_guards_ok = false` on `saves_points_mse`, Track B Tier 1 GKP `active_mae = -2.129m`). Under `ADR 0071` / `run_s2_filter.py` qualification discipline, **no S-2 (`2024-25`) look is consumed**.
- Record pure-history `m1_gkp_solo` in [Candidate Ledger](../candidate-ledger/candidate_ledger.csv) as **`dead`** (`evidence_date=2026-11-28`, `revisit_after=2027-11-28`), distinct from softmax/linear `min_05_*`.
- Keep **`M1` GKP exclusively in Layer 2 (`Internal Minutes Baseline`, `SP_Soft_Shield_M1`)** alongside pre-deadline `Soft Empirical Broad Pool Shield` (`ADR 0072`). Leave `Confirmed Champion` (`def_xg_shrink_challenger`), `config/model_selection.json` (`podium_sealed=false`, `provisional_active=null`), and `2026-27` (`S`) untouched.

## Risks and unknowns

- Whether coupling `M1` GKP with a learned shrinkage blend (e.g., shrinking pure-history `89m` toward Layer 1 `p_start` or soft saves damping) recovers `saves_points_mse` non-inferiority in a future Layer 1 batch remains untested and out of Track C scope.
- `S-1` archived `players.parquet` metadata has known static club/January-transfer caveats (`docs/testing/archive-testing.md`), mitigated for GW1–7 via `admitted` empirical mirrors (`14/14` exact).
