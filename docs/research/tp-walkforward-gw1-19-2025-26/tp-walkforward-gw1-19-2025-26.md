# Transfer Plan Walk-Forward — 2025-26 First-Half

**Updated**: 2026-08-27T15:22:00+07:00  
**Data stamp**: 2025-26 processed archive; 2024-25 vaastav seed; `tp_walkforward_summary.csv` written 2026-08-27T15:19:16+07:00  
**Season**: 2025/26 evidence → 2026/27 First-Half playbook  
**Status**: Ranked  
**Purpose**: Rank Starting Shape, Transfer Target Policy, and Defcon-Floor vs Attack-Ceiling tilts on 2025-26 GW1–19 as 2026/27 playbook evidence. Answer: how to draft and spend Free Transfers in the first half of this season.  
**Scope**: GW1–19 only. Hits forbidden. BB/FH/TC off. GW1 empty-squad construction uses solver Wildcard (MILP Free Transfer ub=5). Free Transfer Bank cap 5 after GW1. Unconstrained baseline plus one-factor-at-a-time (OAT) arms, then one winner cross. Club Occupancy is diagnostic only. Not model MAE. Not a hindsight 15. Not GW20–38. Not Chip Set 2.  
**Related**: [ADR 0020](../../adr/0020-transfer-plan-walk-forward-first-half.md) · [INDEX](../INDEX.md) · [First-Half 5-DEF Rotation](../def-fdr-rotation-gw1-19/def-fdr-rotation-gw1-19.md) · [First-Half GKP Rotation](../gkp-fdr-rotation-gw1-19/gkp-fdr-rotation-gw1-19.md)  
**Artifact**: [tp_walkforward_summary.csv](tp_walkforward_summary.csv) `realized_points` · [def_rotation_club_occupancy.csv](def_rotation_club_occupancy.csv) `rank_mod_fdr`

## Sources

