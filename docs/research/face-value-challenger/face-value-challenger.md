# Face-value Challenger (Champion search 2026-09-28)

**Updated**: 2026-09-28T02:45:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25; 2026-27 archive GW1–5 seed 2025-26; recompute 2026-09-28  
**Season**: 2025/26 (gate) + 2026/27 GW1–5 (holdout)  
**Status**: Active — Champion promoted (ADR 0045)  
**Purpose**: Find Candidate beating Champion `hold_chase_challenger` on Historical Promotion Gate; record lever evidence.  
**Scope**: 5 parallel smoke lanes (fit layer, top-end ordering, minutes/defence, learned model, ensembles) → stacked Candidate → gate. No feature-builder changes.  
**Related**: [ADR 0045](../../adr/0045-champion-face-value-challenger.md) · [ADR 0044](../../adr/0044-blended-eval-target-promotion-primary.md) · [layer-diagnosis-133](../champion-component-gap/layer-diagnosis-133.md) · [Eval canon](../INDEX.md)  
**Artifact**: [face_value_gate_summary.csv](face_value_gate_summary.csv) `combined_delta` / `boot_p_gt0` · [smoke_lane_results.csv](smoke_lane_results.csv) `combined_delta` (frozen smoke snapshot)

## Sources

- **Primary**: `backtesting/promotion.py` `evaluate_historical_promotion_gate`; `backtesting/model_evaluation.py` `compare_to_reference` — pass rule
- **Primary**: `models/metrics_component_hybrid.py` `fit` / `_fit_metric_weights` — in-season ridge + per-player offsets n/(n+15)
- **Repository data**: `data/archive/2025-26/processed`, `data/archive/2026-27/processed`; `commands.evaluate_model_promotion --apply` evidence `data/reports/promotion_evidence/20260927T192257Z-face_value_challenger.json`

**Source boundary**: Archive `snapshot_backed=false`. Smoke lane rows produced by scratch harness (cached features, same scoring loop); not regenerable from runner. Gate rows regenerable.

## Agent Prompt

