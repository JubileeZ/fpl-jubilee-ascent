# First-Half Chip Path (GW1–19)

**Updated**: 2026-08-19T00:45:00+07:00  
**Data stamp**: Stage 2 rates 2026-08-18; FPL API clubs/fixtures 2026-08-18; 2025/26 archive performances; GW1 deadline 2026-08-21T17:30:00Z  
**Season**: 2026/27 · First-Half Horizon GW1–19  
**Status**: Active sibling of Canonical Preseason Chip Path (does not replace 364.21)  
**Purpose**: Publish two Set-1 chip calendars (WC3 and WC4) with GW1 Bench Boost, forced Free Hit and Triple Captain, zero hits, greedy Free Transfers, on Prior-Season Dual-Vector Seed xP.  
**Scope**: Greenfield Draft 15. Research-only multipliers. Production `_fixture_maps` and live DCS CSVs unchanged.  
**Related**: [Canonical Stage 3](../gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md) · [First-half chip source note](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md) · [Live DCS](../defensive-fixture-rotation/defensive-fixture-rotation.md) · [CONTEXT.md](../../../CONTEXT.md)  
**Artifacts**:
- [Summary](../../../data/research/gw1-19-first-half-chip-path/first_half_summary.csv)
- [Weeks](../../../data/research/gw1-19-first-half-chip-path/first_half_weeks.csv)
- [Squads](../../../data/research/gw1-19-first-half-chip-path/first_half_squads.csv)
- [Transfers](../../../data/research/gw1-19-first-half-chip-path/first_half_transfers.csv)
- [FH search](../../../data/research/gw1-19-first-half-chip-path/fh_week_search.csv)
- [Projections](../../../data/research/gw1-19-first-half-chip-path/gw1-19_projections.csv)
- [Dual-Vector seed](../../../data/research/gw1-19-first-half-chip-path/prior_season_dual_vector_seed.csv)
- [Canonical S1 re-score](../../../data/research/gw1-19-first-half-chip-path/canonical_s1_dual_vector_rescore.csv)
- [DCS folder](../../../data/research/gw1-19-first-half-chip-path/dcs/)

---

## Sources

- **Repository data**: Stage 1/2 CSVs; `data/processed/{clubs,fixtures,players,user_picks}.parquet`; `data/archive/2025-26/processed/player_performances.parquet` — cutoff 2026-08-18
- **ADR 0013 / 0014 / 0015**: Dual-Vector Strength spec; Destination Team Concede Rate for promoted; DCS
- **Official FPL 2026/27 chip rules**: Set 1 expires GW19; one chip per GW; FTs preserved through WC/FH (as recorded in first-half chip note)

**Source boundary**: FPL `expected_goals` / `expected_goals_conceded` are not npxG. Seed is a proxy. Greedy FTs are not jointly optimal.

## Agent Prompt

```text
Full redo docs/research/gw1-19-first-half-chip-path/gw1-19-first-half-chip-path.md

1. Re-read CONTEXT.md First-Half Chip Path + Prior-Season Dual-Vector Seed.
2. uv run python docs/research/gw1-19-first-half-chip-path/run_all.py
3. Do not write production features/builder.py or live DCS CSVs.
4. Do not overwrite Canonical 364.21.
5. Update Updated, Data stamp, Findings, Decision.
6. Scratch only under .tmp/agent/; delete before finish.
```

## Method

**Method type**: empirical optimisation (scipy MILP + greedy FTs) on Dual-Vector xP

**Inputs**:
- Stage 2 `expected-stats-gw1-5.csv` + Stage 1 roles
- 2025/26 archive player xG / xGC
- Live fixtures GW1–19

**Procedure**:
1. Club attack = sum of player xG per club-fixture. Club defence = one team xGC (max among minutes>0; not summed). Home/away means scaled to league average. Promoted COV/HUL/IPS = 1.0.
2. In-memory clubs copy fills `strength_attack_*` / `strength_defence_*`. `_fixture_maps` ratios clip 0.4–1.8. Draft-only `ParticipationStateHybridModel` GW1–19.
3. For each WC ∈ {3,4} and FH ∈ {2…19}\{WC}: pre-WC 15 on weeks before WC except FH (BB GW1); FH 15 for that week; WC 15 on remaining weeks except FH with decay 0.84 from WC week. TC = max extra captain xP on a legal week. Post-WC greedy same-position FTs, hit_limit 0, bank up to 5.
4. Publish max Total xP calendar per WC plus FH search table.
5. DCS: effective FDR = `defence_multiplier × 3`; gw1_19 only; files under `dcs/`.

**Definitions and assumptions**:
- Headline Total xP undiscounted. Decay only in WC-window MILP and FT decisions.
- Draft-eligible = Nailed Starter / Regular Starter.
- User Squad comparison requires Draft-eligible mapping.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Scenario Expected Points | Total xP | Undiscounted sum of weekly XI (or 15 on BB) plus captain extras (TC = +2× cap) GW1–19 | Higher ↑ | Maximize; not comparable to 364.21 | First-Half Chip Path ranking |
| Canonical Dual-Vector 6GW | S1 DV | Same Canonical S1 15s scored on Dual-Vector xP GW1–6 | Higher ↑ | vs 364.21 FDR-xP | Scale check only |
| Rotated FDR (DV) | Rot FDR | Mean `defence_multiplier × 3` on started defensive slots | Lower ↓ | ≤ 2.40 | DCS risk; not official 1–5 identity |
| Defensive Composite Score | DCS | 0.60 S_Score + 0.40 S_Risk on Dual-Vector FDR | Higher ↑ | ≥ 80 | Sibling ranking; live DCS CSVs unchanged |

