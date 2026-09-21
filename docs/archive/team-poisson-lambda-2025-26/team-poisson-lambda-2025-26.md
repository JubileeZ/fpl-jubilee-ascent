# Team Poisson λ multipliers (2025-26)

**Updated**: 2026-09-22T04:05:00+07:00  
**Data stamp**: 2025-26 archive GW1–38; K=10 Official FPL club xG/xGC; Realized + Process (ADR 0038)  
**Season**: 2025/26  
**Status**: Archived. Decision: [ADR 0037](../../adr/0037-fdr-fallback-multiplier-neutral.md).  
**Purpose**: Test team-λ Poisson fixture scaling (top-model pattern) vs neutral ×1.0 and Club Strength.  
**Scope**: Multiplier overlay on Champion predict. Not a separate CS Poisson rewrite. Not production.  
**Related**: [Official Dual-Vector](../dual-vector-official-xg-2025-26/dual-vector-official-xg-2025-26.md) · [ADR 0037](../../adr/0037-fdr-fallback-multiplier-neutral.md) · [ADR 0038](../../adr/0038-process-points-eval-target.md)  
**Artifact**: [team_poisson_summary.csv](team_poisson_summary.csv) `signed_bias`

## Method

**Variants** (history before GW; 0.5 all-venue + 0.5 H/A; sparse `w=min(1,n/10)` toward league avg; clip 0.4–1.8):

- `poisson_opp_k10`: attack_mult = opp xGC / league xGC; defence_mult = opp xG / league xG. Own attack stays inside player rates (no double count).
- `poisson_full_k10`: attack_mult = (team xG / league) × (opp xGC / league). Reapplies own attack. Algebra matches prior Dual-Vector ratio `team_att / opp_def`.

Gate: easy_mid_fwd `signed_bias` ≤ neutral on **both** Realized and Process.

## Findings

Source: [team_poisson_summary.csv](team_poisson_summary.csv). Easy MID/FWD n=442.

| Regime | Realized bias | Process bias | Process MAE |
|--------|---------------|--------------|-------------|
| club_strength | −0.135 | +0.206 | 2.082 |
| neutral | −0.120 | +0.221 | 2.082 |
| poisson_opp_k10 | +0.150 | +0.491 | 2.195 |
| poisson_full_k10 | +0.396 | +0.737 | 2.313 |

- `poisson_full` cells match prior `dual_vector_k10` (same ratio). Not a new model.
- `poisson_opp` beats full / raw-style Dual-Vector, still **worse than neutral** on both targets.
- All-pool Process MAE: club 0.964 · neutral 0.968 · opp 0.973 · full 0.984.

## Decision

**Verdict**: Do not replace ADR 0037. Opponent-relative Poisson scaling over-predicts easy fixtures vs neutral. Keep Champion; keep neutral ×1.0 when Club Strength is 0.

**Next only if reopened**: true scoreline Poisson (player share × λ, CS = e^{−λ_against}) rather than another rate multiplier — this overlay is not that layer.
