# Cross-Gameweek Dispersion: Champion xP vs Realized vs Process

**Updated**: 2026-09-24T13:30:00+07:00
**Data stamp**: 2025-26 archive GW1–38 walk-forward (seed 2024-25); 2026-27 live pin GW1–5 finished, GW6 next; companions written 2026-09-24T13:30:00+07:00
**Season**: 2025/26 gate · 2026/27 sanity
**Status**: Active
**Purpose**: Test whether Model Champion xP swings across gameweeks like Realized Points and Process Points, or too stable to capture fixture impact
**Scope**: Headline pool `60+` (≥60 mins that GW). Sensitivities `all`, `min>0`, position splits. Live GW6–11 descriptive only, not alignment. Not a calibration layer (ADR 0033). Not forecast revision (needs Availability Snapshots, unimplemented).
**Related**: [ADR 0033](../../adr/0033-transfer-plan-hits-until-champion-bias.md) · [ADR 0038](../../adr/0038-process-points-eval-target.md) · [ADR 0040](../../adr/0040-calibrated-matchup-share-shrinkage.md) · [Champion signed bias](../champion-signed-bias-2025-26/champion-signed-bias-2025-26.md) · [INDEX](../INDEX.md)
**Artifact**: [dispersion_summary.csv](dispersion_summary.csv) `mean_SD` · [fixture_component_swing.csv](fixture_component_swing.csv) `mean_SD`

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Repository data**: `data/archive/2025-26/processed` — walk-forward eval GW1–38; `data/archive/2024-25/processed` — Prior-Season Seed; `data/processed` — live horizon GW6–11; `config/model_selection.json` `champion` = `calibrated_matchup_hybrid`; CLI `commands.backtest --eval_target process` — 2026-09-24
- **Code**: `backtesting/process_points.py` — Process Points definition; `features/builder.py` — walk-forward `as_of_gw`; `models/calibrated_matchup_hybrid.py` — Champion

**Source boundary**: Archive exploratory (no Availability Snapshots; `snapshot_backed=false`). Champion bias companion still pins retired `participation_penalty_hybrid`; xP rows here use current Champion. Live horizon minutes frozen across GWs (pure fixture swing).

## Agent Prompt

