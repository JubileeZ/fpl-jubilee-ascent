# Champion signed bias vs Realized Points (2025-26 gate)

**Updated**: 2026-09-15T00:15:00+07:00  
**Data stamp**: 2025-26 processed archive GW1–38; 2024-25 Prior-Season Seed; 2026-27 pin GW1–3 sanity; companion written 2026-09-15T00:14:45+07:00  
**Season**: 2025/26 gate · 2026/27 sanity  
**Status**: Active  
**Purpose**: Measure Model Champion `participation_penalty_hybrid` signed bias (`projected_points − actual_points`) vs Realized Points before any Hit ban or xP calibration layer (ADR 0033).  
**Scope**: Gate = 2025-26 GW1–38. Sanity = 2026-27 finished GW1–3 only. Not FPL `ep_*`. Not third-party xP. Not Hit-allowed vs Hit-forbidden walk-forward. Not a calibration layer.  
**Related**: [ADR 0033](../../adr/0033-transfer-plan-hits-until-champion-bias.md) · [ADR 0032](../../adr/0032-live-season-pin-official-only.md) · [INDEX](../INDEX.md) · [archive testing](../../testing/archive-testing.md)  
**Artifact**: [champion_bias_summary.csv](champion_bias_summary.csv) `signed_bias`

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Primary**: [ADR 0033](../../adr/0033-transfer-plan-hits-until-champion-bias.md) — accepted 2026-09-14; role: gate window, Champion model, no calibration until this measurement
- **Repository data**: `data/archive/2025-26/processed` — evaluation; `data/archive/2024-25/processed` — Prior-Season Seed; `data/archive/2026-27/processed` — sanity; `config/model_selection.json` `champion`; CLI `uv run python -m commands.measure_champion_bias` — 2026-09-15

**Source boundary**: Archive exploratory (no Availability Snapshots; `snapshot_backed=false`). Missing actuals filled 0 at player/gameweek grain. Community “almost never Hit” is unvalidated folklore, not a source here.

## Agent Prompt

```text
Full redo docs/research/champion-signed-bias-2025-26/champion-signed-bias-2025-26.md

1. Require data/archive/2025-26/processed and data/archive/2024-25/processed.
2. Run: uv run python docs/research/champion-signed-bias-2025-26/runner.py
   (same as: uv run python -m commands.measure_champion_bias)
3. Refresh Findings from champion_bias_summary.csv signed_bias / mae / sample_count / minutes_bias.
   Gate row: evaluation_season=2025-26 gw_start=1 gw_end=38.
   Sanity row: evaluation_season=2026-27 (finished GWs only).
4. Do not snapshot numeric totals in this prompt. Do not add a calibration layer.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Walk-forward backtest (ADR 0033 gate)

**Inputs**:
- Champion `participation_penalty_hybrid` from `config/model_selection.json`
- Evaluation: `data/archive/2025-26/processed` GW1–38
- Prior-Season Seed: `data/archive/2024-25/processed`
- Sanity: `data/archive/2026-27/processed` GW1–3; seed `2025-26`

**Procedure**:
1. `run_walkforward_backtest` per Gameweek: Feature Contract `as_of_gw`, `use_archive_seed=False`, Champion `predict`, Projection Contract check.
2. Aggregate fixture rows to player/gameweek. Left-join Realized Points; missing actuals = 0.
3. `signed_bias` = mean(`projected_points` − `actual_points`) on that eval frame.
4. Write [champion_bias_summary.csv](champion_bias_summary.csv). No live `hit_cost` / `weekly_hit_limit` change.

**Definitions and assumptions**:
- Signed bias positive = overprediction
- Grain = every Feature Contract player each Gameweek, not scoring-15
- Exploratory archive; not Historical Promotion Gate

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Champion signed bias | `signed_bias` | $\mathrm{mean}(\text{projected\_points} - \text{actual\_points})$ | Near zero | Gate cell in `champion_bias_summary.csv` `signed_bias` | Positive = overprediction vs Realized Points. Not FPL `ep_*`. |
| Points MAE | `mae` | $\mathrm{mean}\| \text{projected\_points} - \text{actual\_points} \|$ | Lower $\downarrow$ | Context | Absolute error on the same eval frame |
| Minutes bias | `minutes_bias` | $\mathrm{mean}(\text{projected\_minutes} - \text{actual\_minutes})$ | Near zero | Context | Minutes over/under; not the Hit gate |

**Validation boundary**: 2025-26 is the gate. 2026-27 has three finished GWs only. `snapshot_backed=false`. Including players with filled-0 actuals raises mean overprediction vs a minutes>0 subset.

## Source synthesis

### Main claims

- ADR 0033: keep live `hit_cost=4`, `weekly_hit_limit=1`. Do not forbid Hits by default. Do not add a calibration layer until Champion signed bias is measured on 2025-26 GW1–38.

### Source rationale

- Live-season tune on 2026-27 leaks the season being played. Third-party xP is Research-Only Evidence.

## Project interpretation

### Decision rules

- If gate `signed_bias` exists in the companion, the ADR 0033 measurement gate is satisfied.
- Do not add a calibration layer, raise `hit_cost`, or set `weekly_hit_limit=0` from this cell.
- A later Hit-allowed vs Hit-forbidden walk-forward may still add a robustness margin.

### Practical implications

- Live Transfer Plan Hits stay allowed. Remaining Hits after mean calibration (if ever added) are taken.

## Findings

### Evidence

- Gate row `evaluation_season=2025-26` `gw_start=1` `gw_end=38` `seed_season=2024-25`: `sample_count` 31958 (841 players × 38 GWs); `signed_bias` +0.1512; `mae` 1.0729; `minutes_bias` +2.09; `snapshot_backed` false. Source: [champion_bias_summary.csv](champion_bias_summary.csv) `signed_bias`.
- Sanity row `evaluation_season=2026-27` `gw_start=1` `gw_end=3` `seed_season=2025-26`: `sample_count` 1974; `signed_bias` +0.2140; `mae` 1.4067; `minutes_bias` +2.64. Three finished GWs only.
- Both windows overpredict on the all-player grain. Magnitude is ~0.15 points per player-GW on the gate, not a 4-point Hit-scale mean miss.
- Independent CLI `commands.backtest` on the same 2025-26 window printed Signed Bias 0.1512 / MAE 1.0729 / n=31958 — same gate cells.

### Alternatives

- Calibrate mean xP or raise `hit_cost` — rejected (ADR 0033).
- Evaluate only minutes>0 rows — not this grain; would change `signed_bias`.
- Forbid Hits in live solve to match walk-forward research policy — rejected.

## Decision

**Verdict**: ADR 0033 gate measurement exists. Keep live Hits. Do not add a calibration layer.

**Recommended action**:
- Leave `hit_cost=4` and `weekly_hit_limit=1`.
- Refresh the companion with `uv run python -m commands.measure_champion_bias` when the 2025-26 archive or Champion changes.

**Trigger / kill switch**:
- Hit-allowed vs Hit-forbidden walk-forward on 2025-26, or a new Champion, can reopen calibration. Not a silent default change.

## Risks and unknowns

- All-player grain with actual=0 fill is not a scoring-15 bias.
- No Availability Snapshots; exploratory leakage on live injury/price fields.
- 2026-27 sanity n is small and the pin is unfinished.
- Component-level bias (minutes vs goals) is in `commands.backtest --component_breakdown`, not this companion.

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
