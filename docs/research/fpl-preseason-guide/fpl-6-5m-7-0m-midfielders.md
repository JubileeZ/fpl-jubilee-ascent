# FPL 2026/27: Best £6.5m–£7.0m Midfielders

**Updated**: 2026-08-18T15:05:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-08-06 (unchanged on 2026-08-13 recheck); accessed 2026-08-13; Playwright recheck 2026-08-18: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Assess £6.5m–£7.0m mid-premium midfielders for FPL 2026/27 starting XI selection, set-piece involvement, talismanic roles, and transfer impacts  
**Scope**: All key midfielders priced at £6.5m and £7.0m in FPL 2026/27  
**Related**: [Pre-season guide](fpl-preseason-guide.md) · [£5.0m midfielders](fpl-5-0m-midfielders.md) · [£6.0m midfielders](fpl-6-0m-midfielders.md) · [£7.5m+ midfielders](fpl-7-5m-midfielders.md) · [Summer transfers](fpl-summer-transfers.md)

> Note revision created 2026-08-09 from Fantasy Football Scout full price-bracket review. Primary article published 2026-08-06. Source claims cross-checked with expected-role-gw1-5.md and fpl-summer-transfers.md.

## Sources

- **Primary**: [Best £6.5m-£7.0m midfielders for FPL 2026/27 — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/08/06/best-6-5m-7-0m-midfielders-for-fpl-2026-27) — published 2026-08-06; accessed 2026-08-13; role: £6.5m–£7.0m midfielder analysis, Opta playing time / DefCon / points per start / big chance data
- **Cross-check**: [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — updated 2026-08-06; role: starter status, minutes expectations, tactical positions
- **Cross-check**: [Confirmed Summer Transfers](fpl-summer-transfers.md) — updated 2026-08-09; role: confirmed transfer moves (Bruno Guimaraes to Arsenal £75m, Elliot Anderson to Man City £116m, Harry Wilson to Leeds free)

**Source boundary**: Source claims cross-checked against internal project notes. No live FPL API refresh or solver optimization run performed in this note.

## Agent Prompt

```text
Full redo docs/research/fpl-preseason-guide/fpl-6-5m-7-0m-midfielders.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`).
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Extract full text and analysis for all covered £6.5m–£7.0m midfielders.
4. Transcribe 100% of Opta statistical images (Minutes per appearance, Total DefCon points, Big chances total, Points per start) into Markdown tables.
5. Keep Source synthesis strictly separate from Project interpretation.
6. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
7. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Source synthesis / price bracket analysis & cross-check audit

**Inputs**:
- Fantasy Football Scout article (`best-6-5m-7-0m-midfielders-for-fpl-2026-27`)
- Expected Role GW1–5 note (`expected-role-gw1-5.md`)
- Confirmed Summer Transfers register (`fpl-summer-transfers.md`)

**Procedure**:
1. Extract player profiles, tactical roles, transfer impacts, and set-piece responsibilities for all £6.5m and £7.0m midfielders.
2. Transcribe Opta statistical images: Minutes per appearance, Total DefCon points, Total Big chances, Points per start.
3. Categorize options into Premium Elite Value, Goal Threat Talismans, High-Floor DefCon/Points-per-Start Anchors, and High-Risk/Differential Punts.
4. Synthesize decision rules and team-structure recommendations.

**Definitions and assumptions**:
- **£6.5m–£7.0m MID**: Midfielders priced at £6.5m or £7.0m in FPL 2026/27.

## Source synthesis

### Featured £6.5m–£7.0m Midfielders Analysis

- **Dominik Szoboszlai (Liverpool, £7.0m)**:
  - Started 36 of 38 league matches in 2025/26, subbed off only once (89.8 mins/app, matching James Garner for league-high playing time stability).
  - 6 goals (4 direct free-kicks), 7 assists, 20 DefCon points.
  - Ranked 2nd among all Fantasy midfielders for crosses (205) and chances created (78).
  - Candidate for penalties post-Salah. Under Iraola, Florian Wirtz (£7.5m) is favored at #10, so Szoboszlai will operate in central midfield / right-back. Liverpool tops Fixture Ticker GW1–5.