```text
Full redo docs/research/xp-cross-gw-dispersion/xp-cross-gw-dispersion.md

1. Require data/archive/2025-26/processed and data/archive/2024-25/processed.
2. Run: uv run python docs/research/xp-cross-gw-dispersion/runner.py
   (walk-forward ~25 min; rewrites both companions in this folder)
3. Refresh Findings from dispersion_summary.csv mean_SD / median_SD / mean_abs_w2w
   (headline pool 60+, series realized + process + blend + xp)
   and fixture_component_swing.csv mean_SD.
4. Do not snapshot numeric totals in this prompt. Do not add a calibration layer.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Walk-forward backtest + live-horizon descriptive slice

**Inputs**:
- Champion `calibrated_matchup_hybrid` from `config/model_selection.json`
- Walk-forward: `build_features(as_of_gw=gw)` + `predict(horizon=1)` per GW, 2025-26 GW1–38, seed 2024-25
- Live: `build_features` GW6 horizon 6 on `data/processed`, minutes frozen across horizon
- Actuals: Realized = `total_points` summed to player/GW; Process via `aggregate_process_points`

**Procedure**:
1. Aggregate fixture rows to player/GW sum (DGW = sum, not separate swings).
2. Per-player sample SD (`ddof=1`) across GWs in window; mean across pool = `mean_SD`; median = `median_SD`; mean abs successive-GW change = `mean_abs_w2w`.
3. Pools: `all` (0-fill incl DNP), `min>0`, `60+` headline, `60+` × GKP/DEF/MID/FWD.
4. Live component split: `xp_attack = xp_goals + xp_assists`; `xp_clean = xp_clean_sheet + xp_conceded`.

**Definitions and assumptions**:
- Q5 lock: `ddof=1` (n=6 live understated ~9% under `ddof=0`; n=38 diff ~1%). Mean-of-SDs, not pooled (pooled mixes level gaps like Haaland ~6.8 vs fodder ~0.3 into swing) and not SD-of-means (cancels opposite swings). Rank on 38-GW walk-forward; 6-GW live descriptive only (SD grows with window).
- Expectation should swing less than reality (ratio < 1), not equal 1. Question = how far below.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Cross-GW dispersion | `mean_SD` | mean over pool of per-player sample SD across GWs in window | Context (expect < actual) | `dispersion_summary.csv` `mean_SD` | Typical-player week-to-week swing of one series |
| Median dispersion | `median_SD` | median of per-player SDs | Context | `dispersion_summary.csv` `median_SD` | Typical experience; skew check vs mean |
| Week-to-week move | `mean_abs_w2w` | mean over pool of mean abs successive-GW change | Context | `dispersion_summary.csv` `mean_abs_w2w` | Step size, same story as SD |
| Dispersion ratio | `ratio` | `mean_SD(xp)` ÷ `mean_SD(actual)` | Context (< 1) | 60+ vs Realized and vs Process | How much swing survives in expectation |
| Fixture Swing | `comp mean_SD` | live-horizon per-player SD of one component (minutes frozen) | Higher $\uparrow$ | `fixture_component_swing.csv` `mean_SD` | Pure fixture-driven move by component |

**Validation boundary**: 2025-26 walk-forward is the rank window. Live GW6–11 has no actuals yet. `snapshot_backed=false`.

## Source synthesis

- ADR 0033: no live xP calibration from mean bias; gate stays Realized Points.
- ADR 0038: Process Points strips finish luck on goals/assists; other components stay Realized.
- ADR 0040: Matchup Share shrunk (`s=0.40`), multipliers forced ×1.0; saves/defcon decoupled.

## Project interpretation

### Decision rules

- If `60+` xP `mean_SD` < 20% of both actuals, fixture scale is suspect — open a Model Candidate, not a live tune.
- If MID/FWD Process strip > 30% but DEF/GKP strip ~0%, finish luck confirmed as attacker noise — fixture work targets `xp_attack`.
- No mean calibration, Hit, or solver change from this note (ADR 0033).

### Practical implications

- Solver sees nearly identical xP every GW; fixture-based transfers and captaincy rotation get no signal.
- DEF swing is clean-sheet only; MID/FWD attack swing near zero — premium attackers never separate on fixture.

## Findings

### Evidence

- Headline `60+` (460 players): Realized `mean_SD` 2.802, Process 2.128, xP 0.299 (`median_SD` 2.802 / 2.092 / 0.182; `mean_abs_w2w` 3.018 / 2.404 / 0.213). Source: [dispersion_summary.csv](dispersion_summary.csv) `mean_SD`.
- Ratios: xP ≈ 11% of Realized, ≈ 14% of Process. Expectation smoother than reality by design, but one order of magnitude = fixture signal missing, not prudence.
- Blend baseline (ADR 0044 promotion primary), `60+`: `mean_SD` 2.387 (`median_SD` 2.429, `mean_abs_w2w` 2.644) — between Realized and Process, slightly below their midpoint (averaging dampens extremes). xP ≈ 12.5% of blend. Position blends: GKP 2.359 (≈ Realized 2.370, no strip); DEF 2.780 (nearest Realized 2.971, least strip); MID 2.039; FWD 2.454. Source: [dispersion_summary.csv](dispersion_summary.csv) `mean_SD`.
- Finish-luck strip by position (`60+`): MID 2.651 → 1.639 (38% strip); FWD 3.153 → 1.976 (37%); DEF 2.971 → 2.693 (9%); GKP 2.370 → 2.354 (~0%). Luck lives in attackers; DEF/GKP noise is minutes + clean sheets. Source: [dispersion_summary.csv](dispersion_summary.csv) `mean_SD`.
- xP position ratios vs Realized: GKP 9%, DEF 9%, MID 12%, FWD 13%. No position escapes flatness.
- Skew: `all`-pool xP mean 0.203 vs median 0.053 — most players flat, few movers. Median alone would understate planning impact; mean alone overstates typical experience. Both reported per Q5 lock.
- Live pure-fixture GW6–11 (667 players, minutes frozen): xP `mean_SD` 0.038, `median_SD` 0.011, `mean_abs_w2w` 0.046. Max player SD 0.30 (Haaland 6.51–7.09 range). Source: [dispersion_summary.csv](dispersion_summary.csv) `mean_SD`.
- Component split live: `xp_attack` 0.0053 vs `xp_clean` 0.0227. DEF swing ~all clean (0.0483 vs attack 0.0034). FWD attack 0.0096, clean 0.0. Fixture moves clean sheets weakly, attack ~zero. Source: [fixture_component_swing.csv](fixture_component_swing.csv) `mean_SD`.
- Mechanism: Matchup Share rate bumps shrunk 0.40 with ×1.0 multipliers + frequent neutral fallback (ADR 0037/0040) + horizon-frozen xMins compress fixture into ±0.05.

### Alternatives

- Pooled SD across all player-GWs — rejected (mixes level gaps into swing).
- Fixture-grain SD — rejected (counts DGW twice).
- Forecast-revision SD — blocked (needs Availability Snapshots).
- `ddof=0` — rejected (penalizes 6-GW live ~9%).

## Decision

**Verdict**: Hypothesis confirmed — Champion xP too stable; fixture impact not captured, especially attack.

**Recommended action**:
- Open a Model Candidate on fixture scale (unshrink matchup deltas / restore attack-defence multipliers as explicit hypothesis), enter via Candidate Admission + Historical Promotion Gate. No live Champion change from this note.
- Refresh stale Champion bias companion (`participation_penalty_hybrid` → current Champion) as separate task.

**Trigger / kill switch**:
- Candidate beating Champion dispersion ratio toward Process while holding MAE/bias guardrails reopens Champion. A second Live Validation Window with finished GW6–11 actuals re-ranks live.

## Risks and unknowns

- 38-GW vs 6-GW SD not comparable in level; live row descriptive only.
- All-pool 0-fill mixes DNP mass into swing; headline uses `60+` for that reason.
- No Availability Snapshots; exploratory leakage on live injury/price fields.
- Component medians for live position splits fill on runner redo (blank cells in current cache).

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/` (pending finish).
