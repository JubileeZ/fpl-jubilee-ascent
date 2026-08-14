# FPL 2026/27 £5.0m Defenders — Fantasy Football Scout Synthesis

**Updated**: 2026-08-13T23:15:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-07-30 (unchanged on 2026-08-13 recheck); accessed 2026-08-13
**Season**: 2026/27  
**Status**: Source synthesis · image stats extracted · cross-checked  
**Purpose**: Capture source-led £5.0m defender shortlist, team defensive metrics, player attacking stats, and minutes/rotation evidence  
**Scope**: Featured candidates across Nottingham Forest, Newcastle, Manchester United, Sunderland, Liverpool, Leeds, and Crystal Palace. Extracted image data tables included. No independent model validation.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md) · [£4.5m defenders](fpl-4-5m-defenders.md) · [Expected role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) · [Summer transfers](fpl-summer-transfers.md)

## Sources

- **Primary**: [Best £5.0m defenders for FPL 2026/27 — FPL Marc, Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/30/best-5-0m-defenders-for-fpl-2026-27) — published 2026-07-30; accessed 2026-07-31; role: £5.0m defender analysis and image stats extraction

**Source boundary**: Source claims not independently validated. Promotional graphics, ads, logos, and non-relevant photos omitted; article statistical image tables and player match logs transcribed directly into Markdown tables.

## Agent Prompt

```text
Full redo docs/research/fpl-5-0m-defenders.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`) to bypass dynamic loading and account truncation.
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Extract 100% of full-page rendered text for all covered players (no partial truncation).
4. Dynamically discover, download, and inspect all image assets in article entry content (`.entry-content img`). Exclude promotional banners, ad images, site logos, author avatars, and decorative photos.
5. Extract and transcribe 100% of relevant statistical data images (team metric tables, player stat graphics, DefCon charts, match logs, fixture tickers) into Markdown tables.
6. Keep Source synthesis strictly separate from Project interpretation.
7. If new primary articles appear under 'BEST FPL PLAYERS FOR 2026/27' on the pre-season guide index, generate dedicated research notes for them following this exact process and update docs/research/fpl-preseason-guide.md.
8. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
9. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Primary-source synthesis & Playwright image data extraction

**Inputs**:
- Playwright rendered article text
- Dynamically fetched article image assets in `.entry-content`

**Procedure**:
1. Extract featured £5.0m defender candidates and club profiles.
2. Inspect all article `.entry-content` image assets; filter out non-data promotional graphics, ads, site logos, author gravatars, and decorative photos.
3. Inspect and transcribe all data-bearing statistical graphics (player attacking stats, team shots on target conceded, and Jaydee Canvot match log) into Markdown tables.
4. Record minutes, set-piece roles, DefCon rates, and early schedule ratings.
5. Translate source claims into conditional project monitoring rules.

**Definitions and assumptions**:
- **PPMPM**: Points per million per match (source shorthand).
- **DefCon**: Defensive contribution scoring measure.
- **Featured candidates**: £5.0m options receiving substantive article analysis.

**Validation boundary**: Article-only synthesis. Minutes, transfers, injury recovery, and fixture ratings subject to change before Gameweek 1.

## Source synthesis

### Extracted image statistics tables

#### Defender attacking statistics (2025/26 season sample)
*Source graphic: Defender attacking metrics (sorted by Shots On Target descending)*

| Name | Team | Cost | Mins | Goals (Tot/In/Out/H) | Shots (Tot/In/Out/H/On) | Big Chances (Tot/Goals/Miss) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Williams (Neco)** | NFO | £5.0m | 3211 | 2 (1 in, 1 out, 0 H) | 46 (17 in, 29 out, 2 H, **19 On**) | 2 (0 goals, 2 miss) |
| **O'Reilly** | MCI | £6.5m | 2665 | 5 (5 in, 0 out, 2 H) | 41 (33 in, 8 out, 13 H, **15 On**) | 10 (3 goals, 7 miss) |
| **van Dijk** | LIV | £6.5m | 3420 | 6 (6 in, 0 out, 5 H) | 30 (27 in, 3 out, 23 H, **14 On**) | 12 (4 goals, 8 miss) |
| **Thiaw** | NEW | £5.0m | 2986 | 4 (4 in, 0 out, 2 H) | 28 (26 in, 2 out, 16 H, **14 On**) | 10 (4 goals, 6 miss) |
| **Kadioglu** | BHA | £4.5m | 3149 | 1 (1 in, 0 out, 0 H) | 28 (15 in, 14 out, 1 H, **13 On**) | 4 (1 goals, 3 miss) |
| **Muñoz** | CRY | £5.5m | 2393 | 4 (3 in, 1 out, 1 H) | 27 (23 in, 4 out, 4 H, **13 On**) | 4 (3 goals, 1 miss) |