```text
Full redo docs/research/face-value-challenger/face-value-challenger.md

1. uv run python docs/research/face-value-challenger/runner.py  (~10 min, 8 procs)
2. Refresh Findings from face_value_gate_summary.csv columns combined_delta, *_regret, *_mae, abs_bias, spearman, xmins_mae, gw_wins, boot_p_gt0.
3. smoke_lane_results.csv is frozen; do not regenerate.
4. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Walk-forward backtest, lever ablation

**Inputs**: Reference `hold_chase_challenger`; Candidate `face_value_challenger`; ablations `ablation_face_value_only` (lever 1), `ablation_face_value_start_shrink` (levers 1+3). Blended eval target.

**Procedure**:
1. Smoke harness: cache per-GW features, replay walk-forward scoring loop, real gate code. Validated: reproduces #131 `defence_link_challenger` Δ +0.0770.
2. Five lanes, tiny pre-declared grids, tune 2025-26 only, one 2026-27 run per lane pick.
3. Stack orthogonal lane winners (A1 attack weights, A2 pooled finishing, A3 start shrink); ablate.
4. Promote via `commands.evaluate_model_promotion --apply`.

**Definitions and assumptions**:
- Delta = reference − Candidate; positive = Candidate better.
- 2026-27 holdout contaminated for stack: each lever's lane saw it once.
- Feature columns copied from `players.parquet` (`total_points`, `minutes`, `goals_scored`, `expected_goals`, `bps`, `threat`, `selected_by_percent`, `now_cost`, `status`, `chance_of_playing`, …) are terminal season-end values in archive features (identical GW2 vs GW30). Banned as new inputs.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Blended top-11 regret | `top_11_regret` | Mean GW (best-11 blended − projected-top-11 blended) | Lower $\downarrow$ | < reference | Gate primary |
| Combined delta | `combined_delta` | reference regret − Candidate regret | Higher $\uparrow$ | > 0 | Gate primary delta |
| GW wins | `gw_wins` / `gw_losses` | GWs with per-GW regret delta > 0 / < 0 | Higher $\uparrow$ | Majority | Robustness |
| Bootstrap P | `boot_p_gt0` | Share of 20k GW resamples with mean delta > 0 | Higher $\uparrow$ | ≥ 0.90 | Robustness; seed 0 |
| Guardrails | `xmins_mae`, `abs_bias`, `spearman`, `realized_mae`, `process_mae` | ADR 0044 | xMins/bias/MAE $\downarrow$; Spearman $\uparrow$ | ≤ / ≥ reference | Gate guardrails |

**Validation boundary**: Runner (repo walk-forward) matches harness to 4 dp. Single evaluation season; 38 GWs.

## Project interpretation

### Decision rules

- Realized-finishing refit is the Champion's defect: ridge on Realized goals drifts to ~1.02 xG + 0.36 threat (A1 `final_goal_w`), inflating attackers (|bias| 0.130).
- Finishing signal is real but must be pooled over minutes: per-appearance n/(n+15) lets one cameo goal explode a rate (A2: Jensen MID projected 16.7 for 19 late GWs, delivered 3.6).
- Levers stack: attack weights fix population calibration; pooled offsets fix late top-11; start shrink fixes xMins/bias.

### Practical implications

- Live `fit(df_perf[gw < target])` path supplies needed columns; no pipeline change.
- Learned hurdle correction (B1) = next lever candidate; needs per-GW feature memory in live path.

## Findings

### Gate (2025-26, `face_value_gate_summary.csv`)

| Model | Segs | Combined Δ | Late regret | Blend MAE | \|bias\| | xMins MAE | GW W/L | Boot P |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `hold_chase_challenger` | — | 0 | 67.054 | 0.9577 | 0.1301 | 14.7437 | — | — |
| face value only | 2/3 | +0.531 | 68.135 | 0.9158 | 0.0373 | 14.7437 | 23/15 | 0.666 |
| + start shrink | 2/3 | +0.709 | 67.667 | 0.8999 | 0.0050 | 14.6004 | 24/13 | 0.714 |
| **`face_value_challenger`** | **3/3** | **+1.670** | **66.072** | 0.8995 | 0.0064 | 14.6004 | 25/12 | **0.951** |

Candidate Spearman 0.6919 vs 0.6900; Realized MAE 0.9696 vs 1.0334; Process MAE 0.8664 vs 0.9205. All guardrails improve. Pooled finishing adds +0.96 combined, flips late (−0.61 → +0.98).

### Holdout (2026-27 GW1–5, contaminated)

`face_value_challenger` combined Δ +5.472, 2/2 populated segments, all guardrails hold (Realized MAE 1.2296 vs 1.3066). Source: summary CSV `season=2026-27`.

### Smoke lanes (`smoke_lane_results.csv`)

170 variant rows, 113 gate-pass. Lane picks: A1 face value +0.53; A2 unfitted + pooled goal offsets +1.46 (3/3); A3 start shrink +0.18; B1 learned hurdle on face-value base +2.61 (3/3, boot P 0.94; holdout +2.51 < base); B2 50/50 xG-only + fitted `defence_link` +1.01 (weight-fragile).

## Decision

**Verdict**: Promote `face_value_challenger`; gate PASS applied 2026-09-28 (ADR 0045).

**Recommended action**:
- Next lever: learned hurdle correction on top of Champion, once live path can label past-GW features.
- Re-run gate on 2026-27 GW6+ (first clean holdout).

**Trigger / kill switch**: 2026-27 GW6–19 walk-forward where `face_value_challenger` loses combined Blended regret or any guardrail to `hold_chase_challenger` → reopen.

## Risks and unknowns

- One gate season; combined margin +1.67 on ~72 regret; late edge +0.45 without best GW.
- Shrink 1800 / k 0.15 chosen from small grids on 2025-26 (K 900 also passes: +1.64).
- Legacy `chance_of_playing` terminal in archive; zero backtest effect (no snapshots) but live-only behavior.
- Holdout contaminated and 5 GWs, cold-start only.
