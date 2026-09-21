# Dual-Vector vs participation under Club Strength vs FDR fallback (2025-26)

**Updated**: 2026-09-22T02:50:00+07:00  
**Data stamp**: 2025-26 processed archive GW1–38; 2024-25 Prior-Season Seed; shrink sweep + ADR 0037 2026-09-22  
**Season**: 2025/26  
**Status**: Archived. Decision: [ADR 0037](../../adr/0037-fdr-fallback-multiplier-neutral.md).  
**Purpose**: Decide whether Dual-Vector beats participation, and whether Modified FDR as `attack_multiplier`/`defence_multiplier` (live 2026-27 zero-strength path) is acceptable vs Club Strength ratios.  
**Scope**: Exploratory walk-forward on `data/archive/2025-26/processed`. Forced FDR = overwrite Feature Contract multipliers with `(6−diff)/3` and `diff/3` clamp 0.4–1.8. Easy slice = `difficulty ≤ 2.0` × MID/FWD × `projected_minutes ≥ 60`. Not Solio. Not Hit policy. Not live calibration layer. Production follow-up: ADR 0037 neutral fallback (`FDR_FALLBACK_MULTIPLIER_SHRINK = 0.0`).  
**Related**: [Champion signed bias](../../research/champion-signed-bias-2025-26/champion-signed-bias-2025-26.md) · [ADR 0013](../../adr/0013-bottom-up-calibrated-component-metrics-and-rqi.md) · [ADR 0019](../../adr/0019-modified-fdr-production.md) · [ADR 0037](../../adr/0037-fdr-fallback-multiplier-neutral.md) · [archive testing](../../testing/archive-testing.md) · [INDEX](../../research/INDEX.md)  
**Artifact**: [model_regime_summary.csv](model_regime_summary.csv) `signed_bias` · [fdr_fallback_shrink_sweep.csv](fdr_fallback_shrink_sweep.csv) `signed_bias`

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Repository data**: `data/archive/2025-26/processed` evaluation; `data/archive/2024-25/processed` seed; `uv run python docs/archive/dual-vector-fdr-regime-2025-26/runner.py` — 2026-09-22
- **Glossary**: `CONTEXT.md` Club Strength Vector, Modified FDR, Dual-Vector Strength (not in production Python)

**Source boundary**: Archive exploratory (`snapshot_backed=false`). Missing actuals filled 0. Forced FDR is a research overlay; 2025-26 natural path used non-zero Club Strength attack/defence. Solio excluded from correctness (no historical Solio archive).

## Agent Prompt

