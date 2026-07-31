# FPL 2026/27 Budget Goalkeepers — Fantasy Football Scout Synthesis

**Updated**: 2026-07-31T07:16:30+07:00  
**Data stamp**: Fantasy Football Scout article published 2026-07-28; image stats and text extracted 2026-07-31  
**Season**: 2026/27  
**Status**: Source synthesis · image stats extracted  
**Purpose**: Capture source-led £4.0m–£4.5m goalkeeper shortlist, defensive stats tables extracted from article graphics, and minutes risks  
**Scope**: Player prices, role evidence, extracted image data tables, fixture/ranking signals, and £4.0m backup routes. No independent fixture or projection validation.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md)

## Sources

- **Primary**: [Best £4.0m-£4.5m goalkeepers for FPL 2026/27 — FPL Marc, Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/28/best-4-0m-4-5m-goalkeepers-for-fpl-2026-27) — published 2026-07-28; accessed 2026-07-31; role: budget goalkeeper analysis and image stats extraction

**Source boundary**: Source claims not independently validated. Non-data promotional graphics, ads, site logos, and editorial celebration images omitted; article statistical image tables and fixture ticker graphics transcribed directly.

## Agent Prompt

```text
Full redo docs/research/fpl-budget-goalkeepers.md

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
1. Extract featured £4.5m goalkeeper candidates and promoted-team alternatives from article text.
2. Inspect all article `.entry-content` image assets; filter out non-data promotional graphics, ads, site logos, author gravatars, and decorative photos.
3. Inspect and transcribe all data-bearing statistical graphics (team overall defensive stats, home defensive stats, and fixture ticker sequences) into Markdown tables.
4. Record £4.0m understudy routes and uncertainty.
5. Translate source claims into conditional project monitoring rules.

**Definitions and assumptions**:
- **PPMPM**: article shorthand for points per million per match.
- **Source ranking**: RMT or Fixture Ticker result reported by article; not project ranking.
- **Backup**: £4.0m goalkeeper described as one injury or suspension away from starting.

**Validation boundary**: Article-only synthesis and image extraction. Prices, transfers, lineups, fixture ratings, and projections subject to change before Gameweek 1.

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

- **Bart Verbruggen — Brighton**: cited as best-value £4.5m goalkeeper. Brighton produced five clean sheets in final 10 matches; from GW28, conceded league-low 18 big chances. Verbruggen save rate on target: 74.6% (2nd best). Brighton overall: 46 goals conceded (3rd fewest), 142 shots on target (4th fewest), 49.13 xGC (5th lowest). RMT projects him top scorer at £4.5m for GW1–6 (early opponents: Leeds, Coventry).
- **Antonin Kinsky — Tottenham**: potential starter if Guglielmo Vicario leaves. Early spell included three wins, clean sheets in four matches. Replaced Vicario (hernia) late in season after early Champions League errors vs Atletico. No promoted opponent until GW7 reduces early schedule rating.
- **Djordje Petrovic — Bournemouth**: 2nd among £4.5m options by PPMPM. Bournemouth 18-match unbeaten run. Home defence ranked 2nd for xGC (16.55) and 1st for fewest big chances conceded (20). GW24–30 overperformance: 3 goals conceded vs 11.41 xGC; 109 saves overall (joint 3rd most). European fixtures, Senesi departure, Iraola departure, and 2nd worst opening-six Fixture Ticker rank are main risks; no promoted opponent until GW10.
- **Bernd Leno — Fulham**: 145 shots on target conceded (5th fewest), but 96 big chances conceded (3rd most). Manager Alvaro Arbeloa appointed; Silva, Jimenez, Wilson departed. Difficult first five fixtures: CHE (H), sun (A), CRY (H), liv (A), MUN (H), followed by ips (A), Hull (H), Coventry (A).

### Promoted-team goalkeepers

- **Coventry**: FPL lists Ben Wilson at £4.5m, but loan goalkeeper **Carl Rushworth — £4.5m** started all 46 league matches. Coventry conceded division-fewest 45 goals. Permanent deal pending; opening-six Ticker rank poor.
- **Ipswich**: **Christian Walton — £4.5m** replaced by **Kayne van Oevelen — £4.5m** and **Kjell Scherpen — £4.5m**. Ipswich kept 15 clean sheets in final 32 matches (17 total), ranked 2nd for xGC (46.60). Fixture rank: 4th through GW6.
- **Hull**: **Jack Butland — £4.5m** replaces Ivor Pandur (moved to Rangers); Konstantinos Tzolakis also reported target. Hull conceded 66 goals, 80.10 xGC (2nd most in Championship).

### £4.0m routes

- Four minimum-priced understudies identified: **Fraser Forster** (Bournemouth), **Jason Steele** (Brighton), **Benjamin Lecomte** (Fulham), and **Martin Dubravka** (Tottenham).
- Understudies to Petrovic, Verbruggen, Leno, and Kinsky.
- Doubling starter + backup recommended if squad budget requires £4.0m cover; Dubravka potential challenger to Kinsky.

## Project interpretation

### Decision rules

- Require confirmed starter status before selecting £4.5m goalkeeper for GW1.
- Treat RMT first-six rankings as hypotheses requiring minutes, fixture, and transfer checks.
- Use £4.0m backups only when starter and succession path are clear.
- Reassess promoted-team goalkeepers after preseason lineups and transfer window close.

### Practical implications

- Verbruggen shows strongest source-led blend of price, late defensive stats (46 GC, 10 CS, 49.13 xGC), and early schedule.
- Kinsky, Rushworth, van Oevelen, Scherpen, and Butland carry selection/transfer uncertainty.
- Petrovic has strong home stats (20 GC, 20 BCC, 16.55 xGC) but top schedule and managerial changes.
- £4.0m backup provides transfer insurance only if succession path is reliable.

## Findings

### Evidence

- Source £4.5m shortlist: Verbruggen, Kinsky, Petrovic, Leno.
- Image stats confirm Brighton's strong overall metrics (46 GC, 49.13 xGC) and Bournemouth's elite home metrics (20 BCC, 16.55 xGC).
- Promoted-team depth charts unsettled at Coventry, Ipswich, Hull.
- No starting £4.0m goalkeeper identified; four specific backups noted.

### Alternatives

- **Brighton pairing**: Verbruggen + Steele; supported by late defensive trend.
- **Tottenham pairing**: Kinsky + Dubravka; higher role uncertainty.
- **Single £4.5m starter**: saves squad slot, no immediate backup.

## Decision

**Verdict**: Source-led opening shortlist favors Verbruggen, with Kinsky, Petrovic, Leno, and promoted options conditional on role confirmation and extracted defensive/fixture stats.

**Recommended action**:
- Monitor preseason lineups, transfer movements, and starter announcements.
- Use extracted image tables as benchmark comparison inputs for model validation.

**Trigger / kill switch**:
- Remove candidate if starter status or expected minutes deteriorate.
- Re-rank if projections, fixtures, or squad depth change.

## Risks and unknowns

- Article relies on prior-season stats and proprietary RMT/Fixture Ticker rankings.
- Kinsky, Rushworth, van Oevelen, Scherpen, Butland role uncertainty.
- Bournemouth European schedule, new manager (Marco Rose), and loss of Senesi.
- £4.0m backup usage contingent on injury/suspension.
- Ad images, logos, and non-relevant graphics omitted.

## Refresh checklist

- [x] Recheck source title, author, publication date, and access date.
- [x] Extract and transcribe statistical tables from article image graphics.
- [x] Confirm all goalkeeper prices and club depth charts.
- [x] Recheck RMT and Fixture Ticker claims.
- [x] Keep article claims labeled as unvalidated.
- [x] Update `Updated`, `Data stamp`, and `Risks`.
- [x] Delete `.tmp/agent/` scratch before finishing.