#### Team defensive metrics — Shots on target conceded (2025/26 season)
*Source graphic: Team defensive metrics (sorted by Shots On Target Conceded ascending)*

| Team | Goals Conceded | Clean Sheets | Goal Attempts Conceded | Shots On Target Conceded | Big Chances Conceded | xG Conceded |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ARS** | 27 | 19 | 314 | 87 | 50 | 28.30 |
| **MCI** | 35 | 16 | 372 | 124 | 76 | 44.20 |
| **MUN** | 50 | 8 | 444 | 138 | 72 | 48.57 |
| **BHA** | 46 | 10 | 443 | 142 | 77 | 49.13 |
| **FUL** | 51 | 9 | 452 | 145 | 96 | 53.31 |
| **EVE** | 50 | 11 | 534 | 149 | 93 | 56.51 |
| **LIV** | 53 | 10 | 437 | 150 | 85 | 47.43 |
| **TOT** | 57 | 9 | 468 | 150 | 78 | 52.32 |

#### Jaydee Canvot — Match log (>40 mins played, Crystal Palace)
*Source graphic: Player match log*

| GW | Match | Score | Starts | Mins | DefCon (DC) | Points |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **11** | CRY vs BHA | 0 - 0 | 1 | 90 | 2 | 10 |
| **21** | CRY vs AVL | 0 - 0 | 1 | 90 | 2 | 10 |
| **27** | CRY vs WOL | 1 - 0 | 1 | 90 | 0 | 5 |
| **28** | MUN vs CRY | 2 - 1 | 1 | 90 | 2 | 3 |
| **29** | TOT vs CRY | 1 - 3 | 1 | 90 | 0 | 2 |
| **32** | CRY vs NEW | 2 - 1 | 1 | 90 | 2 | 4 |
| **33** | CRY vs WHU | 0 - 0 | 1 | 90 | 2 | 10 |
| **34** | LIV vs CRY | 3 - 1 | 1 | 90 | 2 | 3 |
| **35** | BOU vs CRY | 3 - 0 | 1 | 90 | 0 | 0 |
| **36** | CRY vs EVE | 2 - 2 | 1 | 90 | 0 | 1 |
| **36** | MCI vs CRY | 3 - 0 | 1 | 90 | 2 | 3 |
| **37** | BRE vs CRY | 2 - 2 | 1 | 90 | 2 | 3 |
| **30** | CRY vs LEE | 0 - 0 | 1 | 77 | 2 | 11 |
| **23** | CRY vs CHE | 1 - 3 | 1 | 60 | 0 | 0 |
| **20** | NEW vs CRY | 2 - 0 | 0 | 58 | 2 | 2 |

### Featured candidates

- **Neco Williams — Nottingham Forest, £5.0m**: 3,211 mins; 2 goals (1 in, 1 out), 46 shots (19 on target — top among £5.0m defenders). Source highlights attacking involvement, crossing, and long-range shooting. *Cross-check*: Confirmed Nailed Starter in `expected-role-gw1-5.md`; Draft Shortlist eligible.
- **Malick Thiaw — Newcastle United, £5.0m**: 2,986 mins; 4 goals, 28 shots (26 in box, 16 headers, 14 on target), 10 big chances (4 goals, 6 missed), xG 4.72 (3rd among PL defenders). Newcastle schedule ranks 1st over opening 10 GWs. *Cross-check*: Confirmed Nailed Starter in `expected-role-gw1-5.md`; Draft Shortlist eligible.
- **Lewis Hall — Newcastle United, £5.0m**: 21-year-old attacking full-back; 7 assists in 2024/25. Newcastle opening 10 GW schedule rank 1st; GW1 vs Liverpool. *Cross-check*: Classified as Rotation in `expected-role-gw1-5.md` (behind Livramento Nailed); excluded from fit-role Draft Shortlist.
- **Dan Ballard — Sunderland, £5.0m**: 0.80 PPMPM (2nd best value at £5.0m). 24 starts: 8 big chances (joint-4th among defenders), 25 box shots, 15 DefCon points. Opening trip to Ipswich; schedule worsens through GW6 (2nd worst fixture run). Teammate **Omar Alderete (£5.0m)** also cited. *Cross-check*: Both Ballard and Alderete confirmed Nailed Starters in `expected-role-gw1-5.md`; Draft Shortlist eligible.
- **Harry Maguire — Manchester United, £5.0m**: Manchester United 4th best for limiting shots on target (138), big chances (72), xGC (48.57). Under Carrick, fixtures rank 2nd over first 6 and 10 GWs (starts vs two promoted clubs). Cited for set-piece target potential post-Casemiro departure. **Diogo Dalot (£5.0m)** noted as alternative (6 assists, 5 big chances). *Cross-check*: Both Maguire and Dalot confirmed Nailed Starters in `expected-role-gw1-5.md`; Draft Shortlist eligible.
- **Jeremy Jacquet — Liverpool, £5.0m**: £55m signing from Rennes as Konate replacement. Liverpool xGC 47.43 (3rd best). Recovering from season-ending shoulder injury sustained in February; manager Iraola notes cautious preseason easing. *Cross-check*: Classified as Regular Starter in `expected-role-gw1-5.md`; Draft Shortlist eligible, watch pre-season minutes.
- **Tarik Muharemovic — Leeds United, £5.0m**: £34.1m left-footed centre-back replacement for Pascal Struijk. 6ft 4in; averaged 10.8 DefCon actions per 90 at Sassuolo (exceeded only by Senesi, Mavropanos, Lacroix among PL defenders with 2,200+ mins). Leeds Schedule avoids top 7 until GW6; 4 clean sheets in final 8 matches. *Cross-check*: Confirmed transfer 14–17 July (£34.1m) in `fpl-summer-transfers.md`; Regular Starter in `expected-role-gw1-5.md`; Draft Shortlist eligible.
- **Jaydee Canvot — Crystal Palace, £5.0m**: Regular starter from GW27; 14 starts delivered 4 double-digit hauls and 10 DefCon returns. Teammate **Chris Richards (£5.0m)** has lower DefCon rate but 3.74 xGI. *Cross-check*: Confirmed Maxence Lacroix transferred CRY → CHE (£52m, 30 July) in `fpl-summer-transfers.md`, solidifying Palace CB roles; Richards Nailed, Canvot Regular in `expected-role-gw1-5.md`.