- **Kiernan Dewsbury-Hall (Everton, £6.5m)**:
  - 8 goals, 7 assists, 10 DefCons, 18 bonus points in 31 matches (5.0 pts/start average).
  - High reliability (84.5 mins/app), set-piece duties (corners and free-kicks), and Everton's #1 fixture ticker in GW1–6.
- **Elliot Anderson (Manchester City, £6.5m)**:
  - #1 in the ENTIRE LEAGUE for DefCon points in 2025/26 (52 DefCons, ~70% match success rate).
  - 4 goals, 5 assists at Nottingham Forest.
  - Moved to Manchester City for £116m. City's 61% possession may reduce total defensive volume, but Rodri's back surgery rehabilitation opens a starting midfield role with set-piece share under Enzo Maresca.
- **Ismaila Sarr (Crystal Palace, £6.5m)**:
  - 9 goals, 2 assists in 24 starts (242.7 mins/goal).
  - 3rd among all midfielders for big chances in 2025/26 (19 big chances).
  - Deployed in the frontline alongside Jean-Philippe Mateta in Pierre Sage's 3-4-3; secondary penalty taker when Mateta is off. Favourable fixtures from GW3.
- **Dango Ouattara (Brentford, £6.5m)**:
  - 7 goals, 8 assists in 32 matches, averaging 5.2 points per start.
  - 4th among all midfielders for big chances (18 big chances).
  - Brentford has no European congestion; strong home record (only 3 defeats in 19 home games in 2025/26).
- **Bruno Guimaraes (Arsenal, £7.0m)**:
  - 9 goals (2 penalties), 7 assists in 26 games for Newcastle; 8 double-digit hauls (3rd-most in league).
  - £75m summer transfer to Arsenal. Competing in crowded midfield (Rice, Zubimendi, Odegaard, Merino) and likely to lose set pieces.
- **Phil Foden (Manchester City, £7.0m)**:
  - Underwhelmed in 2025/26 (7 goals, 5 assists, with 7 returns in GW13–16), but averaged 5.3 pts/start.
  - Enzo Maresca reported to view Foden as a central pillar; captained City in pre-season; favorable early fixture run.
- **Harry Wilson (Leeds, £6.5m)**:
  - 10 goals, 9 assists in 36 matches for Fulham (overperformed 10.61 xGI).
  - Free transfer to Leeds United; set-piece taker with 3 home matches in first 5 GWs.
- **Other £6.5m–£7.0m Mentions**:
  - **Christos Tzolis (Arsenal, £6.5m)**: Strong GW1 punt vs Coventry before returning internationals (Saka, Martinelli, Madueke) take over.
  - **Estevao & Pedro Neto (Chelsea, £6.5m)**: Estevao fit and scored vs Spurs; competing with Neto.
  - **Enzo Fernandez (Chelsea, £7.0m)**: Deep role under Alonso and tough opening fixtures.
  - **Rayan (Bournemouth, £6.5m)**: Target for GW9+ fixture swing.

---

### 2025/26 Opta Statistical Data

#### Midfielders Sorted by Minutes per Appearance (M/App) (2025/26)

| Name | Team | Cost | App | Starts | Mins | On | Off | M/App | M/Strt |
|---|---|---|---|---|---|---|---|---|---|
| Garner | EVE | 6.0 | 38 | 38 | 3413 | 0 | 1 | **89.8** | 89.8 |
| **Szoboszlai** | **LIV** | **7.0** | **36** | **36** | **3231** | **0** | **1** | **89.8** | **89.8** |
| Rogers | AVL | 7.5 | 37 | 37 | 3279 | 0 | 5 | **88.6** | 88.6 |
| Ampadu | LEE | 5.5 | 35 | 35 | 3078 | 0 | 4 | **87.9** | 87.9 |
| **Anderson (Elliot)** | **NFO** | **6.5** | **38** | **37** | **3332** | **1** | **4** | **87.7** | **88.8** |

#### All Premier League Players Sorted by DefCon Points (DC) (2025/26)

