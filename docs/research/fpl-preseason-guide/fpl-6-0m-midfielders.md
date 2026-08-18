# FPL 2026/27: Best £6.0m Midfielders

**Updated**: 2026-08-18T15:05:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-08-07 (unchanged on 2026-08-13 recheck); accessed 2026-08-13; Playwright recheck 2026-08-18: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Assess £6.0m mid-tier midfielders for FPL 2026/27 starting XI selection, penalty duties, underlying attacking stats, and DefCon hybrid output  
**Scope**: All key midfielders priced at £6.0m in FPL 2026/27  
**Related**: [Pre-season guide](fpl-preseason-guide.md) · [£5.0m midfielders](fpl-5-0m-midfielders.md) · [£6.5m–£7.0m midfielders](fpl-6-5m-7-0m-midfielders.md) · [£7.5m+ midfielders](fpl-7-5m-midfielders.md) · [Summer transfers](fpl-summer-transfers.md)

> Note revision created 2026-08-09 from Fantasy Football Scout full price-bracket review. Primary article published 2026-08-07. Source claims cross-checked with expected-role-gw1-5.md and fpl-summer-transfers.md.

## Sources

- **Primary**: [Best £6.0m midfielders for FPL 2026/27 — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/08/07/best-6-0m-midfielders-for-fpl-2026-27) — published 2026-08-07; accessed 2026-08-13; role: £6.0m midfielder analysis, penalty hierarchies, Opta creativity / big chance data, and starting prospects
- **Cross-check**: [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — updated 2026-08-06; role: starter status, tactical deployment, injury status
- **Cross-check**: [Confirmed Summer Transfers](fpl-summer-transfers.md) — updated 2026-08-09; role: confirmed transfer moves (Mateus Fernandes to Spurs £85m, Tielemans to Man Utd £35m)

**Source boundary**: Source claims cross-checked against internal project notes. No live FPL API refresh or solver optimization run performed in this note.

## Agent Prompt

```text
Full redo docs/research/fpl-preseason-guide/fpl-6-0m-midfielders.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`).
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Extract full text and analysis for all covered £6.0m midfielders.
4. Transcribe 100% of Opta statistical images (Big chances created, Minutes per chance created, Big chances total, Bournemouth & Brighton player stat tables) into Markdown tables.
5. Keep Source synthesis strictly separate from Project interpretation.
6. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
7. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Source synthesis / price bracket analysis & cross-check audit

**Inputs**:
- Fantasy Football Scout article (`best-6-0m-midfielders-for-fpl-2026-27`)
- Expected Role GW1–5 note (`expected-role-gw1-5.md`)
- Confirmed Summer Transfers register (`fpl-summer-transfers.md`)

**Procedure**:
1. Extract profiles, penalty duties, tactical roles, and fitness for all featured £6.0m midfielders.
2. Transcribe Opta statistical images covering big chances created, goal threat, minutes per chance created, and club comparisons.
3. Group targets by primary appeal: Penalty Takers, High-Volume Goal Threats, Creators/Set-Piece Takers, and DefCon Hybrids.
4. Synthesize decision rules and team-structure recommendations.

**Definitions and assumptions**:
- **£6.0m MID**: Midfielders priced at £6.0m in FPL 2026/27.

## Source synthesis

### Featured £6.0m Midfielders Analysis

- **Enzo Le Fee (Sunderland, £6.0m)**:
  - 5 goals, 6 assists, 16 DefCon points in 2025/26.
  - Joint-8th among all Premier League players for big chances created (13).
  - Share of penalties at Sunderland: scored 3 and missed 1 in 2025/26 (shares with Habib Diarra £5.5m).
  - Scored 3 goals in pre-season (including vs Liverpool) operating as central controller in a 4-1-4-1. Minor knock vs Wrexham resolved.
- **Iliman Ndiaye (Everton, £6.0m)**:
  - 4 open-play goals, 3 assists, 12 DefCon points; scored 2/2 penalties in 2025/26.
  - Everton ranks #1 on the Fixture Ticker in GW1–6 (Ipswich H, Hull A).
  - Modest shot frequency (64.7 mins/shot), but high shot quality from central box locations.
- **James Garner (Everton, £6.0m)**:
  - Averaged 4.2 pts/start in 2025/26, boosted by 40 DefCon points (2nd-most among all midfielders in the league).
  - Underwent groin surgery; unlikely to start GW1.
- **Marcus Tavernier & Justin Kluivert (Bournemouth, £6.0m)**:
  - Marco Rose's attacking system ranks 9th for projected goals in GW1–6 despite tough fixture difficulty.
  - **Tavernier**: 2742 mins, 200.1 mins/xGI, 51.0 mins/CC, 2 penalties converted in 2025/26.
  - **Kluivert**: 1001 mins, 260.0 mins/xGI; scored pre-season hat-trick (2 penalties) vs Genoa. Prior regular taker under Iraola before injury.
  - **Alex Scott (£6.0m)**: 30 DefCons in 2025/26; trailing in attacking underlying numbers (423.2 mins/xGI).
