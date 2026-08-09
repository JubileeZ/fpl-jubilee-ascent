# FPL Set-Piece Stats, Expected Takers, and Dead-Ball Projections (2026/27)

**Updated**: 2026-08-09T18:55:00+07:00  
**Data stamp**: 2026-08-09 (Opta Analyst × Solio Analytics 2026/27 Pre-Season Release)  
**Season**: 2026-27  
**Status**: Active  
**Purpose**: Synthesize Premier League set-piece tactical trends, 20-club corner hierarchies, coaching movements, dead-ball goal/assist efficiency, penalty regressions, and target receiver expected goals (xG) for FPL modeling and Draft/Role calibration.  
**Scope**: 20 Premier League clubs (+ Coventry City Championship benchmark), 2025/26 empirical dead-ball distribution, 2026/27 corner taker distributions by pitch flank, direct free-kick specialists, penalty regressions, and aerial target metrics.  
**Related**: [Research Index](../INDEX.md), [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md), [Expected Stats GW1–5](../gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.md), [FPL Pre-Season Guide](../fpl-preseason-guide/fpl-preseason-guide.md)  
**Artifact**: [Corner Takers 2026/27](../../../data/research/fpl-set-piece-analysis/corner_takers_2026_27.csv) · [Team Net Swings 2025/26](../../../data/research/fpl-set-piece-analysis/team_set_piece_swing_2025_26.csv) · [Player Leaders 2025/26](../../../data/research/fpl-set-piece-analysis/player_set_piece_leaders_2025_26.csv)

---

## Sources

