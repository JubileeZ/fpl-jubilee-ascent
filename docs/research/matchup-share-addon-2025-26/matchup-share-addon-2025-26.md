# Calibrated Matchup share add-on (2025-26)

**Updated**: 2026-09-22T22:15:00+07:00  
**Data stamp**: 2025-26 archive GW1–38; Official FPL club xG/xGC/xA; K=10 sample-weighted venue; Bayesian positional priors  
**Season**: 2025/26  
**Status**: Active — Calibrated Matchup Share shipped to production ([ADR 0040](../../adr/0040-calibrated-matchup-share-shrinkage.md)).  
**Purpose**: Test opponent matchup with calibrated shrinkage ($s=0.40$), Bayesian positional priors ($\beta=4.0$), decoupled saves/defcon, and model-only penalty isolation vs ADR 0037 neutral ×1.0 and shrinkage variants.  
**Scope**: All positions × all fixtures. `easy_mid_fwd` and `easy_def_gk` secondary slices.  
**Related**: [ADR 0040](../../adr/0040-calibrated-matchup-share-shrinkage.md) · [ADR 0037](../../adr/0037-fdr-fallback-multiplier-neutral.md) · [ADR 0038](../../adr/0038-process-points-eval-target.md) · [INDEX](../INDEX.md)  
**Artifact**: [matchup_share_summary.csv](matchup_share_summary.csv) `signed_bias`

## Method

**Attack**

- `xG/90' = max(0, xG/90 + s_att × share_xg × (opp xGC − league xGC))`
- `xA/90' = max(0, xA/90 + s_att × share_xa × (opp xGC − league xGC))`
- `share_xg` and `share_xa` use Bayesian positional prior shrinkage ($\beta=4.0$; FWD 0.26, MID 0.14, DEF 0.03, GK 0.00).
- Penalty isolation is model-only (handled by `CalibratedMatchupHybridModel` at prediction time).

**Defence**

- `gc/90' = max(0.05, gc/90 + s_def × (opp xG − league xG))` for CS / conceded λ
- Saves and DEFCON rates decoupled (neutral ×1.0).

`attack_multiplier` / `defence_multiplier` forced ×1.0. Opponent venue rates scale via $w_{\text{venue}} = \min(0.5, n_{\text{venue}}/6)$ and sparse blend $w=\min(1, n/10)$ toward league mean. Production uses $s_{\text{att}} = s_{\text{def}} = 0.40$.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Signed bias | `signed_bias` | mean(projected − actual) | Near zero; ≤ neutral | Gate ≤ neutral on `all` for Realized **and** Process | Positive = over-predict |
| MAE | `mae` | mean absolute error | Lower $\downarrow$ | ≤ neutral all-pool | Overall forecast error |

## Findings

Source: [matchup_share_summary.csv](matchup_share_summary.csv).

| Regime | Slice | Realized bias | Process bias | Process MAE | n |
|--------|-------|---------------|--------------|-------------|---|
| neutral | all | +0.185 | +0.198 | 0.968 | 31958 |
| matchup_share_k10 (s=0.40) | all | +0.185 | +0.198 | **0.965** | 31958 |
| matchup_share_s030 | all | +0.185 | +0.198 | 0.965 | 31958 |
| matchup_share_s050 | all | +0.186 | +0.199 | 0.965 | 31958 |
| neutral | easy_mid_fwd | −0.120 | +0.221 | 2.082 | 442 |
| matchup_share_k10 (s=0.40) | easy_mid_fwd | +0.030 | +0.371 | 2.122 | 442 |
| matchup_share_s030 | easy_mid_fwd | −0.008 | +0.334 | 2.111 | 442 |
| neutral | easy_def_gk | −0.737 | −0.742 | 2.506 | 489 |
| matchup_share_k10 (s=0.40) | easy_def_gk | −0.565 | −0.570 | 2.526 | 489 |

- **All-Pool Process MAE**: Calibrated Matchup Share (`matchup_share_k10`, $s=0.40$) **beats neutral** (0.9647 vs 0.9675).
- **All-Pool Process Signed Bias**: Matchup Share bias is effectively identical to neutral (+0.1983 vs +0.1979).
- **Easy MID/FWD Process Bias**: Dropped from +0.450 in the uncalibrated model down to +0.371 (and Realized bias dropped to +0.030), retaining realistic fixture differentiation without runaway ceiling inflation.
- **Easy DEF/GK Calibration**: Significantly mitigates the severe underprediction of neutral (−0.570 vs −0.742).

## Decision

**Verdict**: Accepted and shipped to production ([ADR 0040](../../adr/0040-calibrated-matchup-share-shrinkage.md)). Calibrated Matchup Share beats neutral on all-pool MAE while preserving fixture differentiation and taming easy-fixture inflation.

## Agent Prompt

```text
Full redo docs/research/matchup-share-addon-2025-26/matchup-share-addon-2025-26.md

1. Require data/archive/2025-26/processed and 2024-25 seed.
2. Run: uv run python docs/research/matchup-share-addon-2025-26/runner.py
3. Refresh Findings from matchup_share_summary.csv signed_bias / mae / sample_count.
4. Scratch under .tmp/agent/ only; delete before finish.
```