## Project interpretation

### Decision rules

- Gate £5.0m defender picks on confirmed starting status and early fixture schedules.
- Treat Thiaw and Williams as high-volume goal/shot threat options.
- Treat Muharemovic and Canvot as high-floor DefCon targets.
- Demote Lewis Hall to watch/rotation pool due to Livramento nailed role.
- Monitor Jacquet's shoulder injury recovery before considering for GW1.

### Practical implications

- Thiaw benefits from Newcastle's #1 ranked 10-game opening schedule; Hall restricted by rotation role.
- Maguire / Dalot gain value from Man Utd's #2 ranked opening schedule and improved Carrick defensive metrics.
- Muharemovic provides direct DefCon replacement value following Struijk's departure to Brighton.
- Canvot and Richards gain secured minutes following Lacroix's £52m departure to Chelsea.

## Findings

### Evidence

- Williams leads all £5.0m defenders in total shots (46) and shots on target (19).
- Thiaw ranks 3rd among all PL defenders for xG (4.72) with 10 big chances.
- Newcastle holds the #1 ranked opening 10-game schedule on Fixture Ticker.
- Canvot delivered 4 double-digit hauls across 14 starts for Crystal Palace.
- Cross-check against `expected-role-gw1-5.md`: Williams, Thiaw, Ballard, Alderete, Maguire, Dalot (Nailed) and Jacquet, Muharemovic, Canvot (Regular) belong to fit-role Draft Shortlist; Hall (Rotation) excluded.
- Cross-check against `fpl-summer-transfers.md`: Lacroix sale to Chelsea solidifies Richards/Canvot roles; Muharemovic £34.1m move to Leeds replaces Struijk.

## Decision

**Verdict**: Source £5.0m watchlist highlights Thiaw (Newcastle schedule), Williams (shot volume), Maguire/Dalot (Man Utd schedule), Muharemovic (DefCon floor), and Canvot/Richards (haul upside / Lacroix departure). Hall demoted to rotation status.

**Recommended action**:
- Verify preseason starting XI roles for Thiaw, Jacquet, and Muharemovic.
- Use extracted shot and DefCon tables as model benchmark inputs.
- Exclude Hall from primary GW1–5 draft shortlist until starting role confirmed.

**Trigger / kill switch**:
- Drop candidate if starting role is lost to rotation or injury recovery delays.

## Risks and unknowns

- Jacquet shoulder injury recovery timeline under Iraola.
- Newcastle head coach transition and defensive regression (only 3 clean sheets from GW8).
- Sunderland European fixture congestion affecting Ballard/Alderete.
- Hall competition with Livramento for Newcastle full-back spots.

## Refresh checklist

- [x] Recheck source URL using Playwright extraction.
- [x] Confirm title, author (FPL Marc), publication date, and prices.
- [x] Transcribe 100% of statistical image tables (Attacking stats, Team defensive stats, Canvot log).
- [x] Omit non-data promotional images and headers.
- [x] Cross-check candidates against `expected-role-gw1-5.md` and `fpl-summer-transfers.md`.
- [x] Update `Updated`, `Data stamp`, and `Risks`.
- [x] Delete `.tmp/agent/` scratch before finishing.