- **Mateus Fernandes (Tottenham, £6.0m)**:
  - 3 goals, 4 assists, 30 DefCon points (5th-most among midfielders) in 36 matches for relegated West Ham.
  - £85m transfer to Spurs to play double pivot under De Zerbi alongside Sandro Tonali (£5.5m); scored and took set plays in pre-season friendly.
- **Anton Stach (Leeds, £6.0m)**:
  - 5 goals, 6 assists in 29 matches, averaging 4.9 points per start (highest of any £6.0m midfielder).
  - Set-piece taker (corners & free-kicks); elite 37.0 mins per chance created. Selected by only 1.3% of managers.
- **Kevin Schade (Brentford, £6.0m)**:
  - 8 goals, 5 assists in 35 matches; underperformed xG by -4.18.
  - Joint-top among ALL midfielders for big chances in 2025/26 (22 big chances, matching Bryan Mbeumo).
  - Faces competition from Jaidon Anthony (£6.0m).
- **Jack Hinshelwood & Yankuba Minteh (Brighton, £6.0m)**:
  - **Hinshelwood**: 3 goals, 3 assists in 13 starts as #10 to close 2025/26; 5th among midfielders for xG (4.34) in that span; 242.1 mins/xGI.
  - **Minteh**: 8 assists, 44 chances created, 270.6 mins/xGI; expected to start on left flank early with Kaoru Mitoma (£6.0m) recovering fitness.
- **Other £6.0m Mentions**:
  - **Emiliano Buendia (Aston Villa, £6.0m)**: Potential early starter as #10 on penalties with Johan Manzambi sidelined by knee surgery.
  - **Amad Diallo, Harvey Barnes, Rio Ngumoha (£6.0m)**: High per-minute upside but rotational minutes risk.
  - **Youri Tielemans (£6.0m)**: Deeper midfield role at Man United blunts appeal.
  - **Ryan Gravenberch (£6.0m)**: 5 goals, 5 assists, 16 DefCons, but overachieved xGI (+3.84) and averaged 4.2 pts/start.

---

### 2025/26 Opta Statistical Data

#### Big Chances Created Leaders — Midfielders (2025/26)

| Name | Team | Cost | Big Chances Created |
|---|---|---|---|
| Bruno Fernandes | MUN | 12.0 | 33 |
| Cherki | MCI | 7.5 | 19 |
| Rice | ARS | 7.5 | 17 |
| Bowen | WHU | 7.8 | 16 |
| Pino | CRY | 5.5 | 15 |
| Szoboszlai | LIV | 7.0 | 14 |
| Wharton | CRY | 5.5 | 14 |
| Doku | MCI | 7.5 | 13 |
| **Le Fee** | **SUN** | **6.0** | **13** |

#### Bournemouth Midfielders Comparison (2025/26)

| Name | Team | Cost | Mins | Mins/Goal | Mins/Shot | Mins In Box | Mins On Target | Mins/Touch | Mins/CC | Mins/Cross | Mins/xA | Mins/xG | Mins/xGI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Tavernier** | BOU | 6.0 | 2742 | 391.7 | 39.2 | 88.5 | 114.3 | 24.1 | 51.0 | 24.1 | 590.9 | 302.6 | **200.1** |
| **Kluivert** | BOU | 6.0 | 1001 | 500.5 | 58.9 | 166.8 | 250.3 | 32.3 | 48.0 | 23.8 | 654.2 | 431.5 | **260.0** |
| **Scott** | BOU | 6.0 | 2861 | 953.7 | 65.0 | 168.3 | 220.1 | 58.4 | 106.0 | 32.5 | 969.8 | 750.9 | **423.2** |

#### Minutes Per Chance Created (CC) Leaders — Midfielders (2025/26)

| Name | Team | Cost | Mins | Mins/Goal | Mins/Shot | Mins In Box | Mins On Target | Mins/Touch | Mins/CC | Mins/Cross | Mins/xA | Mins/xG | Mins/xGI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bruno Fernandes | MUN | 12.0 | 3062 | 340.2 | 36.0 | 76.6 | 127.6 | 33.6 | 23.0 | 16.7 | 248.5 | 282.7 | 132.3 |
| Doku | MCI | 7.5 | 1837 | 367.4 | 47.1 | 68.0 | 122.5 | 9.4 | 31.0 | 31.1 | 297.2 | 668.0 | 205.7 |
| Cherki | MCI | 7.5 | 1866 | 466.5 | 33.9 | 47.8 | 143.5 | 12.6 | 31.0 | 23.3 | 215.7 | 451.8 | 146.0 |
| Odegaard | ARS | 6.5 | 1399 | 1399.0 | 63.6 | 139.9 | 174.9 | 36.8 | 36.0 | 63.6 | 381.2 | 1137.4 | 285.5 |
| Saka | ARS | 9.5 | 2240 | 320.0 | 31.5 | 43.1 | 83.0 | 12.0 | 37.0 | 18.4 | 312.8 | 296.7 | 152.3 |
| **Stach** | **LEE** | **6.0** | **2350** | **470.0** | **42.7** | **111.9** | **167.9** | **42.7** | **37.0** | **15.0** | **521.1** | **804.8** | **316.3** |

