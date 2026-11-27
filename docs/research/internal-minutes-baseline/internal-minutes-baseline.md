# Internal Minutes Baseline & Soft Empirical Shield

**Updated**: 2026-11-27T22:55:00+07:00
**Data stamp**: 2025-26 GW1–38 (`S-1`), 2024-25 GW1–38 (`S-2`), 2026-27 GW6–11 frozen snapshot benchmark (`S`)
**Season**: `2025-26` (development), `2024-25` (untuned cross-check), `2026-27` (one-shot frozen read-only benchmark)
**Purpose**: Design and certify Solio-free Layer 2/3 pre-deadline xMins baseline + state-preserving participation override conversion without degrading 6-GW rolling Strategic MILP net points or overfitting live `2026-27` data (`ADR 0069`).
**Companions**: [S-1 Ablation](s1_ablation_summary.csv) · [S-1 Chance Calibration](s1_chance_calibration.csv) · [S-2 Cross-Check](s2_crosscheck_summary.csv) · [Initial Replay](rolling_replay_summary.csv) · [S-1 Replay Ablation](s1_replay_ablation.csv) · [S-2 Replay Verification](s2_replay_verification.csv) · [Frozen 2026-27 Benchmark](frozen_2026_27_benchmark.csv) · [Frozen 2026-27 By Position](frozen_2026_27_position_benchmark.csv) · [Runner](runner.py) · [Ablation Replay Runner](ablation_replay_runner.py) · [Frozen Benchmark Runner](frozen_2026_27_benchmark.py)

---

## Sources

- `S-1` (`2025-26`) & `S-2` (`2024-25`) pre-deadline `fplcache` bootstraps (`data/reports/empirical_mirrors/{2025-26,2024-25}/bootstraps/gw01..38.json.xz`) + Season Archive outcomes (`data/archive/{2025-26,2024-25}/processed/`).
- Live operational Solio CSVs archived read-only in `data/external/solio/2026-27/` + immutable snapshots from `origin/availability-snapshots` (`2026-27` GW6, 7, 8, 9, 11).

## Agent Prompt

Re-run S-1 chance/recovery calibration & 76-GW offline module ablation via `uv run python docs/research/internal-minutes-baseline/runner.py`, certified 6-GW rolling Strategic MILP ablations via `uv run python docs/research/internal-minutes-baseline/ablation_replay_runner.py`, and frozen read-only `2026-27` check via `uv run python docs/research/internal-minutes-baseline/frozen_2026_27_benchmark.py`. Verify companion columns (`s1_replay_ablation.csv` `cumulative_net`, `s2_replay_verification.csv` `cumulative_net`, `frozen_2026_27_benchmark.csv` `mins_mae` / `xp_mae`). Delete scratch dirs `.tmp/agent/` when done.

## Method

1. **Four candidate Layer 2/3 modules tested offline (`runner.py`, `S-1` calibrated):**
   - `M1`: Club GKP role (`89m`/`1m`, 2-start available-rival handover, doubtful/injured minutes shift to backup GKP).
   - `M2`: Unflagged 1–2 GW absence recovery (**dropped**: regressed `S-1` MAE `11.916` vs `11.796`, `-51` Legal XI pts).
   - `M3`: Pre-deadline FPL availability & return ramps (`20m->65m` known injury returns, `S-1` empirical doubtful curve).
   - `M4`: Club outfield capped minutes reconciliation toward `890m` (**dropped for MILP**: flattens `65m` starter-floor risk gap).
2. **State-preserving override conversion (`scale_states_to_target`) & Soft Empirical Shield:**
   - Replaced `target_to_states()` forced saturation (`p_start >= 0.96` above `70m`, `p_sub=0`) with native `(p_dnp, p_start, p_sub_in, xmins_if_start, p_60_if_start)` scaling (`models/participation_state_hybrid.py`).
   - Replaced 6-GW hard-zeroing on unknown-return injuries (`status='i'`) and `status='n'` with `S-1` empirical horizon recovery curves (`SOFT_UNKNOWN_CURVE`, `SOFT_SUSPENDED_N_CURVE`, `SOFT_DOUBTFUL_CURVES`).

### Metric Definitions & Direction