| Name | Team | Cost | App | Starts | Mins | On | Off | M/App | M/Strt | G | A | CS | GC | OG | YC | RC | sBln | ARtn | Rtn | DC | B | DD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Anderson (Elliot)** | **NFO** | **6.5** | **38** | **37** | **3332** | **1** | **4** | **87.7** | **88.8** | **4** | **5** | **10** | **50** | **0** | **8** | **0** | **11** | **9** | **9** | **52** | **16** | **3** |
| Senesi | BOU | 6.0 | 37 | 37 | 3285 | 0 | 2 | 88.8 | 88.8 | 0 | 6 | 11 | 53 | 0 | 8 | 0 | 19 | 6 | 17 | **50** | 14 | 4 |
| Tarkowski | EVE | 6.0 | 37 | 37 | 3330 | 0 | 0 | 90.0 | 90.0 | 2 | 3 | 11 | 48 | 0 | 8 | 0 | 16 | 5 | 16 | **44** | 12 | 3 |
| Andersen | FUL | 5.0 | 33 | 33 | 2873 | 0 | 1 | 87.1 | 87.1 | 0 | 1 | 8 | 44 | 0 | 7 | 1 | 18 | 1 | 9 | **40** | 8 | 3 |
| Garner | EVE | 6.0 | 38 | 38 | 3413 | 0 | 1 | 89.8 | 89.8 | 2 | 7 | 11 | 50 | 0 | 12 | 0 | 15 | 9 | 9 | **40** | 13 | 3 |
| Lacroix | CRY | 6.0 | 35 | 35 | 3085 | 0 | 1 | 88.1 | 88.1 | 1 | 2 | 11 | 45 | 0 | 4 | 1 | 18 | 3 | 14 | **40** | 11 | 4 |

#### Midfielders Sorted by Big Chances Total (2025/26)

| Name | Team | Cost | App | Mins | Goals Tot | Goals In Box | Goals Out | Head Goals | Mins/Goal | Shots Tot | Shots In Box | Shots Out | Head Shots | Shots On Target | Mins/Shot | Big Chances Tot | Big Chances Goals | Big Chances Missed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Mbeumo | MUN | 8.0 | 33 | 2613 | 11 | 11 | 0 | 1 | 237.5 | 73 | 58 | 15 | 8 | 32 | 35.8 | **22** | 9 | 13 |
| Schade | BRE | 6.0 | 35 | 2748 | 8 | 8 | 0 | 3 | 343.5 | 57 | 56 | 1 | 26 | 24 | 48.2 | **22** | 7 | 15 |
| **Ismaila Sarr** | **CRY** | **6.5** | **28** | **2184** | **9** | **9** | **0** | **1** | **242.7** | **48** | **40** | **8** | **4** | **21** | **45.5** | **19** | **8** | **11** |
| Gibbs-White | NFO | 8.0 | 37 | 3090 | 15 | 13 | 2 | 3 | 206.0 | 83 | 55 | 28 | 13 | 32 | 37.2 | **18** | 8 | 10 |
| **Dango Ouattara** | **BRE** | **6.5** | **32** | **2312** | **7** | **7** | **0** | **2** | **330.3** | **56** | **44** | **12** | **19** | **20** | **41.3** | **18** | **5** | **13** |

#### Midfielders Sorted by Points per Start (Pts/Strt) (2025/26)

