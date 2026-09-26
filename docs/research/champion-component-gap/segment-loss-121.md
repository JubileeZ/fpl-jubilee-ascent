# defence_link Blended segment loss (#123 / #121)

**Updated**: 2026-09-26T17:32:24+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25; forensic recompute 2026-09-26 (matches #121 dry-run reasons)  
**Season**: 2025/26  
**Status**: Active — resolves wayfinder [#123](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/123)  
**Purpose**: Explain why admitted Candidate `defence_link_challenger` won only **1/3** seasonal segments on Historical Promotion Gate dry-run vs Champion `hold_chase_challenger` despite combined Blended primary improving (#121 FAIL).  
**Scope**: Gate code + #121 artifacts + companions. Per-segment Blended primary / Realized / Process + Event Component / position surfaces. Goals-only counterfactual diagnostic. No Candidate redesign.  
**Related**: [#121](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/121) · map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110) · [ADR 0044](../../adr/0044-blended-eval-target-promotion-primary.md) · [ADR 0010](../../adr/0010-participation-state-snapshots-and-evaluation.md) · [gate-plumbing-114](gate-plumbing-114.md) · [component-gap note](champion-component-gap.md) · [Eval canon](../INDEX.md)  
**Artifact**: [segment_loss_121_summary.csv](segment_loss_121_summary.csv) · [segment_loss_121.json](segment_loss_121.json) · [component_gap_summary.csv](component_gap_summary.csv) `mse_share` · [component_gap_totals.csv](component_gap_totals.csv) `realized_mae` / `blend_mae`

## Sources

- **Primary**: `backtesting/promotion.py` `SEASON_WINDOWS` / `evaluate_historical_promotion_gate` / `primary_metric_value` — segment defs + pass rule
- **Primary**: `backtesting/model_evaluation.py` `compare_to_reference` — Blended primary + Realized/Process MAE guardrails
- **Primary**: [#121 resolution comment](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/121#issuecomment-5837353157) — dry-run FAIL axes
- **Primary**: [ADR 0044](../../adr/0044-blended-eval-target-promotion-primary.md) · [ADR 0010](../../adr/0010-participation-state-snapshots-and-evaluation.md) (≥2/3 seasonal windows)
- **Repository data**: forensic walkforward `hold_chase_challenger` / `defence_link_challenger` / `goals_path_challenger` on `data/archive/2025-26/processed` seed `2024-25` → [segment_loss_121.json](segment_loss_121.json); season companions [component_gap_totals.csv](component_gap_totals.csv) · [component_gap_summary.csv](component_gap_summary.csv); model `models/defence_link_challenger.py` (`_CS_SCALE=1.296903`, `_GC_SCALE=1.145226`)

**Source boundary**: Archive exploratory (`snapshot_backed=false`). Gate CLI dry-run does not write evidence; forensic recompute is primary numeric source for per-segment cells. Goals-only rows are diagnostic (not #121 slate).

## Agent Prompt

```text
Full redo docs/research/champion-component-gap/segment-loss-121.md

1. Re-read backtesting/promotion.py SEASON_WINDOWS + evaluate_historical_promotion_gate.
2. Re-run forensic: uv run python .tmp/agent/segment_loss_121_v2.py
   (or equivalent walkforward + metrics_by_season_window on Champion + defence_link + goals_path).
3. Refresh segment_loss_121.json / segment_loss_121_summary.csv in this folder.
4. Update Findings tables from companion columns; cite #121 + ADR 0044.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Empirical gate forensics (walk-forward + segment windows)

**Inputs**:
- Champion `hold_chase_challenger`; Candidate `defence_link_challenger`; counterfactual `goals_path_challenger`
- Archive `data/archive/2025-26/processed`; seed `2024-25`; GW 1–38
- Eval targets: `blended_points` (gate primary), `actual_points`, `process_points`

**Procedure**:
1. Walk-forward each model (`WalkforwardConfig.eval_target="blended_points"`).
2. Score `metrics_by_season_window` on Cold-Start / early_mid / late + combined.
3. Replicate `evaluate_historical_promotion_gate` (primary = `decision_regret` when informative, else MAE).
4. Per segment: Blended/Realized/Process MAE + top-11 regret; Realized component MAE/bias/`mse_share` for focus ledger rows; position Blended MAE.
5. Goals-only vs Champion as counterfactual (same segment rule).

**Definitions and assumptions**:
- Seasonal segments from `SEASON_WINDOWS`: `cold_start` GW1–4; `early_mid` GW5–19; `late` GW20–38 (`backtesting/promotion.py`).
- Segment win = Candidate primary **strictly lower** than Champion on that window (lower regret / MAE better).
- Gate pass = combined primary improve **and** ≥2/3 segment wins **and** guardrails (ADR 0044 / `evaluate_historical_promotion_gate`).

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Blended top-11 regret | `top_11_regret` | Mean GW Decision Regret of top-11 projected vs top-11 Blended actual | Lower $\downarrow$ | Beat Champion | Gate **primary** when informative (`primary_metric_name`) |
| Segment wins | `segment_wins` | Count of `{cold_start, early_mid, late}` where Candidate primary &lt; Champion | Higher $\uparrow$ | ≥ **2**/3 | Majority rule (ADR 0010 / gate code) |
| Combined primary delta | `combined_primary_delta` | Champion primary − Candidate primary on combined window | Higher $\uparrow$ | &gt; 0 | #121 “primary improved” axis |
| Blended / Realized / Process MAE | `*_mae` | Mean \|proj − target\| | Lower $\downarrow$ | ≤ Champion (Realized/Process = guardrails) | Totals surfaces; not segment primary here |
| Component MAE delta | `mae_delta` | Champion component MAE − Candidate component MAE | Higher $\uparrow$ = Candidate better | Context | Which Event Component moves |
| Position Blended MAE delta | `blend_mae_delta` | Same at GKP/DEF/MID/FWD | Higher $\uparrow$ = Candidate better | Context | Where CS/GC vs goals arms land |

**Validation boundary**: Matches #121 printed reasons (1/3 segments; Realized 1.0373 vs 1.0334; Process 0.9234 vs 0.9205). Exploratory archive.

## Project interpretation

### Decision rules

- Combined primary can PASS while segment majority FAILS when one window’s regret margin dominates the season mean.
- Soft pre-gate (#120) clears component bias/demotion; does not guarantee Blended segment majority or MAE guardrails.
- Post-link CS/GC scales that fix `mins_60` link-bias can inflate `pool=all` CS and regress GKP/DEF Blended MAE.

### Practical implications

- #124 route grill should treat **early_mid + late Blended regret loss** + **GKP/DEF CS MAE regression** as the fail signature — not “Blended primary lied.”
- Goals-only counterfactual also 1/3 segments and **worse** combined regret than Champion → bonus / other arms must win mid+late regret, not only soft residual labels.

## Findings

### Gate mechanics (why 1/3 with primary↑)

- Primary metric on this dry-run = **`decision_regret`** (Blended), not Blended MAE. Source: [segment_loss_121.json](segment_loss_121.json) `verdict.primary_metric`; `backtesting/promotion.py` `primary_metric_name`.
- Combined: Champion regret **71.748** → Candidate **71.671** (Δ **+0.077** improve). Blended MAE still **worse** (0.9610 vs 0.9577). Source: [segment_loss_121_summary.csv](segment_loss_121_summary.csv) `combined`; [component_gap_totals.csv](component_gap_totals.csv) `blend_mae`.
- Segment windows (`SEASON_WINDOWS`):

| Segment | GW | Champ regret | Cand regret | Δ (champ−cand) | Cand wins? | Blend MAE Δ |
|---|---|---:|---:|---:|---|---:|
| **cold_start** | 1–4 | 76.583 | **71.810** | **+4.772** | **yes** | +0.0007 |
| **early_mid** | 5–19 | **76.405** | 76.523 | −0.118 | no | −0.0038 |
| **late** | 20–38 | **67.054** | 67.812 | −0.758 | no | −0.0038 |

Source: [segment_loss_121_summary.csv](segment_loss_121_summary.csv).

- Season-mean arithmetic: cold_start margin (~4 GWs × +4.77) outweighs early_mid + late losses in the **combined** mean → primary↑; binary majority still **1/3**. Source: table above + `evaluate_historical_promotion_gate` loop over `_SEGMENT_NAMES`.
- Guardrails (independent fail axis): Realized MAE 1.0373 vs 1.0334; Process MAE 0.9234 vs 0.9205 — matches [#121](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/121#issuecomment-5837353157).

### Which segments won / lost

- **Won:** `cold_start` only.
- **Lost:** `early_mid`, `late`.
- Largest primary loss = **late** (−0.758 regret). early_mid loss small (−0.118) but still a loss.

### Event Components / eval surfaces driving losses

**Position Blended MAE** (combined; same sign in early_mid + late):

| Position | Blend MAE Δ (champ−cand) | Read |
|---|---:|---|
| GKP | **−0.022** | Candidate worse |
| DEF | **−0.024** | Candidate worse |
| MID | +0.003 | Candidate better |
| FWD | **+0.050** | Candidate better (goals arm) |

Source: [segment_loss_121_summary.csv](segment_loss_121_summary.csv) `*_blend_mae_delta`.

**Focus components** (combined Realized ledger):

| Component | MAE Δ | Bias champ → cand | Notes |
|---|---:|---|---|
| `xp_goals` | **+0.020** | +0.075 → +0.047 | Goals arm helps everywhere |
| `xp_clean_sheet` | **−0.030** | +0.014 → **+0.065** | Post-link `k_cs` inflates all-pool CS |
| `xp_conceded` | −0.004 | −0.008 → −0.017 | Mild GC scale cost |
| `xp_bonus` | −0.001 | unchanged | Not a #121 mover |

On lost segments, CS MAE regression stays ~−0.030 to −0.033; goals MAE gain ~+0.018 to +0.021 — **CS cost dominates GKP/DEF totals** while FWD goals gain does not flip mid/late Blended top-11 regret. Source: [segment_loss_121.json](segment_loss_121.json) `segments[].components`.

Season companions agree: `pool=all` CS `mse_share` rises and label → `link-bias`; `mins_60` CS bias hits τ but CS MAE worsens (0.829 → 0.882). Source: [component_gap_summary.csv](component_gap_summary.csv).

DEF/GKP CS component MAE deltas (combined): DEF CS **−0.061**; GKP CS **−0.037**. Source: [segment_loss_121.json](segment_loss_121.json) `position_blend_mae.*.defence_components`.

### Goals-only counterfactual

`goals_path_challenger` (no CS/GC scales): Blended MAE **better** than Champion (0.946 vs 0.958) and better Realized/Process MAE — but combined Blended regret **worse** (72.560 vs 71.748; Δ −0.812) and still **1/3** segments (cold_start only). Defence scales recover combined regret enough to beat Champion primary, at the cost of GKP/DEF MAE + Realized/Process guardrails. Source: [segment_loss_121_summary.csv](segment_loss_121_summary.csv); [component_gap_totals.csv](component_gap_totals.csv).

### Alternatives

- Treat Blended MAE as segment primary — rejected by code (`decision_regret` when informative).
- Blame bonus residual — rejected: `xp_bonus` MAE/bias essentially flat vs Champion on forensic slices.

## Decision

**Verdict**: Lost **`early_mid` + `late`** on Blended **`decision_regret`**; won only **`cold_start`**. Combined primary↑ is cold_start margin averaging, not broad segment strength. Losses driven by post-link **`xp_clean_sheet` inflation** (GKP/DEF Blended MAE regress) while goals arm helps FWD MAE but not mid/late top-11 regret.

**Recommended action**:
- Close #123 with this note; feed #124 route grill: mid+late Blended regret + CS all-pool overprediction vs mins_60 calibration.
- Do not `--apply` until a Candidate wins ≥2/3 segments (and MAE guardrails).

**Trigger / kill switch**:
- New Candidate that wins early_mid **or** late (plus one other) on Blended primary without Realized/Process MAE regression.

## Risks and unknowns

- Forensic recompute not the original #121 stdout artifact (CLI omits per-segment); numbers match published reasons.
- Decision Regret sensitive to top-11 set; component MAE is explanatory, not the gate object.
- Goals-only also fails segment majority — next arm must address mid/late regret, not only soft residual PASS.

## Refresh checklist

- [x] `Updated` ISO 8601 + timezone
- [x] `Data stamp` identifies cutoff
- [x] Companions in topic folder
- [x] Source synthesis vs interpretation separated
- [x] Metric Definitions present
- [x] Scratch under `.tmp/agent/` (delete after commit prep)