| Metric | Column / Formula | Direction | Ideal Benchmark | Description |
| --- | --- | --- | --- | --- |
| **Rolling Replay Net Score** | `cumulative_net` = gross pts minus hits | Higher $\uparrow$ | Beat `L1_L3b_shield` & `L1_native` | Certified `gap=0.0` `600s` cap 6-GW rolling Strategic MILP trajectory |
| **Next-GW Minutes MAE** | `t0_mins_mae` = $\text{mean}(\|\hat{m}_{t=0} - m\|)$ | Lower $\downarrow$ | Minimize without MILP loss | Immediate deadline minutes accuracy |
| **3-GW Horizon Minutes MAE** | `t02_mins_mae` = $\text{mean}(\|\hat{m}_{t=0..2} - m\|)$ | Lower $\downarrow$ | Minimize without MILP loss | Horizon accuracy across planning steps |
| **False-Start Rate** | `false_start_pct` = $P(m=0 \mid \hat{m} \ge 45)$ | Lower $\downarrow$ | $\le 7\%$ | Share of projected starters playing zero minutes |
| **Constrained Legal XI Regret** | `xi_mean_regret` = oracle £100m XI − model XI | Lower $\downarrow$ | Minimize | Single-GW £100.0m 15-squad + autosub gap |

## Findings

1. **Full-pool `target_to_states` + `M4` failed rolling MILP (`rolling_replay_summary.csv`):**
   - `Internal_M1_M3_M4` beat `L1_L3b_shield` on `t=0` MAE (`10.320` vs `11.796` on `S-1`; `11.459` vs `13.089` on `S-2`) but lost **`-39` (`2,068` vs `2,107`)** on `S-1` and **`-69` (`2,137` vs `2,206`)** on `S-2`.
2. **Sparse `SP_Soft_Shield_M1` (Soft Empirical Shield + sparse `M1` GKP + `scale_states_to_target`) won across both seasons (`s1_replay_ablation.csv`, `s2_replay_verification.csv`):**
   - `S-1` (`2025-26`): **`2,207` net** (**`+100`** vs `L1_L3b_shield` `2,107`; **`+87`** vs `L1_native` `2,120`); `t0_mins_mae` `11.4008` (vs `11.9607`), `t02_mins_mae` `13.4613` (vs `14.6375`), `t0_xp_mae` `0.9058` (vs `0.9167`).
   - Untuned `S-2` (`2024-25`): **`2,308` net** (**`+102`** vs `L1_L3b_shield` `2,206`; `-28` vs `L1_native` `2,336`); `t0_mins_mae` `12.6709` (vs `13.2645`), `t02_mins_mae` `14.6040` (vs `15.7977`), `t0_xp_mae` `0.9133` (vs `0.9225`).
   - Full-pool `SP_Soft_M1_M3_M4` gave lowest raw MAE (`10.4754` / `11.6234`) but trailed `SP_Soft_Shield_M1` by `-86` (`2,121`) on `S-1` and `-48` (`2,260`) on `S-2`.
3. **One-shot frozen `2026-27 GW6–11` benchmark vs Solio (`frozen_2026_27_benchmark.csv`, `common_solio` pool):**
   - `SP_Soft_Shield_M1` improved over `L1_L3b_shield` (`t=0` MAE `15.1755` vs `15.8143`, `t=0..2` MAE `17.7307` vs `18.3250`, best `false_start_pct` `5.769%`, best `t=0` xP MAE `1.2526`, GKP MAE `2.6073` vs `7.8988`, Legal XI `235.0` vs `233.0`).
   - `SP_Solio_Soft_Shield` (`scale_states_to_target` + Solio CSV) cut `t=0..2` MAE (`15.6272` vs `15.8539`) and raised Legal XI (`249.0` vs `240.0`) over legacy `L1_L2_L3b_cascade`.

## Decision

- Shipped frozen **`SP_Soft_Shield_M1`** into `models/participation_state_hybrid.py` (`scale_states_to_target`), `features/internal_xmins.py` (`build_soft_shield_layers`, `build_sparse_gkp_baseline`, `build_frozen_internal_minutes_baseline`), `features/injury_triage.py`, and `commands/injury_triage.py`.
- Layer 1 native Champion stays pure Official FPL; outfielders stay blank when `--base-csv` is omitted so `65m` starter-floor separation remains intact.

## Risks and unknowns

- Scoring-rate gap (`Solio_Pts_full` `276.0` vs Champion `233–249` Legal XI on `2026-27`) stems from event/xG/xA/CS rate projections rather than minutes and belongs to a separate `ideate-candidate` track.
- `SP_Soft_Shield_M1` trailed `L1_native` by `-28` pts (`48` vs `36` hits) on untuned `S-2`; left un-tuned to preserve `ADR 0069` holdout validity.