**Validation boundary**: Cold-Start. No live results. Greedy FT reversals are approximation noise.

## Source synthesis

### Main claims

- Set 1 chips expire at GW19 deadline; unused = 0.
- Official Fixture Difficulty on 2026/27 files equals opponent `strength_overall_*` at focal venue (760/760). Attack/defence API fields are 0.

### Source rationale

- Expert FH/TC windows (GW16–19, GW17 Haaland) stay qualitative until this MILP.

## Project interpretation

### Decision rules

- If choosing one calendar now: take WC4 + FH19 + TC17 (higher Total xP).
- If information-led WC wanted: WC3 is −7.39 xP on this model.
- Do not promote over Canonical 364.21 until Dual-Vector xP is accepted as the live scale.

### Practical implications

- Haaland in the GW1 BB 15 under Dual-Vector (Canonical FDR path delayed him to WC4).
- TC17 is Haaland on both winners.
- FH19 is last-call Set 1 expiry on the WC4 winner.

## Findings

### Evidence

- **WC4 winner**: BB1, WC4, TC17 Haaland, FH19. **1201.59 xP**. 6 FTs, 0 hits. Spend £100.0 / £98.5 FH / £100.0 post.
- **WC3 runner-up**: BB1, WC3, FH6, TC17. **1194.20 xP** (−7.39).
- **FH search**: WC4 next-best FH6 1197.12; WC3 next-best FH19 1192.54. All 32 legal FH weeks in `fh_week_search.csv`.
- **Canonical S1 re-score** (same 15s, Dual-Vector xP, GW1–6): **379.94** vs live FDR-xP **364.21**. Different scale; 364.21 remains live Canonical.
- **User Squad**: 4/15 Draft-eligible (J.Timber, Kelleher, Hall, Sangaré). No full 15-man Dual-Vector comparison.
- **DCS (this topic only)**: GKP gw1_19 #1 Raya + £4.0m fodder, DCS **94.00**, rot FDR **1.71**, 142.72 xP. Live DCS #1 Rushworth+Donnarumma is a different difficulty world — not overwritten.
- **WC4 pre-WC 15**: Donnarumma, Verbruggen; Gabriel, Guéhi, Calafiori, Vuskovic, Wieffer; Tzolis, Sarr, Tavernier, Schade, Núñez; Haaland, Isak, Calvert-Lewin.
- **WC4 rebuild**: Raya, Verbruggen; Gabriel, Guéhi, Hill, Vuskovic, Wieffer; Palmer, Tzolis, Tavernier, Stroud, Hjertø-Dahl; Haaland, Isak, Gonzalo.
- **WC4 FH19**: Donnarumma, Verbruggen; Gabriel, Guéhi, Calafiori, Hill, Vuskovic; Tzolis, Schade, Crooks, Sangaré, Slater; Haaland, Isak, Thiago.
- **Net FTs (WC4)**: after ping-pong, Hill→Maguire and Tavernier→Sarr. Full log in transfers CSV.

### Alternatives

- WC3 if locking a 15 for only GW1–2 (BB + one lock week) is preferred over +7.39 xP.
- Holding FH for a blank/double not in this fixture list — kill switch below.

## Decision

**Verdict**: Recommended First-Half Chip Path is **GW1 Bench Boost, GW4 Wildcard, GW17 Triple Captain (Haaland), GW19 Free Hit** at **1201.59 Dual-Vector xP**. Canonical **364.21** stays the live GW1–6 FDR-xP number.

**Recommended action**:
- Play the WC4 calendar if using this Dual-Vector sheet.
- Keep production Model Champion / `_fixture_maps` on FDR fallback until a promotion review.

**Trigger / kill switch**:
- Confirmed DGW/BGW or Haaland absence in GW17 → re-run `run_chip_path.py`.
- FPL fills `strength_attack_*` with a new scale → rebuild seed vs API, do not mix.

## Risks and unknowns

- FPL-xG proxy ≠ ADR 0013 npxG.
- Greedy FTs reverse (Sarr/Tavernier, Hill/Muharemović) — rest-of-horizon approx noise; treat log as net moves.
- Expected Role frozen GW1–5 for all 19 weeks.
- Dual-Vector DCS and 15-man MILP still disagree on keepers (Raya+fodder vs Donnarumma/Verbruggen then Raya).
- User Squad is mostly non-Draft; comparison skipped.

## Refresh checklist

- [x] `Updated` ISO 8601 with timezone
- [x] `Data stamp` evidence cutoff
- [x] Season GW1–19
- [x] Source vs interpretation split
- [x] Agent Prompt points at `run_all.py`
- [x] Live Canonical / production builder / live DCS untouched