| Name | Team | Cost | App | Starts | Mins | On | Off | M/App | M/Strt | G | A | CS | GC | OG | YC | RC | sBln | ARtn | DC | B | DD | Tot Pts | M/Pt | Pts/Strt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bruno Fernandes | MUN | 12.0 | 35 | 35 | 3062 | 0 | 6 | 87.5 | 87.5 | 9 | 24 | 7 | 46 | 0 | 5 | 0 | 10 | 33 | 10 | 41 | 12 | 235 | 13.0 | **6.7** |
| Cherki | MCI | 7.5 | 33 | 19 | 1866 | 14 | 14 | 56.5 | 77.0 | 4 | 13 | 8 | 18 | 0 | 1 | 0 | 6 | 17 | 4 | 16 | 5 | 135 | 13.8 | **5.8** |
| Doku | MCI | 7.5 | 30 | 19 | 1837 | 11 | 14 | 61.2 | 79.5 | 5 | 8 | 8 | 18 | 0 | 0 | 0 | 9 | 13 | 0 | 15 | 5 | 120 | 15.3 | **5.7** |
| Saka | ARS | 9.5 | 31 | 25 | 2240 | 6 | 10 | 72.3 | 82.1 | 7 | 10 | 12 | 16 | 0 | 2 | 0 | 10 | 17 | 10 | 18 | 5 | 157 | 14.3 | **5.7** |
| Semenyo | MCI | 8.5 | 37 | 37 | 3200 | 0 | 10 | 86.5 | 86.5 | 17 | 6 | 12 | 52 | 0 | 7 | 0 | 13 | 23 | 6 | 18 | 5 | 202 | 15.8 | **5.5** |
| **Bruno Guimarães** | **NEW** | **7.0** | **29** | **27** | **2459** | **2** | **8** | **84.8** | **88.1** | **9** | **7** | **6** | **37** | **0** | **6** | **0** | **11** | **16** | **10** | **22** | **8** | **154** | **16.0** | **5.4** |
| **Foden** | **MCI** | **7.0** | **33** | **23** | **2142** | **10** | **10** | **64.9** | **83.3** | **7** | **5** | **11** | **19** | **0** | **4** | **0** | **15** | **12** | **6** | **13** | **6** | **131** | **16.4** | **5.3** |
| **Dango Ouattara** | **BRE** | **6.5** | **32** | **25** | **2312** | **7** | **13** | **72.3** | **84.0** | **7** | **8** | **6** | **35** | **0** | **5** | **0** | **11** | **15** | **4** | **16** | **5** | **136** | **17.0** | **5.2** |

## Project interpretation

### Decision rules

1. **Top Premium Value (£7.0m)**: **Dominik Szoboszlai (Liverpool, £7.0m)** is the standout £7.0m asset; near-100% starter (89.8 mins/app), set-piece dominance, potential post-Salah penalty taker, and top GW1–5 fixtures.
2. **Top Goal-Threat Value (£6.5m)**: **Ismaila Sarr (Crystal Palace, £6.5m)** and **Dango Ouattara (Brentford, £6.5m)** offer elite big chance numbers (19 and 18 big chances respectively, matching £8.0m assets).
3. **Fixture / Consistency Anchor (£6.5m)**: **Kiernan Dewsbury-Hall (Everton, £6.5m)** offers 5.0 pts/start and set-pieces with Everton's #1 fixture ticker.
4. **DefCon Hybrid Watch (£6.5m)**: **Elliot Anderson (£6.5m)** if starting in Rodri's absence under Maresca.

### Practical implications

- £6.5m–£7.0m bracket contains elite semi-premiums (Szoboszlai, Sarr, Dewsbury-Hall, Dango) that can match £8.0m–£9.5m output at substantial price discounts.

## Findings

### Evidence

- Szoboszlai averaged 89.8 mins/app, created 78 chances (2nd among midfielders), and took 205 crosses.
- Elliot Anderson led all Premier League players with 52 DefCon points in 2025/26.
- Ismaila Sarr (19 big chances) and Dango Ouattara (18 big chances, 5.2 pts/start) rival £8.0m premiums.
- Dewsbury-Hall averaged 5.0 pts/start with Everton topping the early fixture ticker.

## Decision

**Verdict**: Dominik Szoboszlai (£7.0m) is the prime £7.0m midfield target; Ismaila Sarr (£6.5m) and Kiernan Dewsbury-Hall (£6.5m) are the top £6.5m midfield picks.

## Risks and unknowns

- Szoboszlai's tactical position under Iraola (central midfield vs right-back).
- Anderson's DefCon volume reduction in high-possession Man City side.
- Bruno Guimaraes minutes and set-piece loss in Arsenal's crowded midfield.

## Refresh checklist

- [x] Recheck source page using Playwright rendering.
- [x] Transcribe all player analysis and statistical tables into Markdown.
- [x] Cross-check with `expected-role-gw1-5.md` and `fpl-summer-transfers.md`.
- [x] Delete `.tmp/agent/` scratch files before completion.
