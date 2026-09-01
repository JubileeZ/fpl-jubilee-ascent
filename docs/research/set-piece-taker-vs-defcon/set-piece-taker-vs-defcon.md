# Set-piece taker vs Defcon — projected-point impact

**Updated**: 2026-09-01T15:30:00+07:00
**Data stamp**: 2024-25 processed archive; vaastav 2025-26 `players_raw` + `gws/merged_gw` (GW1–38); Official FPL scoring pages accessed 2026-09-01
**Season**: 2024/25 attack rates · 2025/26 Defcon + attack · 2026/27 rules still in force
**Status**: Active
**Purpose**: Decide when a set-piece taker with weaker Defcon is the better pick than a non-taker with stronger expected Defcon.
**Scope**: Outfield regulars (≥900 minutes and ≥10 starts of 60+). Penalty / corner / direct-FK primary from FPL `*_order==1`. Not set-piece *targets* (box headers). Not live 2026/27 projections (`data/processed` absent this session).
**Related**: [`INDEX.md`](../INDEX.md) · [ADR 0003](../../adr/0003-reconstruct-points-from-event-components.md) · `models/dual_vector_state_hybrid.py` penalty isolation
**Artifact**: [def_breakeven.csv](def_breakeven.csv) `net_sp_vs_high_defcon` · [mid_breakeven.csv](mid_breakeven.csv) `mean_pts_per_start` · [def_examples.csv](def_examples.csv) `pts_per_start` · [implied_setpiece_xp.csv](implied_setpiece_xp.csv) `xp_per90`

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence.

## Sources

