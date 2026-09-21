# Official FPL Dual-Vector multipliers (2025-26)

**Updated**: 2026-09-22T03:35:00+07:00  
**Data stamp**: 2025-26 processed archive GW1–38; 2024-25 Prior-Season Seed; companion includes Realized + Process Targets (ADR 0038) 2026-09-22  
**Season**: 2025/26  
**Status**: Active  
**Purpose**: Test Official FPL Dual-Vector Strength multipliers (ratio to league avg; 50% all-venue + 50% H/A; sparse → league avg) as replacement for FDR-as-multiplier / ADR 0037 neutral ×1.0.  
**Scope**: Research overlay on Feature Contract multipliers only. Walk-forward `dual_vector_state_hybrid`. Score vs Realized Points and Process Points. Not npxG. Not Explorer difficulty remapping. Not production wire.  
**Related**: [FDR regime](../dual-vector-fdr-regime-2025-26/dual-vector-fdr-regime-2025-26.md) · [ADR 0013](../../adr/0013-bottom-up-calibrated-component-metrics-and-rqi.md) · [ADR 0037](../../adr/0037-fdr-fallback-multiplier-neutral.md) · [ADR 0038](../../adr/0038-process-points-eval-target.md) · [INDEX](../INDEX.md)  
**Artifact**: [dual_vector_xg_summary.csv](dual_vector_xg_summary.csv) `signed_bias` (`eval_target` realized|process)

## Sources

- **Repository data**: `data/archive/2025-26/processed` `player_performances` / `fixtures`; `uv run python docs/research/dual-vector-official-xg-2025-26/runner.py`
- **Glossary**: Dual-Vector Strength; Prior-Season Dual-Vector Seed (FPL-xG proxy)

**Source boundary**: Archive exploratory. Club xG = Σ `expected_goals`; club xGC = max `expected_goals_conceded` among minutes ≥ 60. Official FPL only.

## Agent Prompt

```text
Full redo docs/research/dual-vector-official-xg-2025-26/dual-vector-official-xg-2025-26.md

1. Require data/archive/2025-26/processed and data/archive/2024-25/processed.
2. Run: uv run python docs/research/dual-vector-official-xg-2025-26/runner.py
3. Refresh Findings from dual_vector_xg_summary.csv signed_bias / mae / sample_count / eval_target.
4. Report both realized and process easy_mid_fwd. Do not wire production.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Walk-forward backtest / multiplier regime comparison

**Inputs**:
- Model: `dual_vector_state_hybrid` (fit history before each GW)
- Regimes: `club_strength` (natural), `neutral` (×1.0), `raw_fdr`, `dual_vector_k6`, `dual_vector_k10`
- Dual-Vector: for each club before GW, last ≤K finished club-fixtures; rate′ = 0.5·mean_all + 0.5·mean_venue; blend `w·rate′ + (1−w)·league_avg` with `w=min(1,n/K)`; attack_str = xG/league_xG; defence_str = league_xGC/xGC; multipliers = clip(team/opp, 0.4, 1.8)

**Procedure**:
1. Build club-fixture xG/xGC table once.
2. Per GW: `build_features`; overlay regime multipliers; predict; attach Realized Points and Process Points.
3. Slices: all; easy_mid_fwd (`difficulty ≤ 2`, MID/FWD, `projected_minutes ≥ 60`).
4. Emit companion rows for `eval_target` = realized and process.

### Metric Definitions & Direction

| Metric | Symbol | Definition | Direction | Ideal / Benchmark |
|---|---|---|---|---|
| Signed bias | `signed_bias` | mean(proj − target) | Near zero | Easy-slice ≤ neutral; not raw FDR |
| MAE | `mae` | mean abs error vs target | Lower $\downarrow$ | Not worse than club_strength by much |

**Validation boundary**: Exploratory; no Availability Snapshots. Success bar on **both** Realized and Process: beat `neutral` and `raw_fdr` on easy_mid_fwd; report vs `club_strength`.

## Project interpretation

### Decision rules

- If Dual-Vector easy_mid_fwd `signed_bias` worse than `neutral` on Realized **or** Process → do not replace ADR 0037.
- If Dual-Vector beats `raw_fdr` but not `neutral` → FDR problem remains solved by neutral; Dual-Vector not ready.
- Explorer 1–5 difficulty remapping out of scope until multipliers win.

## Findings

### Evidence

Source: [dual_vector_xg_summary.csv](dual_vector_xg_summary.csv) `signed_bias`.

**Realized Points** (finish luck included):

| Regime | Slice | n | signed_bias | mae |
|--------|-------|---|-------------|-----|
| club_strength | easy_mid_fwd | 442 | **−0.135** | 2.930 |
| neutral | easy_mid_fwd | 442 | **−0.120** | 2.936 |
| dual_vector_k10 | easy_mid_fwd | 442 | **+0.396** | 3.117 |
| raw_fdr | easy_mid_fwd | 442 | **+0.753** | 3.224 |

**Process Points** (goals/assists from Official xG/xA; ADR 0038):

| Regime | Slice | n | signed_bias | mae |
|--------|-------|---|-------------|-----|
| club_strength | easy_mid_fwd | 442 | **+0.206** | 2.082 |
| neutral | easy_mid_fwd | 442 | **+0.221** | 2.082 |
| dual_vector_k10 | easy_mid_fwd | 442 | **+0.737** | 2.313 |
| raw_fdr | easy_mid_fwd | 442 | **+1.094** | 2.435 |

- Process MAE is lower than Realized (less goal/assist noise) for every regime.
- Dual-Vector still **fails** vs `neutral` on Process easy_mid_fwd (+0.74 vs +0.22) — not explained by finish luck.
- Dual-Vector still beats `raw_fdr` on both targets; not enough to ship.
- All-pool Process MAE: club_strength 0.964 · neutral 0.968 · DV_k10 0.984 · raw_fdr 0.966.

### Alternatives

- Wire Dual-Vector into production now — rejected (fails vs neutral on Realized and Process).
- Softer clip / shrink Dual-Vector toward 1.0 — open follow-up; not this cell.
- Research npxG Dual-Vector (ADR 0013 literal) — Research-Only; separate topic.

## Decision

**Verdict**: Official FPL Dual-Vector multipliers **not ready** to replace ADR 0037 neutral ×1.0 under Realized **or** Process evaluation. Keep Modified FDR as difficulty only; keep neutral multipliers when Club Strength attack/defence are 0.

**Recommended action**:
- Leave production on ADR 0037.
- Optional follow-up: shrink Dual-Vector ratios toward 1.0 (`1 + s·(r−1)`) and re-run both eval targets.

**Trigger / kill switch**:
- Easy-slice Dual-Vector `signed_bias` ≤ neutral on **both** Realized and Process, and all-pool Process MAE ≤ club_strength + ε → reopen production ADR.

## Risks and unknowns

- FPL `expected_goals` is not npxG; may double-count set pieces vs ADR 0013 intent.
- Opponent venue = `not is_home` of focal row; DGW / blank weeks not special-cased.
- Early GWs heavily league-avg blended; may understate true Dual-Vector once n≥K mid-season only.

## Open questions

- Does a Dual-Vector shrink (like FDR shrink sweep) recover neutral-level easy bias while beating neutral MAE?
- Should sparse prior be Prior-Season Dual-Vector Seed instead of league avg?