- **Primary**: Grill protocol 2026-08-26 (ADR 0020); vaastav ingest 2026-08-27
- **Secondary**: [vaastav/Fantasy-Premier-League `data/2024-25`](https://github.com/vaastav/Fantasy-Premier-League/tree/master/data/2024-25) — frozen end of 2024-25; accessed 2026-08-27; role: Prior-Season Seed CSVs (`players_raw.csv`, `teams.csv`, `fixtures.csv`, `gws/merged_gw.csv`)
- **Repository data**: `data/archive/2025-26/processed` — evaluation season (projections, realized scores, occupancy FDR); `data/archive/2024-25/processed` — seed mapped from `data/archive/2024-25/vaastav`; CLI `uv run python -m commands.transfer_plan_walkforward` — 2026-08-27

**Source boundary**: Occupancy uses archive Official Fixture Difficulty on 2025-26 fixtures (terminal metadata). Seed has no `defensive_contribution` (not an FPL scoring component in 2024-25). vaastav `xP` unused (possible lookahead). Exploratory: no Availability Snapshots. FPL-Core Insights 2024-2025 Opta dump not used (no FPL minutes/starts table).

## Agent Prompt

```text
Full redo docs/research/tp-walkforward-gw1-19-2025-26/tp-walkforward-gw1-19-2025-26.md

1. Require data/archive/2024-25/processed (ingest via commands.snapshot_season --season 2024-25 --from-vaastav-dir data/archive/2024-25/vaastav).
2. Run: uv run python -m commands.transfer_plan_walkforward
3. Verify tp_walkforward_summary.csv realized_points and def_rotation_club_occupancy.csv rank_mod_fdr.
4. Refresh Findings from companions; do not snapshot numeric totals in the Agent Prompt.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Transfer Plan Walk-Forward

Replay 2025-26 First-Half deadlines as if each Transfer Plan were solved at that deadline using only history before it, then score the squad that actually took the field.

**Why this object.** A hindsight 15 already knows who became essential. `commands.backtest` MAE ranks models, not formation / FT policy. This ranking is the analog of 2026/27 Cold-Start: empty current-season history at GW1, Prior-Season Seed from the previous archive, then unfolding 2025-26 appearances via Appearance Blend.

**Inputs**:
- Evaluation: `data/archive/2025-26/processed` (players, performances, fixtures, clubs)
- Prior-Season Seed: `data/archive/2024-25/processed` (vaastav CSVs → parquet; FPL `code` join; `minutes` + `starts` for `seed_state`)
- Model Champion `participation_state_hybrid`; `minutes_prior_source=seed_state` (not 2026/27 Expected Role Table)
- Per-deadline `price` from `player_performances` (not terminal `now_cost`)

**Procedure**:
1. **GW1.** Greenfield £100m, empty 15. Solver Wildcard on so the 15-man draft is not Hits (MILP Free Transfer variable ub=5; 15 FTs infeasible). BB/FH/TC remain off. Planning Horizon 5.
2. **GW2–19.** History = 2025-26 performances with `gameweek_id` < deadline. Horizon 5 clipped at GW19. Spend Free Transfer Bank only (cap 5); `weekly_hit_limit=0`. Chips off. Did-Not-Play Exception: owned player with deadline `p_dnp ≥ 0.5` may be transferred even if the FT policy would lock that Position.
3. **Score.** That GW’s scoring 15 after autosubs + solved captain, using Realized Points. Sum GW1–19. Hits forbidden so hit cost = 0.
4. **OAT.** Unconstrained baseline; then one family at a time (shape / FT target / tilt). Family winners combined in one cross arm.
5. **Occupancy.** 2025-26 Club Occupancy FDR companion is diagnostic only — not the strategy winner.

**Arms** (10 OAT + 1 cross):

| Family | Arms |
|--------|------|
| Baseline | Unconstrained shape, unconstrained FT, vanilla xP |
| Locked Starting Shape | 3-4-3, 3-5-2, 4-3-3, 4-4-2, 4-5-1 (XI min=max by Position) |
| Transfer Target | Attack = lock GKP+DEF (GKP counts as defence); Defence = lock MID+FWD |
| Tilt | Defcon-Floor: DEF/MID `xP + xp_defcon`; Attack-Ceiling: DEF/MID `xP - xp_defcon` |
| Cross | Winners of shape + FT + tilt families |

**Definitions and assumptions**:
- Scoring 15 = lineup 11 + autosubs + captain multiplier from the solved plan
- Did-Not-Play Exception: deadline `p_dnp ≥ 0.5`
- After GW1, `ft_bank` starts at 1 and accrues with `next_free_transfer_bank` (cap 5)
- 311 / 841 of 2025-26 players had `seed_source=player_prior` at GW1; remainder Position-Price Prior (no 2024-25 `code` match or thin minutes)

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| First-Half Realized Points | `realized_points` | $\sum_{g=1}^{19}$ scoring-15 Realized Points after autosubs; Hits forbidden so 0 | Higher $\uparrow$ | Unconstrained baseline | Ranking object for each walk-forward arm |
| Occupancy rank | `rank_mod_fdr` | Ordinal after $(\text{total\_mod\_fdr}, \text{occupancy\_key})$ | Lower $\downarrow$ | 1 | Diagnostic Club Occupancy only; not the strategy winner |

**Validation boundary**: Archive exploratory. Occupancy uses terminal 2025-26 fixtures/FDR. Seed from vaastav per-GW CSVs, not FPL `element_summary` JSON. Leftover ITB not chained across deadlines. GW1 Wildcard is construction, not a playbook chip.

## Source synthesis

### Main claims

- Protocol forbids Hits, BB/FH/TC, hindsight 15s, and Expected Role Table minutes for 2025-26 Cold-Start.
- Prior-Season Seed must be 2024-25 FPL minutes/starts/event rates, not Opta match stats and not 2025-26 GW1–5 labeled as a prior season.
- Live FPL API cannot snapshot 2024-25; vaastav CSVs are the public per-GW FPL dump used here.

### Source rationale

- Isolates shape / FT policy / tilt. Production 2026/27 Cold-Start has 2025-26 seed + Expected Role minutes; this replay uses 2024-25 seed + 2024-25 realized minutes so GW1 is the same *kind* of problem.

## Project interpretation

### Decision rules

- Rank 2026/27 First-Half squad policy from `tp_walkforward_summary.csv` `realized_points` where `status=ok`.
- Do not pick Starting Shape from occupancy `rank_mod_fdr`.
- Do not use Defence Transfer Target from this ranking (`ft_defence` far below baseline).
- Occupancy `rank_mod_fdr` may inform DEF Club Occupancy discussion only (sibling 5-DEF note).

### Practical implications

- Re-run: `uv run python -m commands.snapshot_season --season 2024-25 --from-vaastav-dir data/archive/2024-25/vaastav` then `uv run python -m commands.transfer_plan_walkforward`.

## Findings

### Evidence

Companion [tp_walkforward_summary.csv](tp_walkforward_summary.csv): 11 rows, all `status=ok`, `realized_points` filled. Window GW1–19. Baseline = 1051.

**OAT ranking** (cache of `arm_id`, `realized_points`):

| `arm_id` | Family | `realized_points` | vs baseline |
|----------|--------|-------------------|-------------|
| `ft_attack` | FT | 1081 | +30 |
| `shape_3-4-3` | Shape | 1057 | +6 |
| `shape_4-5-1` | Shape | 1055 | +4 |
| `tilt_defcon_floor` | Tilt | 1055 | +4 |
| `baseline` | Baseline | 1051 | 0 |
| `tilt_attack_ceiling` | Tilt | 1047 | −4 |
| `shape_4-3-3` | Shape | 1035 | −16 |
| `shape_4-4-2` | Shape | 1033 | −18 |
| `shape_3-5-2` | Shape | 1024 | −27 |
| `ft_defence` | FT | 857 | −194 |

**Winner cross** `cross_3-4-3_attack_defcon_floor`: **1117** (+66 vs baseline; +36 vs best OAT). Family winners: Locked Starting Shape **3-4-3**, Transfer Target **attack**, tilt **Defcon-Floor**.

**Seed quality.** 2024-25 archive: 804 players, 27,605 performances, GW1–38, `code` complete, `minutes`/`starts` present, no Defcon column. At 2025-26 GW1 Feature Contract: 311 player_prior, 530 position_price_prior, 0 none.

**Occupancy diagnostic** (not the ranking object). [def_rotation_club_occupancy.csv](def_rotation_club_occupancy.csv) rank 1 `occupancy_key` = **BOU-CHE-MCI-MUN-MUN**, `total_mod_fdr` 135.75. Easy 2025-26 defensive fixtures ≠ Transfer Plan winner.

### Alternatives

- Wait for official FPL 2024-25 `element_summary` JSON — not available from live API.
- FPL-Core Insights 2024-2025 — Opta minutes, no FPL starts/points table; rejected as seed.
- Use 2025-26 GW1–5 as fake Prior-Season Seed and rank GW6+ — same-season history, not last year; GW6 greenfield would be a Wildcard analog; rejected.
- Position-Price for everyone at GW1 — not the 2026/27 analog; rejected as playbook.
- Start ranking at GW5 — previously rejected; would drop the GW1 draft that locks the half.

## Decision

**Verdict**: For 2026/27 First-Half (Chip Set 1, no Hits in this evidence), play **attack-side Free Transfers**, **3-4-3**, and **Defcon-Floor** on DEF/MID xP. The combined arm is the highest `realized_points` in [tp_walkforward_summary.csv](tp_walkforward_summary.csv).

### Strategy for this season (2026/27 GW1–19)

1. **Draft / XI shape: 3-4-3.** Lock the starting XI as 1 GKP, 3 DEF, 4 MID, 3 FWD. 4-5-1 was close (+4 vs baseline); 3-5-2 and 4-4-2 lost. Do not lock 3-5-2 from this evidence.
2. **Free Transfers: attack.** Spend FTs on MID/FWD. Keep GKP and DEF unless a Did-Not-Play Exception (`p_dnp ≥ 0.5`). Defence-only FT policy scored 857 (−194 vs baseline) — do not run that policy.
3. **Projection tilt: Defcon-Floor.** For DEF/MID, rank on `xP + xp_defcon` (prefer Defcon contribution). Attack-Ceiling (`xP - xp_defcon`) finished below baseline.
4. **Chips / Hits.** This ranking held BB/FH/TC off and forbade Hits. It does not pick Wildcard/FH timing (see First-Half Chip Strategy note). Do not take Hits to copy the replay; the replay never did.
5. **Occupancy.** Use the 5-DEF / GKP rotation notes for *which clubs* have easy fixtures this season. Last year’s easiest occupancy (BOU-CHE-MCI-MUN-MUN) is not this year’s occupancy and is not the Transfer Plan winner.
6. **Cold-Start in production.** Live GW1 still uses Expected Role Prior for minutes and 2025-26 archive for Event Rates. This replay used 2024-25 seed_state minutes so it would not leak 2026/27 roles into 2025-26.

**Recommended action**:
- Squad construction: 3-4-3
- FT policy: attack (lock GKP/DEF except DNP exception)
- Solver tilt: Defcon-Floor on DEF/MID
- Ignore defence-only FT and occupancy rank as shape pickers

**Trigger / kill switch**:
- Re-rank if 2024-25 seed replaced by FPL `element_summary` JSON, Availability Snapshots added, or ITB is chained across deadlines and the order of arms changes

## Risks and unknowns

- Live FPL API cannot snapshot 2024-25
- No Availability Snapshots on origin (terminal injury/price metadata may leak)
- vaastav seed: no Defcon column; `xP` unused
- GW1 solver Wildcard is construction only
- Leftover ITB not chained across deadlines
- Cross is one combination of OAT winners, not a full factorial
- 2026/27 promoted clubs / new signings had no 2024-25 player_prior in this replay; production will seed them from 2025-26 or Position-Price
