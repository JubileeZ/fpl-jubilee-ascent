# Transfer Plan Walk-Forward — 2025-26 First-Half

**Updated**: 2026-08-26T02:45:00+07:00  
**Data stamp**: 2025-26 processed archive on disk; 2024-25 Prior-Season Seed absent  
**Season**: 2025/26  
**Status**: Blocked pending 2024-25 ingest  
**Purpose**: Rank Starting Shape, Transfer Target Policy, and Defcon-Floor vs Attack-Ceiling tilts on 2025-26 First-Half as 2026/27 playbook evidence  
**Scope**: GW1–19. No chips. No Hits. Free Transfer Bank cap 5. Unconstrained baseline plus OAT arms. Club Occupancy is diagnostic only. Not model MAE. Not hindsight oracle. Not GW20–38.  
**Related**: [ADR 0019](../../adr/0019-transfer-plan-walk-forward-first-half.md) · [INDEX](../INDEX.md) · [First-Half 5-DEF Rotation](../def-fdr-rotation-gw1-19/def-fdr-rotation-gw1-19.md)  
**Artifact**: [tp_walkforward_summary.csv](tp_walkforward_summary.csv) `realized_points` · [def_rotation_club_occupancy.csv](def_rotation_club_occupancy.csv) `rank_mod_fdr`

## Sources

- **Primary**: Confirmed grill protocol 2026-08-26 (ADR 0019)
- **Repository data**: `data/archive/2025-26/processed` — occupancy FDR; Transfer Plan Walk-Forward blocked without `data/archive/2024-25/processed`

**Source boundary**: Occupancy companion uses archive Official Fixture Difficulty. Walk-forward ranking not computed until Prior-Season Seed exists. Exploratory: no Availability Snapshots.

## Agent Prompt

```text
Full redo docs/research/tp-walkforward-gw1-19-2025-26/tp-walkforward-gw1-19-2025-26.md

1. Require data/archive/2024-25/processed (ingest via commands.snapshot_season --season 2024-25 --from-raw-dir).
2. Run: uv run python docs/research/tp-walkforward-gw1-19-2025-26/runner.py
3. Verify tp_walkforward_summary.csv realized_points and def_rotation_club_occupancy.csv rank_mod_fdr.
4. Refresh Findings from companions; do not snapshot numeric totals in the Agent Prompt.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Transfer Plan Walk-Forward

**Inputs**:
- 2025-26 processed archive
- 2024-25 processed archive (Prior-Season Seed + minutes prior)
- Model Champion, `minutes_prior_source=seed_state`

**Procedure**:
1. Greenfield GW1 Transfer Plan, £100m, no chips.
2. Each later deadline: Planning Horizon 5 clipped at GW19; spend Free Transfer Bank only; never a Hit.
3. Score scoring-15 Realized Points with autosubs and solved captain.
4. OAT families: Locked Starting Shape; Transfer Target Policy; Defcon-Floor / Attack-Ceiling tilts. Then one winner cross.
5. Club Occupancy FDR on 2025-26 fixtures as diagnostic.

**Definitions and assumptions**:
- Did-Not-Play Exception: deadline `p_dnp ≥ 0.5`
- Defcon-Floor: DEF/MID `xP + xp_defcon`
- Attack-Ceiling: DEF/MID `xP - xp_defcon`
- GKP counts as defence for Transfer Target Policy

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| First-Half Realized Points | `realized_points` | $\sum_{g=1}^{19}$ scoring-15 Realized Points after autosubs, minus Hits (Hits forbidden so 0) | Higher $\uparrow$ | Unconstrained baseline | Ranking object for each walk-forward arm |
| Occupancy rank | `rank_mod_fdr` | Ordinal after $(\text{total\_mod\_fdr}, \text{occupancy\_key})$ | Lower $\downarrow$ | 1 | Diagnostic Club Occupancy only; not the strategy winner |

**Validation boundary**: Archive exploratory. Walk-forward ranking blocked until 2024-25 ingest. Occupancy uses terminal 2025-26 fixtures/FDR.

## Source synthesis

### Main claims

- Protocol forbids chips, Hits, hindsight 15s, and Expected Role Table minutes for 2025-26 Cold-Start.

### Source rationale

- Isolates shape / FT policy / tilt. GW1 playbook needs Prior-Season Seed.

## Project interpretation

### Decision rules

- If `tp_walkforward_summary.csv` `status` is `blocked_missing_prior_season_seed`, do not pick a 2026/27 Starting Shape from this note.
- Occupancy `rank_mod_fdr` may inform DEF Club Occupancy discussion only.

### Practical implications

- First implementation step remains 2024-25 raw ingest.

## Findings

### Evidence

- Transfer Plan Walk-Forward ranking: blocked. See `tp_walkforward_summary.csv` `status`.
- Club Occupancy companion generated from 2025-26 archive fixtures when runner ran.

### Alternatives

- Position-Price Prior at GW1 (rejected). Start ranking at GW5 (rejected).

## Decision

**Verdict**: No 2026/27 Starting Shape / Transfer Target / tilt playbook until 2024-25 archive exists and walk-forward `realized_points` is filled.

**Recommended action**:
- Ingest 2024-25 via `uv run python -m commands.snapshot_season --season 2024-25 --from-raw-dir <raw>`
- Re-run topic runner

**Trigger / kill switch**:
- Seed present and summary `status=ok` → rank arms by `realized_points`

## Risks and unknowns

- Live FPL API cannot snapshot 2024-25
- No Availability Snapshots on origin
- MILP walk-forward loop not executed while seed is missing
