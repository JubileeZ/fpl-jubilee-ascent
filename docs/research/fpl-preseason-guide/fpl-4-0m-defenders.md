# FPL 2026/27 £4.0m Defenders — Fantasy Football Scout Synthesis

**Updated**: 2026-08-18T15:05:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-07-24 (unchanged on 2026-08-13 recheck); accessed 2026-08-13; Playwright recheck 2026-08-18: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Source synthesis · Playwright full-page extracted · Cross-checked against expected-role & summer-transfers  
**Purpose**: Capture source-led £4.0m defender shortlist, player statistics, set-piece threat, and promoted-team minutes evidence  
**Scope**: 46 £4.0m defenders pool context and accessible Coventry City 10-player detailed evaluation. Non-data promotional graphics omitted; player card graphics noted.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md) · [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) · [Confirmed Summer Transfers](fpl-summer-transfers.md) · [£4.5m defenders](fpl-4-5m-defenders.md) · [£5.0m defenders](fpl-5-0m-defenders.md)

## Sources

- **Primary**: [Best £4.0m defenders for FPL 2026/27: All 46 assessed — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-0m-defenders-for-fpl-2026-27-all-46-assessed) — published 2026-07-24; accessed 2026-07-31; role: £4.0m defender analysis
- **Cross-reference**: [Expected Role (GW1–5)](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — updated 2026-07-31; role: starting role priors and XI contention set validation
- **Cross-reference**: [Confirmed Summer Transfers](fpl-summer-transfers.md) — register through 2026-07-30; role: confirmed transfer arrivals (e.g. Amenda £17m to COV)

**Source boundary**: Source claims not independently validated. Playwright rendered full-page content extracted. Promoted-team introductory analysis and Coventry City 10-player assessment transcribed in full. Text following Coventry heading requires free user account login; source gap noted. Cross-checked with internal models for role alignment.

## Agent Prompt

```text
Full redo docs/research/fpl-4-0m-defenders.md

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

**Method type**: Primary-source synthesis & Playwright full-page extraction

**Inputs**:
- Playwright rendered article text
- Dynamically fetched article image assets in `.entry-content`

**Procedure**:
1. Extract £4.0m defender price-pool context across Premier League and promoted clubs.
2. Inspect all article `.entry-content` image assets; filter out non-data promotional graphics, ads, site logos, author gravatars, and decorative photos.
3. Transcribe Coventry City defender statistics table (starts, goals, assists, DefCon per 90, notes).
4. Evaluate full-back assist routes, centre-half set-piece threats, and transfer-dependent replacement roles.
5. Record account gate boundary for subsequent promoted/established club sections.

**Definitions and assumptions**:
- **£4.0m pool**: 46 defenders listed at £4.0m in FPL 2026/27 price release.
- **DefCon per 90**: Article defensive-contribution rate.
- **Promoted proportion**: 26 of 46 £4.0m defenders belong to Coventry City, Hull City, and Ipswich Town.

**Validation boundary**: Article-only synthesis. Preseason friendlies, starting XI announcements, and final transfer window moves require verification.

## Source synthesis

### Price-pool context

- 46 defenders priced at £4.0m for FPL 2026/27.
- Over half (26 defenders) belong to promoted clubs: Coventry City, Hull City, and Ipswich Town.
- Historical trend: prior to 2023/24, playing £4.0m defenders were rare (e.g. Lundstram, Livramento); recent price lists provide more starters via promoted teams.

### Coventry City defender statistics (2025/26 Championship season)

| Player | Price | Starts (Sub Apps) | Goals | Assists | DefCon / 90 | Role & Tactical Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Milan van Ewijk** | £4.0m | 43 (1) | 0 | 8 | 6.42 | First-choice right-back. Only two absences enforced; final-day benching post-promotion. Created 46 chances (11 from long throws). Joint-2nd among Championship defenders for assists (8). |
| **Jay Dasilva** | £4.0m | 41 (1) | 0 | 3 | 5.12 | Regular left-back. 48 chances created (pipped van Ewijk). Left-back transfer links increase competition risk. |
| **Liam Kitching** | £4.0m | 37 (1) | 2 | 0 | 8.90 | Mainstay centre-half; dropped briefly in Jan. 46 shots (41 from set plays — top among Coventry defenders). |
| **Bobby Thomas** | £4.0m | 33 (0) | 3 | 4 | 8.56 | Main centre-half starter (*source card graphic*). 3 goals, 4 assists (3 from dead-balls), 37 shots. Set-piece goal threat (5 goals in 2024/25). Primary centre-half recommendation if no new signing arrives. |
| **Joel Latibeaudiere** | £4.0m | 15 (0) | 0 | 1 | 7.98 | Missed start through knee injury; deputised for Thomas/Kitching post-Christmas. |
| **Luke Woolfenden** | £4.0m | 11 (6) | 0 | 0 | 9.48 | 4th-choice centre-half; high DefCon rate across limited minutes. |
| **Kaine Kesler-Hayden** | £4.0m | 5 (17) | 2 | 1 | 8.60 | Right-back backup behind van Ewijk. |
| **Jake Bidwell** | £4.0m | 3 (8) | 0 | 1 | 7.84 | Veteran left-back backup behind Dasilva. |
| **Miguel Brau** | £4.0m | 1 (8) | 0 | 0 | 5.97 | Limited impact; 4-month injury absence. |
| **Aurele Amenda** | £4.0m | — | — | — | 8.97 | New signing from Eintracht Frankfurt. Bundesliga sample: 8.97 DefCon/90 (10-action threshold in 7 of 18 starts). Potential Kitching replacement starter. |

### Source rationale

- **van Ewijk**: Top £4.0m full-back pick due to secure starting role (43 starts), chance creation (46), long-throw duty, and 8 assists.
- **Thomas**: Top £4.0m set-piece centre-half pick (3 goals, 4 assists, 37 shots).
- **Amenda**: High-floor Bundesliga DefCon rate (8.97), but requires preseason starting confirmation.
- **Gated boundary**: Text following Coventry header states free login required for Hull City, Ipswich Town, and remaining 20 Premier League £4.0m defenders.

## Project interpretation

### Decision rules

- Prioritize van Ewijk as primary £4.0m defender watchlist candidate (validated as Coventry Regular Starter in `expected-role-gw1-5.md`).
- Select Thomas if set-piece goal threat is prioritized over full-back assist route (validated as Coventry Regular Starter in `expected-role-gw1-5.md`).
- Monitor Amenda (£17m transfer from Eintracht Frankfurt confirmed in `fpl-summer-transfers.md`) for preseason starting role confirmation (classified as Coventry Regular Starter in `expected-role-gw1-5.md`).
- Note demotion of Kitching and Dasilva to Rotation in `expected-role-gw1-5.md` due to new signings/competition risk, perfectly aligning with FFS source notes.
- Gate all £4.0m selections on verified starting XI roles.

### Practical implications

- van Ewijk provides the strongest combined starting probability and assist potential.
- Thomas provides dead-ball and set-piece aerial threat (37 shots).
- Amenda provides high-floor DefCon rating (8.97 per 90) but requires monitoring as a new summer arrival.
- £4.0m enablers must start regularly to avoid bench dead weight.

## Findings

### Evidence

- 26 of 46 £4.0m defenders play for promoted teams.
- van Ewijk logged 43 starts, 46 chances created, and 8 assists for Coventry.
- Thomas recorded 37 shots, 3 goals, and 4 assists from central defence.
- Amenda averaged 8.97 DefCon per 90 in the Bundesliga and joined Coventry for £17m.
- Cross-checking against `expected-role-gw1-5.md` confirms Coventry's Draft Shortlist contains van Ewijk, Thomas, and Amenda as Regular Starters with 0 Nailed Starters.

## Decision

**Verdict**: van Ewijk is top £4.0m full-back pick; Thomas is top £4.0m set-piece centre-back pick. Confirm starting roles in preseason.

**Recommended action**:
- Monitor Coventry preseason line-ups and transfer arrivals.
- Cross-check starting XI lineups prior to GW1 lock.

**Trigger / kill switch**:
- Drop candidate if starting role is lost to new summer signing.

## Risks and unknowns

- Championship assist and goal rates may regress in Premier League.
- Account-gated sections for Hull, Ipswich, and established PL clubs require account login.
- Preseason friendly starter composition may alter final GW1 minutes expectations.

## Refresh checklist

- [x] Recheck source URL using Playwright full-page rendering / metadata.
- [x] Confirm title, author, publication date, and prices.
- [x] Transcribe full Coventry defender statistics table and player card graphics.
- [x] Omit non-data promotional banners and ads.
- [x] Cross-check player prices, stats, roles, and claims against `expected-role-gw1-5.md` and `fpl-summer-transfers.md`.
- [x] Ensure compliance with research standards in `docs/research/INDEX.md`.
- [x] Update `Updated`, `Data stamp`, and `Risks`.
- [x] Delete `.tmp/agent/` scratch before finishing.