- **Primary**: [FPL basics explained: Scoring points](https://www.premierleague.com/en/news/2174909) — Premier League; accessed 2026-09-01; role: goal/assist/Defcon point values and CBIT/CBIRT thresholds
- **Primary**: [What’s happening with defensive contribution points in 2026/27 Fantasy?](https://www.premierleague.com/en/news/4361991/whats-happening-with-defensive-contribution-points-in-202627-fantasy) — Premier League; 2026-07; accessed 2026-09-01; role: Defcon remains 2026/27; 2-pt cap per match
- **Primary**: [What's new in 2025/26 Fantasy: Changes to assists rules](https://www.premierleague.com/en/news/4362187/whats-new-in-202526-fantasy-changes-to-assists-rules) — Premier League; accessed 2026-09-01; role: corner/cross assist after ≤1 defensive touch if receiver is in the box
- **Primary**: [FPL defensive contribution points: Which defenders will get the most?](https://www.premierleague.com/en/news/4361968) — Premier League Scout; accessed 2026-09-01; role: Muñoz vs Lacroix 2024/25 retrospective
- **Primary**: [Long balls, long throws: Opta Analyst](https://www.premierleague.com/en/news/4426039/opta-analyst-on-long-balls-long-throws-key-tactical-trends-spotted-in-2025-26-season) — Premier League / Opta Analyst; accessed 2026-09-01; role: 20.6% of 2024/25 goals from non-penalty set-pieces; 0.35 corner-origin goals per match
- **Primary**: [All you need to know about changes to FPL for 2026/27](https://www.premierleague.com/en/news/4679873/all-you-need-to-know-about-changes-to-fpl-for-202627) — Premier League; accessed 2026-09-01; role: Defcon unchanged; BPS tweaked
- **Secondary**: [BBC — Palmer penalty record](https://www.bbc.com/sport/football/articles/c2ld0rqxglyo) — 2024-12-10; accessed 2026-09-01; role: Opta penalty xG = 0.79
- **Secondary**: [The Athletic — attacking performance versus xG](https://www.nytimes.com/athletic/6679514/2025/10/02/the-alternative-premier-league-table-expected-goals/) — 2025-10-02; accessed 2026-09-01; role: independent 0.79 penalty xG
- **Secondary**: [Opta Analyst — most dangerous set-piece teams](https://theanalyst.com/articles/premier-league-teams-most-dangerous-set-pieces) — accessed 2026-09-01; role: 58.8% of 187 set-piece goals from corners; second-phase often denies taker the assist
- **Repository data**: `data/archive/2024-25/processed` (no `defensive_contribution`); vaastav 2025-26 CSVs via runner; `models/dual_vector_state_hybrid.py`; `models/scoring_matrix.py`

**Source boundary**: FPL `*_order` is terminal season metadata (exploratory leakage). vaastav `xP` unused. 60% corner-assist credit in [implied_setpiece_xp.csv](implied_setpiece_xp.csv) is an assumption, not measured. League penalty rate 0.125/team/match is a midpoint, not a counted 2025-26 total.

## Agent Prompt

```text
Full redo docs/research/set-piece-taker-vs-defcon/set-piece-taker-vs-defcon.md

1. Re-read primary FPL scoring, Defcon 2026/27, and assist-rule pages listed under Sources.
2. Run: uv run python docs/research/set-piece-taker-vs-defcon/runner.py
3. Refresh Findings from companions in this folder. Do not snapshot totals in this prompt.
   - def_breakeven.csv net_sp_vs_high_defcon / mean_pts_per_start
   - mid_breakeven.csv mean_pts_per_start
   - def_examples.csv and mid_examples.csv pts_per_start
   - implied_setpiece_xp.csv xp_per90
4. Keep Source synthesis separate from Project interpretation.
5. Scratch under .tmp/agent/ only; delete before finishing.
```

## Method

**Method type**: Empirical player-season reconstruction + source synthesis of official scoring and set-piece volume.

**Inputs**:
- 2024-25: `data/archive/2024-25/processed/players.parquet` + `player_performances.parquet`
- 2025-26: vaastav `players_raw.csv` + `gws/merged_gw.csv` (archive `data/archive/2025-26/vaastav` if present, else download to `.tmp/agent`)
- Official FPL event values via `models/scoring_matrix.py` (DEF goal 6, assist 3, Defcon 2)

**Procedure**:
1. Quality pass: row counts, GW span, duplicate `player_id`+`fixture` (drop exact copies), Defcon nulls, set-piece order coverage. DGW duplicate `player_id`+`gameweek_id` kept (separate fixtures).
2. Assign `sp_role` from terminal FPL orders: `pen_and_corner` / `pen_primary` / `corner_primary` / `fk_primary` / `backup_sp` / `no_sp`.
3. Restrict to DEF/MID/FWD with ≥900 minutes and ≥10 appearances of ≥60 minutes.
4. Reconstruct per start: attack xP (goals × position + assists × 3), Defcon xP (2 if count ≥10 DEF or ≥12 MID/FWD on a 60+ minute appearance), CS xP.
5. Compare high-Defcon non-takers (no_sp, hit-rate ≥ p75) vs set-piece roles. Named players in example CSVs.

**Definitions and assumptions**:
- Start = appearance with ≥60 minutes (Defcon and CS eligibility).
- Break-even hit-rate gap = extra attack xP per start / 2 (one extra Defcon hit = 2 pts).
- Corner-taker implied xA uses 60% credit of team corner-origin goals — unvalidated.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Attack xP per start | `xp_attack_per_start` | $(\text{goals} \times \text{goal pts} + \text{assists} \times 3) / n_{\ge60}$ | Higher $\uparrow$ | DEF $\ge 1.0$ / MID $\ge 1.5$ | Set-piece and open-play returns packed into FPL points. |
| Defcon xP per start | `xp_defcon_per_start` | $2 \times \mathbf{1}[\text{count} \ge \text{threshold}]$ averaged over starts | Higher $\uparrow$ | $\ge 1.0$ ($\ge 50\%$ hit rate) | Capped at 2 pts/match; extra CBIT above threshold adds 0 FPL Defcon pts. |
| Defcon hit rate | `defcon_hit_rate` | Starts reaching 10 CBIT (DEF) or 12 CBIRT (MID/FWD) / starts | Higher $\uparrow$ | DEF $\ge 0.45$ | Probability a started player banks the 2 Defcon pts. |
| Attack+Defcon per start | `attack_plus_defcon` | `xp_attack_per_start` + `xp_defcon_per_start` | Higher $\uparrow$ | Maximized | User's framed trade-off, CS/bonus stripped. |
| Points per start | `pts_per_start` | Official `total_points` / starts | Higher $\uparrow$ | DEF $\ge 4.5$ | Includes CS, bonus, cards; the pick metric. |
| Break-even hit-rate gap | `breakeven_hit_rate_gap` | $\Delta$ attack xP per start / 2 | Context | DEF $\approx 0.34$ in 2025-26 corner vs high-Defcon | Extra Defcon hits needed to offset the taker's extra attack xP. |
| Penalty xP per 90 | `xp_per90` (pen) | $\lambda_{\text{pen xG}} \times$ goal pts | Higher $\uparrow$ | Engine DEF $0.90$; league DEF $\approx 0.59$ | Isolated penalty contribution if the player takes every club penalty. |

**Validation boundary**: 2025-26 Defcon is observed. 2024-25 has no Defcon column. Exclusive DEF `corner_primary` n=2 (James, H.Bueno) — do not treat that mean as a type. `DEF_any_setpiece_order` n=17 is the more stable DEF set-piece cohort. Terminal orders miss in-season role changes.

## Source synthesis

### Main claims

- Defcon is 2 pts once per match at 10 CBIT (DEF) or 12 CBIRT (MID/FWD); capped; remains in 2026/27. A 20-CBIT game still scores 2 Defcon pts.
- Goals: DEF 6, MID 5, FWD 4. Assists 3. Corner deliveries can award the taker an assist when the scorer receives in the box after at most one defensive touch (2025/26 rule; Scout: 41 extra assists if applied to the prior season). Second-phase / two-touch clearances still deny the taker.
- Opta penalty xG = 0.79 (BBC and The Athletic). Non-penalty set-pieces were 20.6% of 2024/25 goals; 58.8% of 187 set-piece goals were corners; 2024/25 corner-origin scoring 0.35 goals/match (both teams).
- Scout 2024/25 retrospective: Muñoz 142 + 14 Defcon = 156; Lacroix 114 + 34 Defcon = 148. Attacking wing-back still ahead after adding Defcon; gap shrinks from 28 to 8.
- Direct free-kick goals are rare relative to corners; many "set-piece goals" are first contacts by *targets*, not takers.

### Source rationale

- Penalty duty is a large, repeatable xG stream attached to one player. Corner duty is a smaller, noisier assist stream and is club-quality dependent. Defcon is a high-floor 0-or-2 coin per start for CBs and some DMs, independent of clean sheets.

## Project interpretation

### Decision rules

1. **Penalty primary (`penalties_order==1`)** — select over a similar-minutes non-taker. League-implied ~0.10 xG/90 × goal pts ≈ 0.40–0.59 xP/90; engine isolates 0.15 xG/90 (0.75–0.90 xP/90 for MID/DEF). That is 0.20–0.45 extra Defcon hits/90. No regular 2025-26 DEF was a penalty primary.
2. **DEF, corners only, weak CS** — select the high-Defcon CB. 2025-26 high-Defcon no_sp p75: `mean_pts_per_start` 4.13 vs H.Bueno 3.46. Attack+Defcon net for exclusive DEF corners vs that CB cohort is negative (`def_breakeven.csv` `net_sp_vs_high_defcon`).
3. **DEF, corners/FK on a strong CS team with real returns** — select the taker even at ~10% Defcon hit rate. James 6.05 pts/start (1.58 attack, 1.68 CS, 0.21 Defcon); De Cuyper 7.00 (small sample, 12 starts); Digne 5.11. Pattern: `xp_attack_per_start` ≥ 1.0 and `xp_cs_per_start` ≥ ~1.4.
4. **DEF, shared/backup set-piece (order 2+)** — do not assume taker value. Porro/Cash/Hume/Trippier sit at 3.0–3.8 pts/start, below Tarkowski/Lacroix/Senesi.
5. **MID, corners without pens** — corners alone do not beat a high-Defcon DM. 2025-26 corner-primary mids 4.40 pts/start vs no_sp 4.39. Tonali 3.00 / Bernardo 3.29 lose to Palhinha 6.00 and Casemiro 5.69. Select the taker only with open-play threat (Wilson, Saka) or stacked Defcon (Anderson 70% hit rate, Rice 40%).
6. **Have both** — Rice, Anderson, Garner. No trade-off; pick them over a Defcon-only specialist.
7. **Target ≠ taker** — Virgil/Mavropanos/Ballard score headers *and* hit Defcon. That is not set-piece *taking*.

### Practical implications

- User scenario (better expected Defcon, not a taker vs taker with decent Defcon): **on DEF, the CB wins unless the taker also brings CS + attacking returns**. Corners are not enough.
- Engine (`dual_vector_state_hybrid`): only `penalties_order==1` is isolated (0.15 xG/90, unscaled by `attack_multiplier`). Corner duty enters only via historical `per90_xa` / creativity. A new corner taker is understated until Appearance Blend. Defcon is a negbin threshold on `per90_defensive_contribution`.
- Ownership Explorer already splits `xp_goals` / `xp_assists` / `xp_defcon`. Rank on the sum, not on Defcon or set-piece flags alone.

## Findings

### Evidence

- **Scoring math (official).** One extra DEF goal = 6 pts = 3 Defcon hits. One assist = 3 pts = 1.5 hits. Defcon cannot exceed 2 pts in a match, so a 55% vs 20% hit-rate gap is 0.70 xP/start and does not grow if the CB puts up 18 CBIT.
- **Implied set-piece xP** ([implied_setpiece_xp.csv](implied_setpiece_xp.csv) `xp_per90`): engine penalty DEF 0.90; league penalty DEF 0.59; corner-assist credit (assumption) 0.32 for any position. Penalty >> corners as an individual stream.
- **2025-26 DEF regulars** ([def_breakeven.csv](def_breakeven.csv)): no_sp n=106, hit rate 0.279, 3.89 pts/start. High-Defcon p75 n=28, hit rate 0.548, 4.13 pts/start. Any FPL set-piece order n=17, 4.32 pts/start (wins on *total* points via CS). Exclusive corner primary n=2 only.
- **Named DEF split.** James: 10.5% Defcon, 1.58 attack, 1.68 CS, 6.05 pts/start. H.Bueno: 12.5% Defcon, 0.63 attack, 0.67 CS, 3.46 pts/start. Senesi 4.73 / Tarkowski 4.59 / Lacroix 4.53 with 59–70% Defcon. Same duty, opposite pick — CS and actual returns decide.
- **2025-26 MID** ([mid_breakeven.csv](mid_breakeven.csv)): penalty group 5.38 pts/start. Corner group 4.57. High-Defcon no_sp 4.18 (pulled down by low-attack DMs). Palhinha/Casemiro work because they also score, not because Defcon replaces attack.
- **2024-25 attack-only (no Defcon).** DEF corner primary n=5: 0.63 attack xP/start vs no_sp 0.38 (`group_summary.csv` `mean_xp_attack_per_start`). Extra ~0.25 xP/start from corners, ≈ 0.13 Defcon hits — too small to beat a 50%+ CB once Defcon exists.
- **Scout pair (2024/25 + imputed Defcon).** Muñoz still beats Lacroix after +20 Defcon pts to Lacroix. Matches James-vs-Tarkowski: elite attacking DEF survives Defcon; ordinary full-backs do not.

### Alternatives

- Ignore set-piece flags and rank on engine xP: misses new corner takers; fine for penalty isolation.
- Always pick max Defcon: overweights promoted CBs with terrible CS (Estève 2.58 pts/start despite 58% hits).
- Always pick takers: overweights Bueno/Tonali/Cash types.

## Decision

**Verdict**: Corners with weaker Defcon beat a high-Defcon non-taker only when the taker also delivers penalty duty, strong clean-sheet odds, or real open-play threat; Defcon alone wins the "decent vs elite CBIT" DEF comparison.

**Recommended action**:
- Penalty taker → select.
- DEF: high-Defcon CB (hit rate ≥ ~0.45) vs corners-only FB on a mid/weak defence → CB.
- DEF: taker with attack xP/start ≥ 1.0 and CS xP/start ≥ ~1.4 → taker.
- MID: corners without goals/pens/Defcon → skip for Palhinha/Casemiro-type or a true attacker.
- Prefer players who stack (Rice, Anderson) over a pure specialist on either axis.

**Trigger / kill switch**:
- Player loses penalty/corner order (FFS/Opta taker tables, not stale FPL `*_order`).
- Defcon hit rate over 6+ starts sits below 0.30 for a "Defcon CB" pick, or CS rate collapses for a "taker FB" pick.
- Engine xP: if `penalties_order` flips to 1 with `per90_xg` still low, trust the 0.15 isolation only after confirming they actually take pens.

## Risks and unknowns

- DEF exclusive `corner_primary` n=2; James/Bueno mean is not a type.
- Terminal FPL order ≠ in-season taker share (De Cuyper classified `fk_primary` while also taking corners).
- Corner-assist 60% credit unvalidated; Opta second-phase share unknown in this extract.
- League penalty frequency not counted from 2025-26 events (0.125/team used as midpoint).
- No live 2026/27 `data/processed` this session — 2026/27 GW1 takers (FFS 2026-08-25) not scored here.
- 2024-25 archive: 374 DGW duplicate player-GW rows kept; 20 managers excluded; no Defcon.
- 2025-26: 10 exact duplicate player-fixture rows dropped (Kroupi, Gannon-Doak copies).

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