- **Primary**: [FPL Set-Piece Stats: Expected Takers, Players to Target, and Projections for 2026-27 — Opta Analyst × Solio Analytics](https://theanalyst.com/articles/fpl-set-piece-stats-projections-tips-premier-league-2026-27) — Dan Edwards, Matt Sisneros, Ithiel Piñero; published August 2026; accessed 2026-08-09; role: primary empirical data for 2025/26 set-piece goal shares, 20-club taker hierarchies, receiver metrics, and Solio PPG projections.
- **Repository data**: `docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv` — player roles and Draft eligibility.

**Source boundary**: Source claims regarding projected taker hierarchies represent Solio model projections and tactical deductions. Actual corner shares during live matches will be subject to starting lineups, in-game substitutions, and match-state dynamics.

---

## Agent Prompt

```text
Full redo docs/research/fpl-set-piece-analysis/fpl-set-piece-analysis.md

1. Re-read primary source at https://theanalyst.com/articles/fpl-set-piece-stats-projections-tips-premier-league-2026-27.
2. Verify all 20 club corner taker pairings by flank (Left vs Right).
3. Validate team non-penalty set-piece goal numbers, net swings, and coaching movements.
4. Refresh companion CSVs in data/research/fpl-set-piece-analysis/.
5. Maintain strict separation between Source synthesis and Project interpretation.
6. Verify delivery gate with ruff, pytest, and verify.sh.
```

---

## Method

**Method type**: Source synthesis & tactical data extraction.

**Inputs**:
- Opta Analyst 2025/26 Premier League dead-ball event tracking (non-penalty set-pieces, corners, direct FKs, indirect FKs, throw-ins, penalty counts).
- Solio Analytics 2026/27 corner taker hierarchy models and projected points-per-game (PPG).

**Procedure**:
1. Extract league-wide macro trends (share of goals from set-pieces, corner goal share, inswinger ratio).
2. Extract club-by-club dead-ball net swings and coaching staff changes.
3. Tabulate the 20-club corner taker hierarchy by pitch flank (Left vs Right) and dominant foot.
4. Compile individual player case studies (Fernandes, Szoboszlai, Stach vs Wilson, Rice vs Guimarães, Thiago, Van Dijk, Thiaw).
5. Map practical implications to our Feature Contract, Expected Role audits, and component rate expectations.

---

## Source synthesis

### Macro League Trends (2025/26)

- **Set-Piece Goal Surge**: 27.4% of all Premier League goals came from non-penalty set-pieces in 2025/26 (second-highest proportion in 34 seasons, up from 20.6% in 2024/25).
- **Corner Dominance**: Goals from corners reached an all-time Premier League high of 18.0% of all goals (up from 12.1% in 2024/25).
- **Inswinging Hegemony**: Teams overwhelmingly favoured inswinging corners (2,643 inswingers vs 541 outswingers; ~83.0% inswingers). Left-footers dominated right-flank deliveries and right-footers dominated left-flank deliveries.
- **Direct Free-Kicks Declining**: Only 251 direct free-kick shots occurred across the entire 2025/26 campaign (down from 621 in 2003/04), making reliable direct FK specialists exceptionally rare and valuable.

### Club Set-Piece Performance & Coaching Impacts

| Club | 25/26 NP Set-Piece Scored | 25/26 NP Set-Piece Conceded | Net Goal Swing | Set-Piece Coach / Notes |
|:---|:---:|:---:|:---:|:---|
| **Arsenal** | 25 (19 corners) | 8 | **+17** | Nicolas Jover. Best in PL; set all-time corner goal record (19). |
| **Tottenham Hotspur** | — | — | **+10** | Andreas Georgson. 2nd-best swing in PL despite finishing 17th. |
| **Coventry City** (Championship) | 29 | 13 | **+16** | Standout promoted team from set-plays; swing would rank 2nd in PL. |
| **AFC Bournemouth** | — | 20 (tied worst) | — | 96.4% inswingers (highest in PL). Andoni Iraola staff moved to Liverpool. |
| **Crystal Palace** | — | 20 (tied worst) | **-9** | Worst net dead-ball swing in Premier League. |
| **Liverpool** | — | 20 (tied worst) | — | Hired Andoni Iraola and Bournemouth set-piece coaching staff for 26/27. |
| **Chelsea** | — | — | — | Hired Austin MacPhee from Aston Villa for undisclosed release-clause fee. |

### 2026/27 20-Club Corner Taker Hierarchy (Opta × Solio)

| Club | Left Corner (Primary / Secondary) | Right Corner (Primary / Secondary) | Flank / Tactical Dynamic |
|:---|:---|:---|:---|
| **Arsenal** | Declan Rice | Bukayo Saka / Noni Madueke | Rice took 87 L / 8 R corners in 25/26; Saka/Madueke right inswingers. |
| **Aston Villa** | Matty Cash | Lucas Digne / John McGinn | Austin MacPhee departed to Chelsea; Cash right-footed on left. |
| **Bournemouth** | Alex Scott / Justin Kluivert | Marcus Tavernier / David Brooks | 96.4% inswinger preference in 25/26. |
| **Brentford** | Mathias Jensen / Mikkel Damsgaard | Vitaly Janelt / Dango Ouattara | Jensen/Damsgaard (R) on left; Janelt/Ouattara (L) on right. |
| **Brighton** | Pascal Groß / Ferdi Kadıoğlu | Maxim De Cuyper / Yankuba Minteh | Groß/Kadıoğlu on left; De Cuyper/Minteh left-footed on right. |
| **Chelsea** | Reece James / Enzo Fernández | Pedro Neto / Estêvão | Austin MacPhee arrived; Neto/Estêvão left-footed options on right. |
| **Coventry City** | Matt Grimes / Victor Torp | Matt Grimes / Jack Rudoni | Grimes delivers from both flanks; Torp (L) / Rudoni (R). |
| **Crystal Palace** | Yeremy Pino / Brennan Johnson | Adam Wharton / Will Hughes | Yeremy/Johnson (R) on left; Wharton/Hughes (L) on right. |
| **Everton** | James Garner | Kiernan Dewsbury-Hall | Garner took 100 L / 10 R corners; Dewsbury-Hall 43 R / 0 L. |
| **Fulham** | Saša Lukić / Alex Iwobi | Saša Lukić / Oscar Bobb | Lukić features on both flanks; Bobb left-footed on right. |
| **Hull City** | Regan Slater / Ryan Giles | Mohamed Belloumi / Ryan Giles | Giles left-footed crosser active on both flanks. |
| **Ipswich Town** | Marcelino Núñez / Jack Clarke | Leif Davis / Marcelino Núñez | Davis left-footed specialist on right; Núñez primary on left. |
| **Leeds United** | Anton Stach | Harry Wilson / Anton Stach | Stach took corners equally in 25/26 (52% inswing); Wilson left-footed incoming. |
| **Liverpool** | Dominik Szoboszlai / Cody Gakpo | Dominik Szoboszlai / Florian Wirtz | Szoboszlai primary from both sides; Iraola staff arrived from BOU. |
| **Manchester City** | Rayan Cherki / Elliot Anderson | Phil Foden / Rayan Cherki | Foden primary left-footed from right; Cherki dual-flank delivery. |
| **Manchester United** | Bruno Fernandes | Bryan Mbeumo / Luke Shaw | Fernandes primary (R) on left; Mbeumo/Shaw left-footed on right. |
| **Newcastle United** | Bruno Guimarães / Jacob Murphy | Lewis Hall | Guimarães creates shot every 1.9 corners; Hall left-footed on right. |
| **Nottingham Forest** | Neco Williams / Dan Ndoye | Omari Hutchinson / Callum Hudson-Odoi | Williams/Ndoye on left; Hutchinson/Hudson-Odoi on right. |
| **Sunderland** | Enzo Le Fée / Trai Hume | Granit Xhaka | Le Fée right-footed on left; Xhaka left-footed on right. |
| **Tottenham Hotspur** | Pedro Porro / Mathys Tel | Mohammed Kudus / Pedro Porro | Andreas Georgson coach; Porro (R) / Kudus (L). |

### Key Player Case Studies & Value Levers

1. **Bruno Fernandes (£12.0m, MUN)**:
   - 21 assists in 2025/26 (Premier League all-time record).
   - 11 set-piece assists (equalled Steven Gerrard's all-time single-season record); 7 from first-time crosses.
   - Solio projected PPG: **6.12** across GW1–6 (2nd overall to Haaland's 6.57).
2. **Dominik Szoboszlai (£7.0m, LIV)**:
   - 14 direct free-kick attempts (most in PL); 4 direct free-kick goals (only Beckham and Robert scored 5 in a single season).
   - Primary corner taker from both flanks; Solio projected PPG: **4.91** across GW1–10 (6th overall, matching/exceeding Cole Palmer at £9.5m [4.98] and Antoine Semenyo at £8.5m [4.79]).
3. **Anton Stach (£6.0m) vs Harry Wilson (£6.5m) (LEE)**:
   - Stach: 4.9 pts/start in 25/26, 3 direct FK goals; Leeds had balanced 52% inswingers.
   - Wilson: 5.0 pts/start; elite left-footed delivery expected to absorb right-sided corners.
   - Solio GW1–10 PPG: Wilson **3.70** vs Stach **3.63**.
4. **Declan Rice (£6.5m) & Bruno Guimarães (£7.5m) (ARS)**:
   - Rice: 95 corners (87 L / 8 R), 130 indirect FKs, 45 crossed indirect FKs, 5 direct FKs, 24 box throw-ins.
   - Guimarães: Generated a shot every 1.9 corners (best among ARS/NEW takers >=20 corners); 2/2 penalties.
5. **Igor Thiago (£8.0m, BRE)**:
   - 22 goals in 25/26 (2nd to Haaland 27); 9 penalties taken (8 scored).
   - Non-penalty goals were 14 (lower than João Pedro's 15). Penalty regression expected; Solio projects Iliman Ndiaye (£6.0m) to outscore Thiago over GW1–10 despite being £2.0m cheaper.
6. **Set-Play Target Expected Goals (xG) Leaders (25/26 Non-Penalty)**:
   - **Malick Thiaw** (NEW, DEF, £5.0m): **4.7 xG** (1st in PL).
   - **Casemiro** (MUN, MID, departed): **4.1 xG** (2nd in PL).
   - **Marc Guéhi** (MCI, DEF, £6.0m): **3.7 xG** (3rd in PL).
   - **Virgil van Dijk** (LIV, DEF, £6.0m): 4 goals from first contact on crossed corners (1st in PL).
   - **Pascal Struijk** (BHA, DEF, £4.5m): 19 first contacts on crossed corners (1st in PL), 16 shots, 0 goals.
   - **Gabriel Magalhães** (ARS, DEF, £8.0m): 13 first contacts, 8 shots, 1 goal.

---

## Project interpretation

### Decision rules

1. **Szoboszlai Role & Floor Confirmation**: Szoboszlai's monopoly on direct FKs (14 shots, 4 goals) and primary corner duties across both flanks provides elite non-open-play baseline assist/goal volume, reinforcing his Nailed Starter / priority status in GW1–5 draft models.
2. **Defensive Target Aerial Upside**: Defenders with top-tier set-play xG (Van Dijk, Thiaw, Guéhi, Gabriel) should carry elevated `per90_xg` component priors relative to standard fullbacks with similar open-play stats.
3. **Penalty Variance Caution**: Forward pricing inflated by penalty volume (Igor Thiago 8 penalty goals) must be discounted in open-play event rate estimations; mids with strong open-play and Defcon rates (e.g. Ndiaye) offer superior value per million.
4. **Flank-Specialized Corner Sharing**: Inswinging corner tactics dilute single-player corner monopolies when clubs lack a switch hitter. Right-footed corner takers (e.g. Rice, Garner, Bruno Fernandes) lose right-sided deliveries to left-footed specialists (Saka, Dewsbury-Hall, Mbeumo).

---

## Findings

### Evidence

- Non-penalty dead balls represent 27.4% of total league goal volume, cementing set-piece involvement as a major component of attacking xP.
- 83.0% of crossed corners are inswingers, establishing footedness as a decisive predictor of corner taker splits.
- Specialized set-piece coaching (Jover at ARS, Georgson at TOT, MacPhee at CHE, Iraola at LIV) creates persistent club-level net goal swings of +10 to +17 goals.

---

## Decision

**Verdict**: Adopt Opta Analyst / Solio set-piece taker hierarchies as primary domain evidence for 2026/27 dead-ball assignments and player role evaluations.

**Recommended action**:
- Retain companion CSVs in `data/research/fpl-set-piece-analysis/`.
- Cross-reference taker hierarchies against `docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv` during pre-GW1 squad selection.
- Factor set-play aerial target metrics into defender xP comparisons (favoring Van Dijk, Thiaw, and Gabriel over pure open-play options).

**Trigger / kill switch**:
- Confirmed pre-season friendly corner routines or summer transfer arrivals shifting taker hierarchies (e.g. Harry Wilson claiming right-side corners from Anton Stach).

---

## Risks and unknowns

- Pre-season friendly evidence may alter flank assignments before GW1.
- In-game substitutions frequently shift secondary corner and free-kick takers.
- Solio projected PPG figures are external third-party model estimates, not outputs of the local `participation_state_hybrid` engine.

---

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff (2026-08-09).
- [x] `Season` and scope remain accurate (2026-27).
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