#### Big Chances Total Leaders — Midfielders (2025/26)

| Name | Team | Cost | App | Mins | Goals Tot | Goals In Box | Goals Out | Head Goals | Mins/Goal | Shots Tot | Shots In Box | Shots Out | Head Shots | Shots On Target | Mins/Shot | Big Chances Tot | Big Chances Goals | Big Chances Missed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Schade** | **BRE** | **6.0** | **35** | **2748** | **8** | **8** | **0** | **3** | **343.5** | **57** | **56** | **1** | **26** | **24** | **48.2** | **22** | **7** | **15** |
| Mbeumo | MUN | 8.0 | 33 | 2613 | 11 | 11 | 0 | 1 | 237.5 | 73 | 58 | 15 | 8 | 32 | 35.8 | 22 | 9 | 13 |
| Ismaila Sarr | CRY | 6.5 | 28 | 2184 | 9 | 9 | 0 | 1 | 242.7 | 48 | 40 | 8 | 4 | 21 | 45.5 | 19 | 8 | 11 |
| Dango Ouattara | BRE | 6.5 | 32 | 2312 | 7 | 7 | 0 | 2 | 330.3 | 56 | 44 | 12 | 19 | 20 | 41.3 | 18 | 5 | 13 |
| Gibbs-White | NFO | 8.0 | 37 | 3090 | 15 | 13 | 2 | 3 | 206.0 | 83 | 55 | 28 | 13 | 32 | 37.2 | 18 | 8 | 10 |

#### Brighton Midfielders Comparison (2025/26)

| Name | Team | Cost | Mins | Mins/Goal | Mins/Shot | Mins In Box | Mins On Target | Mins/Touch | Mins/CC | Mins/Cross | Mins/xA | Mins/xG | Mins/xGI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Hinshelwood** | BHA | 6.0 | 1758 | 439.5 | 47.5 | 58.6 | 117.2 | 27.5 | 117.0 | 251.1 | 751.3 | 357.3 | **242.1** |
| **Minteh** | BHA | 6.0 | 2414 | 804.7 | 58.9 | 71.0 | 219.5 | 12.9 | 55.0 | 15.2 | 471.5 | 635.3 | **270.6** |

## Project interpretation

### Decision rules

1. **Top Goal-Threat Pick**: **Kevin Schade (Brentford, £6.0m)** matches £8.0m Bryan Mbeumo with 22 big chances; elite pure volume goal threat.
2. **Top Creator / Differential Pick**: **Anton Stach (Leeds, £6.0m)** offers 4.9 pts/start, set-pieces, and elite 37.0 mins/CC at 1.3% ownership.
3. **Fixture / Penalty Route**: **Iliman Ndiaye (Everton, £6.0m)** on penalties with top GW1–6 fixtures; **Enzo Le Fee (Sunderland, £6.0m)** for spot-kicks and open-play creativity.
4. **Early Punts**: **Emiliano Buendia (£6.0m)** on pens for Villa in GW1; **Jack Hinshelwood (£6.0m)** for Brighton attacking runs.

### Practical implications

- £6.0m bracket represents the primary "value attacker" tier in 2026/27, offering primary penalty takers (Ndiaye, Le Fee, Buendia) and league-leading big chance volume (Schade) without requiring a £7.5m+ budget.

## Findings

### Evidence

- Kevin Schade recorded 22 big chances (joint-top of all FPL midfielders).
- Anton Stach posted 4.9 pts/start and 37 mins/CC (best among all £6.0m midfielders).
- Enzo Le Fee created 13 big chances (joint-8th in the entire Premier League).
- James Garner is recovering from groin surgery and doubtful for GW1.

## Decision

**Verdict**: Kevin Schade (£6.0m) and Anton Stach (£6.0m) are the standout value midfield picks; Iliman Ndiaye (£6.0m) and Enzo Le Fee (£6.0m) provide penalty-backed fixture security.

## Risks and unknowns

- Brentford signing Jaidon Anthony adding competition for Schade.
- Harry Wilson's arrival at Leeds potentially pushing Anton Stach into a deeper holding role.
- Kaoru Mitoma's return timeline affecting Minteh and Hinshelwood minutes.

## Refresh checklist

- [x] Recheck source page using Playwright rendering.
- [x] Transcribe all player analysis and statistical images into Markdown.
- [x] Cross-check with `expected-role-gw1-5.md` and `fpl-summer-transfers.md`.
- [x] Delete `.tmp/agent/` scratch files before completion.
