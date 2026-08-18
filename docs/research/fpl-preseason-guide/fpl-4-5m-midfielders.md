# FPL 2026/27 £4.5m Midfielders — Fantasy Football Scout Synthesis

**Updated**: 2026-08-18T15:05:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-07-24 (unchanged on 2026-08-13 recheck); accessed 2026-08-13; Playwright recheck 2026-08-18: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Source synthesis · Playwright extracted & cross-checked  
**Purpose**: Capture source-led £4.5m midfielder minutes evidence, player statistics, and enabler evaluation  
**Scope**: 25 £4.5m midfielders pool context and Coventry City detailed evaluation. Non-data promotional graphics omitted; player card graphics noted.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md) · [£4.5m defenders](fpl-4-5m-defenders.md) · [Expected role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) · [Summer transfers](fpl-summer-transfers.md)

## Sources

- **Primary**: [Best £4.5m midfielders for FPL 2026/27: All 25 assessed — FPL Marc, Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-5m-midfielders-for-fpl-2026-27-all-25-assessed) — published 2026-07-24; accessed and re-verified 2026-08-01; role: £4.5m midfielder analysis

**Source boundary**: Source claims not independently validated. Playwright rendered full-page content extracted. Price pool overview and Coventry City 3-player assessment transcribed in full. Text following Coventry heading requires free user account login; source gap noted.

## Agent Prompt

```text
Full redo docs/research/fpl-4-5m-midfielders.md

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
1. Extract £4.5m midfielder price-pool context across Premier League and promoted clubs.
2. Inspect all article `.entry-content` image assets; filter out non-data promotional graphics, ads, site logos, author gravatars, and decorative photos.
3. Transcribe Coventry City midfielder statistics table (starts, goals, assists, DefCon per 90, notes).
4. Evaluate bench-enabler requirements vs minutes risk (citing historical Andreas Pereira 2022/23 benchmark).
5. Record account gate boundary for subsequent promoted/established club sections.

**Definitions and assumptions**:
- **£4.5m pool**: 25 midfielders listed at £4.5m in FPL 2026/27 price release.
- **DefCon per 90**: Article defensive-contribution rate.
- **Promoted proportion**: 11 of 25 £4.5m midfielders belong to Coventry City, Ipswich Town, and Hull City.

**Validation boundary**: Article-only synthesis. Preseason minutes, line-ups, and transfer window additions require verification.

## Source synthesis

### Price-pool context

- 25 midfielders priced at £4.5m for FPL 2026/27.
- 11 of 25 midfielders play for promoted clubs (Coventry City, Ipswich Town, Hull City).
- Key distinction vs budget defenders: regular starting minutes are significantly harder to secure in midfield.
- Historical benchmark: Andreas Pereira (2022/23 at Fulham: 4 goals, 10 assists, 123 pts); recent seasons yield few playing £4.5m midfielders.
- Primary evaluation filter: guaranteed starting role to avoid stranded bench slots.

### Coventry City midfielder statistics (2025/26 Championship season)

| Player | Price | Starts (Sub Apps) | Goals | Assists | DefCon / 90 | Role & Tactical Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **George Shepherd** | £4.5m | 0 (0) | 0 | 0 | 0.00 | 17-year-old youth asset (*source card graphic*). Has not yet made senior debut. |
| **Raphael Borges Rodrigues** | £4.5m | 0 (2) | 0 | 1 | 12.86 | Left winger returned from Wigan loan (29 League One starts: 1 goal, 3 assists). 12.86 DefCon/90 based on tiny 35-min cameo sample. |
| **Kai Andrews** | £4.5m | 0 (7) | 0 | 0 | 4.26 | Returned from Hibernian loan (74 mins across 7 cameos; scored winner vs Celtic). |

### Source rationale

- **Coventry trio assessment**: None of Shepherd, Borges Rodrigues, or Andrews established Championship starting credentials for Coventry.
- **Transfers expectation**: Expected summer signings will further suppress their starting probability.
- **Gated boundary**: Text following Coventry header states free login required for Ipswich Town, Hull City, and remaining 14 Premier League £4.5m midfielders.

## Project interpretation

### Decision rules

- Reject all non-starting £4.5m midfielders; do not use un-nailed enablers.
- Disregard small-sample DefCon rates (e.g. 12.86 over 35 mins).
- Require verified senior starting role in preseason before adding to squad draft.

### Practical implications

- Enforces a strict minutes-first filter for £4.5m midfielders.
- Avoids dead bench slots that restrict transfer flexibility.

## Findings

### Evidence

- 11 of 25 £4.5m midfielders belong to promoted teams.
- None of the accessible Coventry £4.5m midfielders possesses senior starting history.
- Starting minutes remain the single critical gating criteria for budget midfielders.

## Decision

**Verdict**: Do not select accessible Coventry £4.5m midfielders. Require verified starting XI roles from preseason before selecting any £4.5m midfielder enabler.

**Recommended action**:
- Recheck preseason starting line-ups across all Premier League teams.

**Trigger / kill switch**:
- Only activate a £4.5m midfielder if confirmed as regular starter with stable role.

## Risks and unknowns

- Account-gated sections for Ipswich, Hull, and remaining PL clubs require account login.
- Promoted-team transfer additions will alter depth charts before GW1.

## Refresh checklist

- [x] Recheck source URL using Playwright full-page rendering.
- [x] Confirm title, author, publication date, and prices.
- [x] Transcribe Coventry midfielder statistics table and player card graphics.
- [x] Cross-check player prices, roles, and claims against expected-role-gw1-5.md and fpl-summer-transfers.md.
- [x] Omit non-data promotional banners and ads.
- [x] Update `Updated`, `Data stamp`, and `Risks`.
- [x] Delete `.tmp/agent/` scratch before finishing.
