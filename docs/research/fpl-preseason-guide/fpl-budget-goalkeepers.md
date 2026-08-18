# FPL 2026/27 Budget Goalkeepers — Fantasy Football Scout Synthesis

**Updated**: 2026-08-18T15:05:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-07-28 (unchanged on 2026-08-13 recheck); accessed 2026-08-13; Playwright recheck 2026-08-18: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Active · audited & cross-checked  
**Purpose**: Capture source-led £4.0m–£4.5m goalkeeper shortlist, extracted defensive stats tables, role cross-checks, and minutes risks  
**Scope**: Player prices, role evidence, extracted image data tables, fixture/ranking signals, £4.0m backup routes, and cross-checks against project role/transfer models. No independent fixture or projection validation.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md) · [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) · [Summer transfers](fpl-summer-transfers.md)

## Sources

- **Primary**: [Best £4.0m-£4.5m goalkeepers for FPL 2026/27 — FPL Marc, Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/28/best-4-0m-4-5m-goalkeepers-for-fpl-2026-27) — published 2026-07-28; last modified 2026-07-28; accessed 2026-08-13; role: budget goalkeeper analysis and image stats extraction
- **Cross-check**: [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — updated 2026-07-31; role: pre-season expected roles, starter status, and draft availability audit
- **Cross-check**: [Summer transfers](fpl-summer-transfers.md) — updated 2026-07-31; role: confirmed transfer register (Dubravka, Scherpen, Van Oevelen, Butland, Senesi)

**Source boundary**: Source claims not independently validated. Non-data promotional graphics, ads, site logos, and editorial celebration images omitted; article statistical image tables and fixture ticker graphics transcribed directly.

## Agent Prompt

```text
Full redo docs/research/fpl-budget-goalkeepers.md

1. Re-read source URL using Playwright / HTTP fetch; verify title, author, publication/update date (published 2026-07-28, modified 2026-07-28, accessed 2026-08-03).
2. Cross-check prices, roles, stats, and claims against docs/research/expected-role-gw1-5.md and docs/research/fpl-summer-transfers.md.
3. Extract 100% of statistical data images into Markdown tables.
4. Keep Source synthesis strictly separate from Project interpretation.
5. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
6. Run pre-commit gate checks (uv run ruff check ., uv run pytest, bash tests/verify.sh); delete .tmp/agent/ scratch files before finishing.
```

## Method

**Method type**: Primary-source synthesis, image data extraction & multi-source cross-check

**Inputs**:
- Article text and rendered image assets (`.entry-content`) from FFS primary source
- `docs/research/expected-role-gw1-5.md` Expected Role model & Draft Availability overlay
- `docs/research/fpl-summer-transfers.md` confirmed transfer register

**Procedure**:
1. Extract featured £4.5m goalkeeper candidates and promoted-team alternatives from article text.
2. Inspect all article `.entry-content` image assets; filter out non-data promotional graphics, ads, site logos, author gravatars, and decorative photos.
3. Inspect and transcribe all data-bearing statistical graphics (team overall defensive stats, home defensive stats, and fixture ticker sequences) into Markdown tables.
4. Cross-check player starter roles and draft availability against `expected-role-gw1-5.md`.
5. Cross-check confirmed transfers against `fpl-summer-transfers.md`.
6. Record £4.0m understudy routes and uncertainty.
7. Translate source claims into conditional project monitoring rules.

**Definitions and assumptions**:
- **PPMPM**: article shorthand for points per million per match.
- **Source ranking**: RMT or Fixture Ticker result reported by article; not project ranking.
- **Backup**: £4.0m goalkeeper described as one injury or suspension away from starting.

**Validation boundary**: Article synthesis and cross-check overlay. Prices, transfers, lineups, fixture ratings, and projections subject to change before Gameweek 1.

## Source synthesis

### Extracted image statistics tables

#### Overall defensive statistics (2025/26 season)
*Source graphic: Overall defensive metrics (sorted by Goals Conceded ascending)*

| Team | Goals Conceded | Clean Sheets | Goal Attempts Conceded | Shots On Target Conceded | Big Chances Conceded | xG Conceded |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ARS** | 27 | 19 | 314 | 87 | 50 | 28.30 |
| **MCI** | 35 | 16 | 372 | 124 | 76 | 44.20 |
| **BHA** | 46 | 10 | 443 | 142 | 77 | 49.13 |
| **SUN** | 48 | 11 | 544 | 164 | 80 | 54.45 |
| **AVL** | 49 | 9 | 493 | 160 | 90 | 53.87 |
| **MUN** | 50 | 8 | 444 | 138 | 72 | 48.57 |
| **EVE** | 50 | 11 | 534 | 149 | 93 | 56.51 |

#### Home defensive statistics (2025/26 season)
*Source graphic: Home defensive metrics (sorted by Big Chances Conceded ascending)*

| Team | Goals Conceded | Clean Sheets | Goal Attempts Conceded | Shots On Target Conceded | Big Chances Conceded | xG Conceded |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **BOU** | 20 | 6 | 177 | 58 | 20 | 16.55 |
| **ARS** | 11 | 11 | 136 | 35 | 23 | 12.38 |
| **LEE** | 21 | 6 | 210 | 65 | 32 | 22.29 |
| **BHA** | 20 | 5 | 188 | 68 | 33 | 21.34 |
| **MUN** | 24 | 4 | 197 | 65 | 33 | 20.82 |
| **LIV** | 20 | 5 | 211 | 68 | 34 | 22.19 |

#### Extracted opening fixture ticker graphics (GW1–GW6)

- **Tottenham (Kinsky)** (*source fixture graphic*):
  - GW1: bre (A) · GW2: NEW (H) · GW3: nfo (A) · GW4: EVE (H) · GW5: AVL (H) · GW6: mun (A)
- **Bournemouth (Petrovic)** (*source fixture graphic*):
  - GW1: mci (A) · GW2: EVE (H) · GW3: new (A) · GW4: BRE (H) · GW5: LIV (H) · GW6: che (A)
- **Fulham (Leno)** (*source fixture graphic*):
  - GW1: CHE (H) · GW2: sun (A) · GW3: CRY (H) · GW4: liv (A) · GW5: MUN (H) · GW6: ips (A)

### £4.5m candidates

- **Bart Verbruggen — Brighton (£4.5m)**: cited as best-value £4.5m goalkeeper. Brighton produced five clean sheets in final 10 matches; from GW28, conceded league-low 18 big chances. Verbruggen save rate on target: 74.6% (2nd best). Brighton overall: 46 goals conceded (3rd fewest), 142 shots on target (4th fewest), 49.13 xGC (5th lowest). RMT projects him top scorer at £4.5m for GW1–6 (early opponents: Leeds, Coventry).  
  *Cross-check (`expected-role-gw1-5.md`)*: Nailed Starter (`p_start=0.90`), `draft_availability=eligible`. Highest project alignment.
- **Antonin Kinsky — Tottenham (£4.5m)**: potential starter if Guglielmo Vicario leaves. Early spell included three wins, clean sheets in four matches. Replaced Vicario (hernia) late in season after early Champions League errors vs Atletico. No promoted opponent until GW7 reduces early schedule rating.  
  *Cross-check (`expected-role-gw1-5.md` & `fpl-summer-transfers.md`)*: Role demoted from Nailed to Regular Starter (`p_start=0.75`) in project model following pre-season friendlies where Brandon Austin and Martin Dubravka started later matches (Sydney XI). Dubravka joined Spurs on free transfer (confirmed in transfer register).
- **Djordje Petrovic — Bournemouth (£4.5m)**: 2nd among £4.5m options by PPMPM. Bournemouth 18-match unbeaten run. Home defence ranked 2nd for xGC (16.55) and 1st for fewest big chances conceded (20). GW24–30 overperformance: 3 goals conceded vs 11.41 xGC; 109 saves overall (joint 3rd most). European fixtures, Senesi departure, Iraola departure, and 2nd worst opening-six Fixture Ticker rank are main risks; no promoted opponent until GW10.  
  *Cross-check (`expected-role-gw1-5.md` & `fpl-summer-transfers.md`)*: Nailed Starter (`p_start=0.90`), `draft_availability=eligible`. Senesi transfer to Spurs confirmed in transfer register (free transfer); Iraola departure increases defensive structure uncertainty.
- **Bernd Leno — Fulham (£4.5m)**: 145 shots on target conceded (5th fewest), but 96 big chances conceded (3rd most). Manager Alvaro Arbeloa appointed; Silva, Jimenez, Wilson departed. Difficult first five fixtures: CHE (H), sun (A), CRY (H), liv (A), MUN (H), followed by ips (A), Hull (H), Coventry (A).  
  *Cross-check (`expected-role-gw1-5.md`)*: Nailed Starter (`p_start=0.90`), `draft_availability=eligible`. Tough GW1–5 schedule limits early appeal.

### Promoted-team goalkeepers

- **Coventry**: FPL lists Ben Wilson at £4.5m, but loan goalkeeper **Carl Rushworth — £4.5m** started all 46 league matches. Coventry conceded division-fewest 45 goals. Permanent deal pending; opening-six Ticker rank poor.  
  *Cross-check (`expected-role-gw1-5.md` & `fpl-summer-transfers.md`)*: Ben Wilson is Regular Starter (`p_start=0.75`); no Nailed Starter for Coventry. Rushworth move not confirmed in summer-transfers register.
- **Ipswich**: **Christian Walton — £4.5m** replaced by **Kayne van Oevelen — £4.5m** and **Kjell Scherpen — £4.5m**. Ipswich kept 15 clean sheets in final 32 matches (17 total), ranked 2nd for xGC (46.60). Fixture rank: 4th through GW6.  
  *Cross-check (`expected-role-gw1-5.md` & `fpl-summer-transfers.md`)*: Scherpen (£8.5m on 29 Jul) and Van Oevelen (£3.4m on 20 Jul) transfers confirmed. Both classified as Rotation (`p_start=0.40`) due to split pre-season minutes; Ipswich has no Nailed Starter.
- **Hull**: **Jack Butland — £4.5m** replaces Ivor Pandur (moved to Rangers); Konstantinos Tzolakis also reported target. Hull conceded 66 goals, 80.10 xGC (2nd most in Championship).  
  *Cross-check (`expected-role-gw1-5.md` & `fpl-summer-transfers.md`)*: Butland transfer from Rangers (£3m on 1 Jul) confirmed. Classified as Regular Starter (`p_start=0.75`).

### £4.0m routes

- Four minimum-priced understudies identified: **Fraser Forster** (Bournemouth), **Jason Steele** (Brighton), **Benjamin Lecomte** (Fulham), and **Martin Dubravka** (Tottenham).
- Understudies to Petrovic, Verbruggen, Leno, and Kinsky.
- Doubling starter + backup recommended if squad budget requires £4.0m cover; Dubravka potential challenger to Kinsky.  
  *Cross-check (`expected-role-gw1-5.md`)*: All four listed as backup/rotation GKs in respective club depth notes. Dubravka addition to Spurs creates active starter competition for Kinsky.

## Project interpretation

### Decision rules

- Require confirmed starter status before selecting £4.5m goalkeeper for GW1.
- Cross-check primary source claims against project Expected Role model (`expected-role-gw1-5.md`) and transfer register (`fpl-summer-transfers.md`).
- Treat RMT first-six rankings as hypotheses requiring minutes, fixture, and transfer checks.
- Use £4.0m backups only when starter and succession path are clear.
- Reassess promoted-team goalkeepers after pre-season lineups and transfer window close.

### Practical implications

- **Verbruggen (Brighton)**: Strongest source-led and project-verified £4.5m pick (Nailed Starter, `p_start=0.90`, `draft_availability=eligible`, late defensive stats 46 GC / 49.13 xGC, favourable early schedule).
- **Kinsky (Spurs)**: High role risk. Demoted from Nailed to Regular Starter (`p_start=0.75`) in project model due to Dubravka free transfer and pre-season friendly rotation (Austin/Dubravka starting Sydney XI).
- **Petrovic (Bournemouth)**: Solid fit-role (Nailed Starter, `p_start=0.90`, `draft_availability=eligible`) and elite home stats (20 GC, 20 BCC, 16.55 xGC), but Senesi transfer to Spurs, Iraola exit, and tough opening schedule increase volatility.
- **Leno (Fulham)**: Nailed Starter (`p_start=0.90`), but difficult opening fixture run (CHE, sun, CRY, liv, MUN) caps early value.
- **Promoted Goalkeepers**: Ipswich (Scherpen/Van Oevelen) and Coventry (Wilson/Rushworth) carry selection split risk (Rotation / Regular, no Nailed Starter); Butland (Hull) confirmed Regular Starter but weak underlying team stats.

## Findings

### Evidence

- Source £4.5m shortlist: Verbruggen, Kinsky, Petrovic, Leno.
- Image stats confirm Brighton's strong overall metrics (46 GC, 49.13 xGC) and Bournemouth's elite home metrics (20 BCC, 16.55 xGC).
- Cross-checks with `expected-role-gw1-5.md` and `fpl-summer-transfers.md` confirm:
  - Verbruggen: Nailed Starter (`p_start=0.90`), `draft_availability=eligible`.
  - Kinsky: Regular Starter (`p_start=0.75`), friendly rotation risk with Austin & newly signed Dubravka.
  - Petrovic: Nailed Starter (`p_start=0.90`), `draft_availability=eligible`; Senesi moved to Spurs.
  - Leno: Nailed Starter (`p_start=0.90`), `draft_availability=eligible`.
  - Promoted GKs: Scherpen & Van Oevelen transferred to Ipswich (Rotation `p_start=0.40`); Butland transferred to Hull (Regular `p_start=0.75`); Wilson at Coventry (Regular `p_start=0.75`).
- No starting £4.0m goalkeeper identified; four specific backups noted.

### Alternatives

- **Brighton pairing**: Verbruggen + Steele; supported by late defensive trend.
- **Tottenham pairing**: Kinsky + Dubravka; elevated role competition risk.
- **Single £4.5m starter**: saves squad slot, no immediate backup.

## Decision

**Verdict**: Source-led opening shortlist strongly favors Verbruggen as top £4.5m selection. Kinsky role demoted to Regular Starter due to Dubravka addition and friendly rotation. Petrovic and Leno viable but constrained by schedule/structural changes. Promoted options lack Nailed status.

**Recommended action**:
- Prioritize Verbruggen among £4.5m goalkeepers for GW1–5 draft builds.
- Monitor pre-season lineups and final friendlies for Tottenham (Kinsky vs Dubravka vs Austin) and Ipswich/Coventry starter announcements.
- Use extracted image tables as benchmark comparison inputs for model validation.

**Trigger / kill switch**:
- Remove candidate if starter status or expected minutes deteriorate.
- Re-rank if projections, fixtures, or squad depth change before GW1.

## Risks and unknowns

- Primary source article published 2026-07-28; relies on prior-season stats and proprietary RMT/Fixture Ticker rankings.
- Kinsky role competition from Dubravka and Austin.
- Promoted-team starter uncertainty (Ipswich Scherpen vs Van Oevelen vs Walton; Coventry Wilson vs Rushworth).
- Bournemouth European schedule, new manager (Rose), and loss of Senesi.
- £4.0m backup usage contingent on starter injury/suspension.

## Refresh checklist

- [x] Primary source URL checked; title, author, publication date (2026-07-28), and modified date (2026-07-28) verified.
- [x] Transcribed statistical tables from article image graphics verified.
- [x] Cross-checked prices, roles, and starter status against `expected-role-gw1-5.md`.
- [x] Cross-checked confirmed transfers against `fpl-summer-transfers.md`.
- [x] Updated `Updated` ISO timestamp (2026-08-01T15:52:00+07:00) and `Data stamp`.
- [x] Kept article claims strictly separate from project interpretation.
- [x] Cleaned up temporary files/scratch.