```text
Full redo docs/archive/dual-vector-fdr-regime-2025-26/dual-vector-fdr-regime-2025-26.md

1. Require data/archive/2025-26/processed and data/archive/2024-25/processed.
2. Run: uv run python docs/archive/dual-vector-fdr-regime-2025-26/runner.py
3. Refresh Findings from model_regime_summary.csv signed_bias / mae / sample_count.
   Rows: model × multiplier_regime × slice (all | easy_mid_fwd).
4. Do not snapshot numeric totals in this prompt. Do not add a calibration layer.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Walk-forward backtest / regime comparison

**Inputs**:
- Models: `dual_vector_state_hybrid`, `participation_state_hybrid`
- Seed: 2024-25; evaluation GW1–38 on 2025-26 archive
- Regimes: `club_strength` (natural Feature Contract multipliers); `fdr_fallback` (overwrite to Modified FDR formula)

**Procedure**:
1. Per GW: `build_features` once; fork `fdr_fallback` via runner `apply_fdr_fallback_multipliers`.
2. Per model: `fit` on history before GW; `predict` both regimes.
3. Aggregate player/GW; fill missing actuals 0; evaluate all-pool and easy_mid_fwd slice.

**Definitions and assumptions**:
- Easy slice: mean fixture `difficulty ≤ 2.0`, `position_id` in {3,4}, `projected_minutes ≥ 60`.
- Dual-Vector Strength (rolling npxG) not tested; production Dual-Vector consumes Feature Contract multipliers only.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Signed bias | `signed_bias` | mean(`projected_points − actual_points`) | Near zero | Gate ~0; live easy-slice concern if large + | Positive = overprediction |
| MAE | `mae` | mean absolute error | Lower $\downarrow$ | Compare regimes / models | Overall forecast error |
| Easy-slice n | `sample_count` | player-GW rows in easy_mid_fwd | Context | Companion cell | Coverage of easy MID/FWD nails |

**Validation boundary**: Exploratory archive; no Availability Snapshots. Forced FDR mimics live 2026-27 zeros, not ADR 0013 Dual-Vector Strength.

## Project interpretation

### Decision rules

- If Dual-Vector and participation `signed_bias`/`mae` match within noise → Dual-Vector pen isolation is not the Haaland-class lever.
- If `fdr_fallback` easy_mid_fwd `signed_bias` ≫ `club_strength` easy_mid_fwd → live FDR multiplier fallback is the inflation mechanism to adjust.
- Solio does not decide correctness.

### Practical implications

- Keep Modified FDR as **difficulty**. Revisit FDR as **multiplier** when Club Strength attack/defence are 0.
- Demoting Champion to participation alone will not fix easy-fixture ceilings under FDR fallback.

## Findings

### Evidence

Source: [model_regime_summary.csv](model_regime_summary.csv) `signed_bias` / `mae` / `sample_count`.

| Model | Regime | Slice | n | signed_bias | mae |
|-------|--------|-------|---|-------------|-----|
| dual_vector_state_hybrid | club_strength | all | 31958 | +0.179 | 1.078 |
| participation_state_hybrid | club_strength | all | 31958 | +0.179 | 1.078 |
| dual_vector_state_hybrid | fdr_fallback | all | 31958 | +0.198 | 1.080 |
| participation_state_hybrid | fdr_fallback | all | 31958 | +0.198 | 1.080 |
| dual_vector_state_hybrid | club_strength | easy_mid_fwd | 442 | **−0.135** | 2.930 |
| dual_vector_state_hybrid | fdr_fallback | easy_mid_fwd | 442 | **+0.753** | 3.224 |
| participation_state_hybrid | club_strength | easy_mid_fwd | 442 | −0.134 | 2.929 |
| participation_state_hybrid | fdr_fallback | easy_mid_fwd | 442 | +0.784 | 3.237 |

- Dual-Vector ≈ participation on every row (δ ≪ 0.01 on all-pool; ~0.03 on easy FDR).
- All-pool FDR fallback adds only ~+0.02 signed_bias vs Club Strength.
- Easy MID/FWD: Club Strength **under**predicts (~−0.13); FDR fallback **over**predicts (~+0.75). Same n=442. MAE also worse under FDR.
- Matches live 2026-27 Haaland-shaped story: zero Club Strength → FDR multipliers inflate easy weeks.

### Alternatives

- Demote Champion to participation — rejected for this cell (no material gain; FDR easy-slice still broken).
- Drop Modified FDR as difficulty — out of scope; not tested.
- Match Solio — not correctness; no 2025-26 Solio archive.
- Ship ADR 0013 Dual-Vector Strength immediately — larger project; candidate after clamp research.

## Decision

**Verdict**: Dual-Vector vs participation is a wash on 2025-26. **FDR-as-multiplier fallback** is the problem on easy MID/FWD. Club Strength ratios on the same slice were slightly conservative, not hot.

**Recommended action** (shipped ADR 0037):
- Do not demote Dual-Vector for ceiling inflation.
- When Club Strength attack/defence are 0: `FDR_FALLBACK_MULTIPLIER_SHRINK = 0.0` → neutral ×1.0 multipliers. Keep Modified FDR as difficulty.
- Shrink sweep: [fdr_fallback_shrink_sweep.csv](fdr_fallback_shrink_sweep.csv) — shrink 0.0 easy_mid_fwd `signed_bias` ≈ −0.12 vs club_strength ≈ −0.14; raw FDR (1.0) ≈ +0.75.

**Trigger / kill switch**:
- Retune `FDR_FALLBACK_MULTIPLIER_SHRINK` if easy-slice bias drifts; restore non-zero Club Strength or Dual-Vector Strength when available.

## Risks and unknowns

- Forced FDR on 2025-26 is counterfactual (archive had non-zero strengths).
- Easy-slice n=442 is thin vs all-pool 31958.
- All-pool `signed_bias` here (~+0.18) differs slightly from ADR 0033 gate companion (+0.151); Trailing Start Window / code drift possible — not this note’s gate.
- No Availability Snapshots; exploratory leakage risk.
- Early-season `fit` reweight (live Haaland) interacts with FDR; not isolated in this design.

## Open questions

- What clamp (e.g. attack_multiplier cap &lt; 1.42) restores easy-slice bias near Club Strength without harming hard fixtures?
- Should live 2026-27 prefer Prior-Season Dual-Vector Seed multipliers over FDR fallback while API strengths stay 0?
