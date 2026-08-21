# FPL 2026/27 £4.5m Defenders — Fantasy Football Scout Synthesis

**Updated**: 2026-08-21T13:27:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-07-29 (unchanged on 2026-08-13 recheck); accessed 2026-08-13; Playwright recheck 2026-08-21: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Source synthesis · image stats extracted · cross-checked  
**Purpose**: Capture source-led £4.5m defender shortlist, team defensive metrics, clean-sheet probabilities, long-throw statistics, and minutes/rotation evidence  
**Scope**: Featured candidates across Manchester United, Crystal Palace, Leeds, Brentford, Nottingham Forest, Brighton, Aston Villa, and Fulham. Extracted image data tables included. Cross-checked against GW1-5 role priors and summer transfer register.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md) · [£5.0m defenders](fpl-5-0m-defenders.md) · [Expected role GW1-5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) · [Summer transfers](fpl-summer-transfers.md)

## Sources

- **Primary**: [Best £4.5m defenders for FPL 2026/27 — avfc82, Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/29/best-4-5m-defenders-for-fpl-2026-27) — published 2026-07-29; accessed 2026-07-31; re-verified 2026-08-01; role: £4.5m defender analysis and image stats extraction
- **Cross-check**: [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — role priors & availability overlay (verified 2026-08-01)
- **Cross-check**: [Confirmed Summer Transfers](fpl-summer-transfers.md) — confirmed transfers register (verified 2026-08-01)

**Source boundary**: Source claims not independently validated. Promotional graphics, ads, logos, and non-relevant photos omitted; article statistical image tables and clean-sheet odds graphics transcribed directly into Markdown tables.

## Agent Prompt

```text
Full redo docs/research/fpl-4-5m-defenders.md

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
1. Extract featured £4.5m defender candidates across all 15 covered clubs.
2. Inspect all article `.entry-content` image assets; filter out non-data promotional graphics, ads, site logos, author gravatars, and decorative photos.
3. Inspect and transcribe all data-bearing statistical graphics (post-Carrick defensive stats, GW19+ clean sheets, throw-ins into box, and clean-sheet probability sequences) into Markdown tables.
4. Record minutes, set-piece roles, DefCon rates, long-throw stats, and early schedule ratings.
5. Translate source claims into conditional project monitoring rules.

**Definitions and assumptions**:
- **DefCon**: Defensive contribution scoring measure.
- **Points per start**: Article statistic, not recomputed here.
- **Long throws into box**: Article statistic tracking throw-in danger.

**Validation boundary**: Article-only synthesis. Minutes, transfers, formations, fixture ratings, and clean-sheet probabilities subject to change before Gameweek 1.

## Source synthesis

### Extracted image statistics tables

#### Team defensive metrics — Post-Carrick 17-match sample (2025/26 season)
*Source graphic: Post-Carrick defensive metrics (sorted by Clean Sheets descending)*

| Team | Played | Goals (G) | Open Play (OA) | Set Play (FA) | Total Attempts (TA) | Clean Sheets (CS) | Goals Conceded (GC) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ARS** | 17 | 31 | 24 | 3 | 27 | **9** | 13 |
| **MCI** | 17 | 32 | 24 | 5 | 29 | **7** | 16 |
| **BOU** | 17 | 24 | 17 | 6 | 23 | **6** | 14 |
| **MUN** | 17 | 33 | 23 | 5 | 28 | **6** | 18 |
| **NFO** | 17 | 27 | 21 | 5 | 26 | **6** | 17 |
| **WHU** | 17 | 24 | 20 | 3 | 23 | **6** | 22 |

#### Team defensive metrics — 20 matches from GW19 onwards (2025/26 season)
*Source graphic: GW19+ defensive metrics (sorted by Clean Sheets descending)*

| Team | Played | Goals (G) | Open Play (OA) | Set Play (FA) | Total Attempts (TA) | Clean Sheets (CS) | Goals Conceded (GC) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ARS** | 20 | 38 | 29 | 5 | 34 | **10** | 16 |
| **MCI** | 20 | 34 | 24 | 7 | 31 | **8** | 18 |
| **BRE** | 20 | 27 | 19 | 6 | 25 | **7** | 26 |
| **LEE** | 20 | 24 | 14 | 8 | 22 | **6** | 24 |
| **BHA** | 20 | 26 | 18 | 7 | 25 | **6** | 21 |
| **WHU** | 20 | 27 | 21 | 5 | 26 | **6** | 29 |
| **BOU** | 20 | 31 | 21 | 6 | 28 | **6** | 21 |
| **NFO** | 20 | 30 | 23 | 5 | 28 | **6** | 23 |
| **MUN** | 20 | 37 | 26 | 5 | 31 | **6** | 22 |

#### Long throw-ins into the penalty box (2025/26 season)
*Source graphic: Throw-ins into penalty box (sorted by Throws Into Box descending)*

| Name | Team | Cost | Total Throw Ins | Throws Into Box | Successful Throws Into Box |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Kayode** | BRE | £4.5m | 391 | **169** | 38 |
| **Ampadu** | LEE | £5.5m | 151 | **138** | 32 |
| **Mukiele** | SUN | £5.5m | 236 | **111** | 25 |
| **Richards (Chris)** | CRY | £5.0m | 128 | **103** | 30 |
| **Walker** | BUR | £4.4m | 321 | **81** | 20 |
| **Hill (James)** | BOU | £5.5m | 95 | **64** | 10 |

#### Clean sheet probability percentages by club (2026/27 opening fixtures)

- **Manchester United (Luke Shaw — £4.5m)** (*source CS odds graphic*):
  - GW1 vs HUL (A): **39%** · GW2 vs IPS (H): **46%** · GW3 vs EVE (A): **30%** · GW4 vs MCI (H): **26%** · GW5 vs FUL (A): **31%** · GW6 vs TOT (H): **36%**
- **Crystal Palace (Tyrick Mitchell — £4.5m)** (*source CS odds graphic*):
  - GW1 vs EVE (A): **32%** · GW2 vs MCI (H): **24%** · GW3 vs FUL (A): **33%** · GW4 vs IPS (H): **45%** · GW5 vs LEE (A): **36%** · GW6 vs NFO (H): **38%**
- **Leeds United (Joe Rodon — £4.5m)** (*source CS odds graphic*):
  - GW1 vs NFO (A): **26%** · GW2 vs BRE (H): **34%** · GW3 vs BHA (A): **25%** · GW4 vs NEW (H): **25%** · GW5 vs CRY (H): **28%**
- **Brentford (Michael Kayode — £4.5m)** (*source CS odds graphic*):
  - GW1 vs TOT (H): **34%** · GW2 vs LEE (A): **31%** · GW3 vs SUN (H): **39%** · GW4 vs BOU (A): **22%** · GW5 vs CHE (H): **34%** · GW6 vs AVL (A): **22%** · GW7 vs LIV (H): **27%** · GW8 vs HUL (A): **36%**
- **Nottingham Forest + Coventry Rotation (Ola Aina — £4.5m)** (*source CS odds graphic*):
  - GW1 NFO vs LEE (H): **30%** · GW2 COV vs HUL (H): **37%** · GW3 NFO vs TOT (H): **23%** · GW4 COV vs BHA (H): **28%** · GW5 NFO vs COV (H): **35%**
- **Brighton (Ferdi Kadioglu / Lewis Dunk / Maxim De Cuyper — £4.5m)** (*source CS odds graphic*):
  - GW1 vs AVL (H): **32%** · GW2 vs CHE (A): **23%** · GW3 vs LEE (H): **41%** · GW4 vs COV (A): **35%** · GW5 vs ARS (H): **15%** · GW6 vs SUN (A): **30%**
- **Aston Villa (Matty Cash — £4.5m)** (*source CS odds graphic*):
  - GW1 vs BHA (A): **26%** · GW2 vs ARS (H): **12%** · GW3 vs HUL (A): **34%** · GW4 vs NFO (H): **33%** · GW5 vs TOT (A): **23%** · GW6 vs BRE (H): **36%**
- **Fulham (Antonee Robinson — £4.5m)** (*source CS odds graphic*):
  - GW1 vs CHE (H): **25%** · GW2 vs SUN (A): **22%** · GW3 vs CRY (H): **25%** · GW4 vs LIV (A): **13%** · GW5 vs MUN (H): **26%** · GW6 vs IPS (A): **26%** · GW7 vs HUL (H): **39%** · GW8 vs COV (A): **27%**

### Main candidates

- **Luke Shaw — Manchester United, £4.5m**: 38 starts; 3.0 pts/start; 0.28 shots, 0.45 chances created, 6.27 DefCon per 90. Ownership 23.1% (highest in price group). Under Carrick, PPM rose to 3.9 across 17 matches (1 goal, 7 CS, 6 DefCon, 3 bonus). Top opening CS probabilities (39% Hull A, 46% Ipswich H).
- **Tyrick Mitchell — Crystal Palace, £4.5m**: 36 starts + 2 subs; 3.7 pts/start; 0.53 shots, 0.80 chances created, 6.84 DefCon per 90. Scored 135 points (highest in article: 1 goal, 3 assists, 12 CS, 8 bonus). CS probabilities peak at 45% (GW4 Ipswich H) and 38% (GW6 Forest H).
- **Joe Rodon — Leeds, £4.5m**: 33 starts + 2 subs; 3.3 pts/start; 0.55 shots, 0.27 chances created, 8.31 DefCon per 90. Joint-most DefCon points among £4.5m defenders (18 pts). Leeds kept 6 CS in 20 matches from GW19; 15 headed attempts.
- **Michael Kayode — Brentford, £4.5m**: 37 starts; 3.1 pts/start; 0.25 shots, 0.94 chances created, 6.05 DefCon per 90. Created 34 chances; delivered 169 long throws into box (1st in Premier League). Brentford 7 CS in 20 matches post-GW19.
- **Ola Aina — Nottingham Forest, £4.5m**: 18 starts; 3.7 pts/start; 0.68 shots, 0.51 chances created, 7.37 DefCon per 90. Back-three trial under Glasner; rotates with Coventry for 30%+ CS probabilities in GW1, GW2, GW5.
- **Ferdi Kadioglu — Brighton, £4.5m**: 34 starts + 3 subs; 3.4 pts/start; 0.80 shots, 0.60 chances created, 4.89 DefCon per 90. Established starting left-back; 41% CS probability in GW3 vs Leeds.
- **Lewis Dunk — Brighton, £4.5m**: 31 starts + 2 subs; 3.2 pts/start; 0.76 shots, 0.22 chances created, 7.41 DefCon per 90. 16 DefCon points; 15 headed goal attempts.
- **Maxim De Cuyper — Brighton, £4.5m**: 17 starts + 13 subs; 3.6 pts/start; 0.80 shots, 1.96 chances created, 3.98 DefCon per 90. Assist potential, but un-nailed.
- **Matty Cash — Aston Villa, £4.5m**: 34 starts + 1 sub; 3.4 pts/start; 0.90 shots, 0.90 chances created, 5.57 DefCon per 90. Villa top defender (117 pts: 3 goals, 3 assists). 1st in RMT projections for GW1-6 despite low early CS odds vs Arsenal (12%).
- **Antonee Robinson — Fulham, £4.5m**: 17 starts + 5 subs; 3.5 pts/start; 0.36 shots, 1.30 chances created, 8.05 DefCon per 90. High chance creation; CS odds rise in GW7 (39% Hull H).

### Other named monitors

- **Leeds**: Bogle (£4.5m: 1G, 5A, 4 DefCon); Gudmundsson (£4.5m: 2.2 pts/start); Justin (£4.5m: 4.1 pts/start).
- **Crystal Palace**: Chadi Riad (£4.5m: Lacroix departure backup).
- **Aston Villa**: Konsa (£4.5m: low DefCon); Maatsen (£4.5m: Digne departure dependent).
- **Chelsea**: Hato (£4.5m: un-nailed left-back/CB).
- **Everton**: Mykolenko (£4.5m: 2.9 pts/start, 1A, 14 DefCon).
- **Sunderland**: Reinildo and Hume (£4.5m).
- **Tottenham**: Robertson, Udogie, Spence (£4.5m).
- **Bournemouth**: Adam Smith (£4.5m).

## Project interpretation

### Decision rules

- Gate £4.5m selection on expected starts before applying attacking or DefCon rates.
- Use early CS probabilities (Shaw 46% GW2, Mitchell 45% GW4, Kadioglu 41% GW3) to optimize GW1-6 rotation.
- Treat Kayode long throws (169 into box) as specialized set-piece assist route.

### Practical implications

- Shaw offers highest immediate CS odds (39% and 46% vs promoted teams).
- Mitchell combines highest previous total points (135) with strong CS odds (GW4/6).
- Rodon provides highest DefCon floor (18 pts) with solid GW2/5 CS odds.
- Kayode provides unique long-throw threat (169 box throws).

## Findings

### Evidence

- Shaw leads price group in opening CS probabilities (46% peak).
- Kayode leads all PL defenders in long throw-ins into the penalty box (169 throws).
- Mitchell achieved the highest overall points total (135) among £4.5m defenders.
- Rodon achieved the joint-most DefCon points (18) among £4.5m defenders.

## Decision

**Verdict**: Shortlist centers on Shaw (schedule/CS odds), Mitchell (points floor), Rodon (DefCon floor), Kayode (long throws), and Cash (RMT rank).

**Recommended action**:
- Verify preseason starter status before Gameweek 1 lock.
- Use clean-sheet probability sequences for rotation pair optimization.

**Trigger / kill switch**:
- Remove candidate if starting role or team defensive system deteriorates.

## Risks and unknowns

- DefCon and clean-sheet probability metrics rely on publisher models.
- Managerial changes at Man Utd, Palace, and Brighton create tactical shifts.
- European play-off workload for Brighton and Brentford.

## Refresh checklist

- [x] Recheck source URL using Playwright extraction.
- [x] Confirm title, author, publication date, and prices.
- [x] Transcribe 100% of statistical image tables (Post-Carrick stats, GW19+ stats, Long throws, CS odds sequences).
- [x] Omit non-data promotional images and headers.
- [x] Cross-check candidates against `expected-role-gw1-5.md` and `fpl-summer-transfers.md`.
- [x] Update `Updated`, `Data stamp`, and `Risks`.
- [x] Delete `.tmp/agent/` scratch before finishing.

