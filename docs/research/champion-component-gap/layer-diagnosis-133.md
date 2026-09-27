# Layer diagnosis of late regret and MAE guardrails (#133)

**Updated**: 2026-09-27T23:10:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25; recompute 2026-09-27  
**Season**: 2025/26  
**Status**: Active — resolves wayfinder [#133](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/133)  
**Purpose**: Name which stack layer opens the late GW20–38 Blended regret loss and the Realized/Process MAE guardrail regress vs Champion `hold_chase_challenger`, and whether cheap post-hoc ablations pass the Historical Promotion Gate.  
**Scope**: Walk-forward layers + algebraic defence scale + bonus-ledger ablations. No model build. No slate or Champion change.  
**Related**: [#132](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/132) · [#131](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/131) · map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110) · [segment-loss-121](segment-loss-121.md) · [Eval canon](../INDEX.md)  
**Artifact**: [layer_diagnosis_133_gate.csv](layer_diagnosis_133_gate.csv) `late_delta` · [layer_diagnosis_133_late_position.csv](layer_diagnosis_133_late_position.csv) `regret_delta` · [layer_diagnosis_133_late_component.csv](layer_diagnosis_133_late_component.csv) `mae_delta` · [layer_diagnosis_133.json](layer_diagnosis_133.json)

## Sources

- **Primary**: `backtesting/promotion.py` `evaluate_historical_promotion_gate` / `SEASON_WINDOWS` — pass rule and GW20–38 `late`
- **Primary**: `models/goals_path_challenger.py` `_GOAL_WEIGHT_SCALE=0.891559`; `models/defence_link_challenger.py` `predict` post-link scales; `models/bonus_arm_challenger.py` `_XBPS_WEIGHTS` / `_BONUS_SOFTMAX_T=8`
- **Primary**: [#131](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/131) dry-run — defence and bonus cells must match
- **Repository data**: walk-forward `hold_chase_challenger`, `goals_path_challenger`, `bonus_arm_challenger` on `data/archive/2025-26/processed` seed `2024-25`

**Source boundary**: `defence_link` ledger is goals ledger plus shipped scales (predict algebra). Undo of those scales on `bonus_arm` matches goals `xp_clean_sheet` / `xp_conceded` / `xp_goals` within 1e-15 (`layer_diagnosis_133.json` `align_max_abs`). Archive `snapshot_backed=false`.

## Agent Prompt

```text
Full redo docs/research/champion-component-gap/layer-diagnosis-133.md

1. uv run python docs/research/champion-component-gap/layer_diagnosis_133.py
2. Refresh gate / late position / late component companions in this folder.
3. Update Findings from companion columns. Do not refit reduced k_cs; set is (1.00, 1.10, 1.15).
4. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Walk-forward gate forensics plus post-hoc scales

**Inputs**:
- Champion `hold_chase_challenger`; layers `goals_path_challenger` → `defence_link_challenger` → `bonus_arm_challenger`
- Ablations on the bonus ledger after reversing `_CS_SCALE` / `_GC_SCALE`: no defence scale; prod scales on GKP+DEF only (`position_id` 1 and 2); reduced `k_cs` ∈ {1.00, 1.10, 1.15} with prod `k_gc` (precommitted from the #124 grid)
- Season 2025-26 GW1–38; seed 2024-25; `eval_target=blended_points`

**Procedure**:
1. Quality: row count, GW span, duplicate player-GW, nulls, position ids, ledger residual. Then aggregates.
2. Score each ledger with `evaluate_historical_promotion_gate` (Blended primary + Realized/Process MAE).
3. Late window: Blended top-11 regret attributed to position of XI swaps (positions sum to mean regret). Realized component MAE / bias by position.
4. Layer cause = incremental move versus the parent ledger, not only the gap versus Champion.

**Definitions and assumptions**:
- `late` = GW20–38. Delta = Champion − Candidate. Positive primary / regret / MAE delta = Candidate better.
- Position regret is the swap-set contribution. It sums to late regret. It is not a claim that the projection of that position changed.
- `defence_link` not a fourth walk-forward.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Blended top-11 regret | `top_11_regret` | Mean GW regret of projected XI vs Blended oracle XI | Lower $\downarrow$ | Beat Champion | Gate primary when informative |
| Late delta | `late_delta` | Champion late regret − Candidate late regret | Higher $\uparrow$ | > 0 | GW20–38 segment |
| Segment wins | `segment_wins` | Windows with Candidate primary &lt; Champion | Higher $\uparrow$ | ≥ 2/3 | Gate majority |
| Combined primary delta | `combined_primary_delta` | Champion − Candidate combined regret | Higher $\uparrow$ | > 0 | Season primary |
| Realized / Process MAE delta | `realized_mae_delta` / `process_mae_delta` | Champion MAE − Candidate MAE | Higher $\uparrow$ | ≥ 0 | Guardrails |
| Position regret delta | `regret_delta` | Same as late delta, one position's swap players | Higher $\uparrow$ | Parts sum to `late_delta` | Where the XI gap sits |
| Component MAE delta | `mae_delta` | Champion component MAE − Candidate, Realized ledger | Higher $\uparrow$ | Context | Which Event Component moves |

**Validation boundary**: defence and bonus gate cells match [#131](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/131) `champion_dry_run_131.json`. Position-sum regret matches gate late regret within 1e-13.

## Project interpretation

### Decision rules

- Late regret and MAE guardrails have different parent layers. Do not treat “the stack” as one cause.
- A post-hoc CS or bonus scale that leaves late delta ≤ 0 is not a flip path.
- Un-stacking defence scales is allowed and, on this window, makes late regret worse.

### Practical implications

- Next build should aim at FWD top-11 regret from the goals weight, not another `k_cs` / `k_gc` / current bonus-weight retune.
- Every `goals_path` descendant in this run misses xMins MAE and Spearman by a hair. A gate pass still has to recover those.

## Findings

### Data quality

31958 rows each, GW1–38, 0 duplicate player-GW, 0 nulls on points and `position_id`, ledger residual &lt; 1e-14. Late slice 15979 rows = GKP 1843 + DEF 5130 + MID 7201 + FWD 1805. Source: [layer_diagnosis_133.json](layer_diagnosis_133.json) `quality`; [layer_diagnosis_133_late_position.csv](layer_diagnosis_133_late_position.csv) `rows`.

`bonus_arm` with scales removed matches goals `xp_goals` / `xp_clean_sheet` / `xp_conceded` (max abs 4.4e-16). `xp_goals`, `xp_assists`, `xp_minutes` match exactly between goals and bonus. Source: `align_max_abs`.

### No ablation passes

`any_pass=false`. Eight ledgers, zero Historical Promotion Gate passes. Source: [layer_diagnosis_133.json](layer_diagnosis_133.json) `any_pass`; [layer_diagnosis_133_gate.csv](layer_diagnosis_133_gate.csv) `passed`.

| Ledger | Segs | Combined Δ | Late Δ | Realized MAE Δ | Process MAE Δ |
|---|---:|---:|---:|---:|---:|
| `goals_path_challenger` | 1/3 | −0.812 | −1.678 | **+0.012** | **+0.011** |
| `defence_link_challenger` | 1/3 | **+0.077** | −0.758 | −0.004 | −0.003 |
| `bonus_arm_challenger` | 2/3 | −0.497 | −1.554 | −0.002 | −0.005 |
| `goals_bonus_no_def` | 1/3 | −1.254 | −2.302 | **+0.013** | **+0.009** |
| `def_gkp_def_only` | 2/3 | −0.445 | −1.618 | **+0.002** | −0.001 |
| `reduced_k_cs_1.00` | 1/3 | −1.254 | −2.302 | **+0.016** | **+0.012** |
| `reduced_k_cs_1.10` | 2/3 | −0.878 | −1.940 | **+0.010** | **+0.007** |
| `reduced_k_cs_1.15` | 1/3 | −0.959 | −2.071 | **+0.007** | **+0.004** |

Source: [layer_diagnosis_133_gate.csv](layer_diagnosis_133_gate.csv). Positive MAE Δ = Candidate better. `reduced_k_cs_1.00` matches `goals_bonus_no_def` on regret (same XIs) and differs on MAE because prod `k_gc` does not change the top-11.

`defence_link` combined Δ +0.07697 and `bonus_arm` −0.49724 / late −1.55368 match [champion_dry_run_131.json](champion_dry_run_131.json).

### Which layer opens late regret

Incremental late Δ (this layer minus parent):

| Step | Late Δ vs Champion | Incremental |
|---|---:|---:|
| Champion → goals | −1.678 | **−1.678** |
| goals → defence | −0.758 | **+0.920** |
| defence → bonus | −1.554 | **−0.796** |

Goals opens the late hole. Defence link gives back 0.920. Bonus gives 0.796 of that back. Versus Champion, every shipped layer still loses late. Source: `late_delta` differences.

Late regret by position (`regret_delta`, parts sum to late Δ):

| Position | Goals | Defence | Bonus |
|---|---:|---:|---:|
| GKP | +0.421 | +1.684 | +0.421 |
| DEF | +0.396 | +2.681 | −1.023 |
| MID | +1.595 | +0.163 | +3.680 |
| FWD | **−4.089** | **−5.286** | **−4.632** |
| ALL | −1.678 | −0.758 | −1.554 |

Source: [layer_diagnosis_133_late_position.csv](layer_diagnosis_133_late_position.csv) `regret_delta`.

FWD is the only position with a large negative regret delta on the goals layer, and it more than cancels MID/DEF/GKP gains. FWD `xp_goals` mean projection falls 0.074 vs Champion and FWD goals MAE improves (+0.041), so the dampen `k=0.891559` is MAE-good and top-11-bad. Source: [layer_diagnosis_133_late_component.csv](layer_diagnosis_133_late_component.csv) `mean_proj_delta_cand_minus_champ` / `mae_delta` for `xp_goals` × FWD.

Defence does not change FWD projections (FWD clean sheet and conceded stay 0). The worse FWD regret under defence is XI spillover: GKP/DEF regret improves (+1.26 / +2.29 vs goals) and MID/FWD swap regret worsens. Net late still improves by 0.920.

Bonus mean `xp_bonus` is unchanged versus Champion (ALL `mean_proj_delta` ≈ 0) but the mass moves: DEF −0.024, GKP −0.012, MID +0.020. Late regret follows: MID +3.52 vs defence, DEF −3.70 vs defence. Source: component CSV `xp_bonus` by position.

### Which layer opens the MAE guardrail regress

Season Realized / Process MAE Δ vs Champion:

| Step | Realized Δ | Process Δ | Incremental Realized | Incremental Process |
|---|---:|---:|---:|---:|
| goals | +0.012 | +0.011 | +0.012 | +0.011 |
| defence | −0.004 | −0.003 | **−0.016** | **−0.014** |
| bonus | −0.002 | −0.005 | +0.002 | −0.002 |

Goals clears both MAE guardrails. Defence scale is what crosses them (Realized 1.0373 vs 1.0334, Process 0.9234 vs 0.9205). Bonus heals Realized a little versus defence and makes Process worse; both stay above Champion. Source: gate CSV `realized_mae_*` / `process_mae_*`.

Late component MAE (ALL): goals `xp_goals` +0.018; defence adds `xp_clean_sheet` −0.030 (bias +0.063) and `xp_conceded` −0.004. DEF clean-sheet MAE −0.060, GKP −0.034. Bonus adds `xp_bonus` MAE +0.006 overall, with MID bonus MAE −0.007. Source: component CSV.

Late position Blended MAE Δ: goals positive on DEF/MID/FWD; defence GKP −0.019 and DEF −0.023. Source: position CSV `blend_mae_delta`.

### Structural guardrails the ablations never clear

xMins MAE is 14.7472 on every Candidate vs Champion 14.7437. Spearman is lower on every row (Champion 0.68997). Absolute Blended bias passes for goals (0.102 vs 0.130) and fails for defence and bonus (0.145). Source: gate CSV `xmins_mae_*`, `spearman_*`, `abs_bias_*`.

Minute forecasts differ on 104 / 31958 rows (max |Δ| 7.0, mean |Δ| 0.010). Source: [layer_diagnosis_133.json](layer_diagnosis_133.json) `minutes_forecast_vs_champion`. `xp_minutes` points match exactly, so the miss is the minute count, not appearance points. It does not explain the late regret gap.

## Decision

**Verdict**: Late Blended regret loss is opened by **`goals_path`**, almost entirely **FWD** top-11 swaps, while that same layer **improves** Realized and Process MAE. **`defence_link` repairs late regret (+0.920) and is the layer that breaks the MAE guardrails** via all-pool clean-sheet inflation. **`bonus_arm` re-opens late regret (−0.796)** by moving bonus off DEF/GKP onto MID; it is why the stack is 2/3 segments and still late-negative. **No cheap ablation passes the gate, and none wins late.**

**Ranked build options** (user pick; none is a proven pass):

1. **Position-split goals weight.** Restore FWD `xp_goals` toward Champion; keep the MID/DEF dampen that buys MAE. Re-score the gate before more CS or bonus work. Matches the only large negative position on the layer that opens late.
2. **Drop the current bonus shift from the flip stack.** Bonus is the step that widens late again. A replacement has to beat `defence_link` on late, not only win `early_mid`. Flat and current non-flat bonus have not won late (#124 and this note).
3. **Do not spend the next build on `k_cs` / `k_gc`.** GKP+DEF-only, `k_cs` 1.00 / 1.10 / 1.15, and dropping both scales all leave late Δ &lt; 0. Un-stacking defence makes late worse (−2.302).

**Outcome**: Map #110 closed by user 2026-09-27 before a pick; options above left unbuilt.

**Trigger / kill switch**: A Candidate with `late_delta>0`, ≥2/3 segments, Realized and Process MAE ≤ Champion, plus xMins MAE and Spearman ≥ Champion.

## Risks and unknowns

- Swap-set position regret equals the regret total. It does not equal “that position’s projection caused the gap” when another position’s scale changes the XI (defence vs goals on FWD).
- Position-split `k` is not scored here. It can miss the soft `xp_goals` bias bar.
- xMins / Spearman hairline miss blocks this family under a strict guardrail even if late and MAE were fixed. 104 rows. Not investigated beyond the count.
- Post-hoc scales match shipped predict algebra. They are not a refit of Poisson λ.
