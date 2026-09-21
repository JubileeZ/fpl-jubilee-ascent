# Matchup share add-on (2025-26)

**Updated**: 2026-09-22T05:35:00+07:00  
**Data stamp**: 2025-26 archive GW1–38; Official FPL club xG/xGC/xA; K=10 blended venue  
**Season**: 2025/26  
**Status**: Active — research measured fail vs neutral; **shipped to production** with Club Strength → neutral cold-start (ADR 0037 revised).  
**Purpose**: Test opponent matchup as rate add-on (goals/assists by player share; team λ for CS/GC; saves/defcon ratio) vs ADR 0037 neutral ×1.0.  
**Scope**: Research overlay measured on Champion feature rates; now wired in production via `features/matchup_share.py` (ADR 0037). Primary gate was all positions × all fixtures. `easy_mid_fwd` secondary.  
**Related**: [ADR 0037](../../adr/0037-fdr-fallback-multiplier-neutral.md) · [ADR 0038](../../adr/0038-process-points-eval-target.md) · [Team Poisson archive](../../archive/team-poisson-lambda-2025-26/team-poisson-lambda-2025-26.md) · [INDEX](../INDEX.md)  
**Artifact**: [matchup_share_summary.csv](matchup_share_summary.csv) `signed_bias`

## Method

**Attack**

- `xG/90' = max(0, xG/90 + (player xG / club xG) × (opp xGC − league xGC))`
- `xA/90' = max(0, xA/90 + (player xA / club xA) × (opp xGC − league xGC))`
- `penalties_order==1`: add-on on open-play only (~0.15 xG/90 held out)

**Defence**

- `gc/90' = max(0.05, gc/90 + (opp xG − league xG))` for CS / conceded λ
- saves and defcon rates × `(opp xG / league xG)`

`attack_multiplier` / `defence_multiplier` forced ×1.0. Club rates: 0.5 all-venue + 0.5 H/A, sparse blend `w=min(1,n/10)` toward league mean.

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
| matchup_share_k10 | all | +0.200 | +0.213 | 0.971 | 31958 |
| neutral | easy_mid_fwd | −0.120 | +0.221 | 2.082 | 442 |
| matchup_share_k10 | easy_mid_fwd | +0.109 | +0.450 | 2.176 | 442 |

- All-pool: matchup worse than neutral on Realized and Process (~+0.015 bias; MAE also worse).
- Easy MID/FWD: same inflation pattern as opponent-ratio arms (Process +0.45 vs neutral +0.22).

## Decision

**Verdict**: All-pool bias worse than neutral on 2025-26. **Product override**: production uses Matchup Share when this-season Official club xG exists; cold-start falls back Club Strength then neutral (ADR 0037).

**Recommended action**: Keep companion as gate evidence. Retune or kill if live signed bias drifts vs Champion bias companion.

## Risks and unknowns

- Share from cumulative Official xG/xA (includes pens in share numerator except open-play holdout on the add-on only).
- Early GWs heavily league-blended.
- Saves/defcon ratio and CS add-on shipped together; not ablated.

## Agent Prompt

```text
Full redo docs/research/matchup-share-addon-2025-26/matchup-share-addon-2025-26.md

1. Require data/archive/2025-26/processed and 2024-25 seed.
2. Run: uv run python docs/research/matchup-share-addon-2025-26/runner.py
3. Refresh Findings from matchup_share_summary.csv signed_bias / mae / sample_count.
4. Scratch under .tmp/agent/ only; delete before finish.
```
