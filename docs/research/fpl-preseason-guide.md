# FPL 2026/27 Pre-Season Guide — Source Directory

**Updated**: 2026-07-31T07:16:30+07:00  
**Data stamp**: Fantasy Football Scout guide capture reviewed 2026-07-31; child notes refreshed 2026-07-31  
**Season**: 2026/27  
**Status**: Source directory · 6 child notes active & refreshed  
**Purpose**: Index decision-relevant pre-season source notes  
**Scope**: Budget goalkeepers, £5.0m defenders, £4.5m defenders, £4.0m defenders, £4.5m midfielders, and confirmed summer transfers. Guide-only index content; no full transcription of unrelated sections.  
**Related**: [Budget goalkeepers](fpl-budget-goalkeepers.md) · [£5.0m defenders](fpl-5-0m-defenders.md) · [£4.5m defenders](fpl-4-5m-defenders.md) · [£4.0m defenders](fpl-4-0m-defenders.md) · [£4.5m midfielders](fpl-4-5m-midfielders.md) · [Summer transfers](fpl-summer-transfers.md)

> Guide is a dynamic directory. Child notes preserve dated source synthesis; article claims remain unvalidated.

## Sources

- **Primary**: [FPL 2026/27: The ultimate pre-season guide, tips + more — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-the-ultimate-pre-season-guide-tips-more) — initial publication date not exposed in capture; accessed 2026-07-31; role: pre-season content directory
- **Supporting primary**: [Best £4.0m-£4.5m goalkeepers for FPL 2026/27](https://www.fantasyfootballscout.co.uk/2026/07/28/best-4-0m-4-5m-goalkeepers-for-fpl-2026-27) — published 2026-07-28; accessed 2026-07-31; role: budget goalkeeper analysis & extracted image stats
- **Supporting primary**: [Best £5.0m defenders for FPL 2026/27](https://www.fantasyfootballscout.co.uk/2026/07/30/best-5-0m-defenders-for-fpl-2026-27) — published 2026-07-30; accessed 2026-07-31; role: £5.0m defender analysis & extracted image stats
- **Supporting primary**: [Best £4.5m defenders for FPL 2026/27](https://www.fantasyfootballscout.co.uk/2026/07/29/best-4-5m-defenders-for-fpl-2026-27) — published 2026-07-29; accessed 2026-07-31; role: £4.5m defender analysis & extracted image stats
- **Supporting primary**: [Best £4.0m defenders for FPL 2026/27: All 46 assessed](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-0m-defenders-for-fpl-2026-27-all-46-assessed) — published 2026-07-24; accessed 2026-07-31; role: £4.0m defender analysis
- **Supporting primary**: [Best £4.5m midfielders for FPL 2026/27: All 25 assessed](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-5m-midfielders-for-fpl-2026-27-all-25-assessed) — published 2026-07-24; accessed 2026-07-31; role: £4.5m midfielder analysis
- **Supporting primary**: [FPL 2026/27 transfer news: Confirmed summer signings](https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings) — page date not exposed; register current through 2026-07-30; accessed 2026-07-31; role: transfer register

**Source boundary**: Guide and child-page claims not independently validated. No FPL API refresh, fixture recalculation, projection run, or lineup verification performed.

## Agent Prompt

```text
Full redo docs/research/fpl-preseason-guide.md

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

**Method type**: Source synthesis / directory mapping

**Inputs**:
- Fantasy Football Scout guide capture
- Six linked child-note source pages
- Stable child-note files in `docs/research/`

**Procedure**:
1. Identify guide headings containing requested decision topics under **BEST FPL PLAYERS FOR 2026/27**.
2. Map each heading to one stable child note and one source URL.
3. Automatically generate dedicated research notes for newly published primary articles (e.g. `fpl-5-0m-defenders.md`).
4. Inspect all article `.entry-content` image assets; filter out non-data promotional graphics, ads, site logos, author gravatars, and decorative photos.
5. Record source availability and metadata limits.
6. Avoid transcribing unrelated guide sections, ads, comments, or decorative content.

**Definitions and assumptions**:
- **Directory note**: Navigation and scope map; not substitute for child-page evidence.
- **Source-led**: Reported by Fantasy Football Scout; not project-validated.

**Validation boundary**: Descriptive source mapping only. Guide links and linked-page content can change before operational use.

## Source synthesis

### Relevant guide sections

- **BEST FPL PLAYERS FOR 2026/27**: links to [budget goalkeepers](fpl-budget-goalkeepers.md), [£5.0m defenders](fpl-5-0m-defenders.md), [£4.5m defenders](fpl-4-5m-defenders.md), [£4.0m defenders](fpl-4-0m-defenders.md), and [£4.5m midfielders](fpl-4-5m-midfielders.md).
- **SUMMER TRANSFERS**: links to [confirmed summer transfers](fpl-summer-transfers.md).
- Pre-season directory collated and regularly refreshed through Gameweek 1.
- **CLUB BY CLUB** contains additional team, friendly, and transfer links; excluded from core scope.

### Source rationale

- Functions as publisher-maintained index for price-list analysis and transfer coverage.
- Child pages provide decision-relevant player prices, roles, minutes evidence, statistics, rankings, and transfer context.

## Project interpretation

### Decision rules

- Use guide links to locate child-note sources; do not treat guide presence as player endorsement.
- Ensure every primary article listed under **BEST FPL PLAYERS FOR 2026/27** has a dedicated research note created via Playwright full-page and statistical image extraction.
- Recheck guide and child pages before preseason squad or model decisions.

### Practical implications

- Directory reduces source-discovery cost while preserving separate evidence notes.
- Dynamic guide requires link and freshness checks near deadline.

## Findings

### Evidence

- Guide exposes six decision sections: budget goalkeepers, £5.0m defenders, £4.5m defenders, £4.0m defenders, £4.5m midfielders, and summer-transfer register.

### Alternatives

- **Direct-page workflow**: read each source URL directly.
- **Guide-led workflow**: use guide as index, then child notes for evidence.

## Decision

**Verdict**: Use guide as navigation layer; maintain six dedicated child notes as dated source-synthesis records.

**Recommended action**:
- Start topic review from linked child note.
- Monitor guide for new position/price articles published prior to GW1.

**Trigger / kill switch**:
- Create a new research note whenever a new primary article is published under **BEST FPL PLAYERS FOR 2026/27**.

## Risks and unknowns

- Guide publication date not exposed in capture.
- Preseason player roles remain subject to friendly usage and deadline transfer moves.

## Refresh checklist

- [x] Re-read guide and confirm six requested links.
- [x] Recheck child-note source URLs, publication dates, and access dates.
- [x] Create dedicated research note for newly added primary articles (`fpl-5-0m-defenders.md`).
- [x] Update directory scope and child-page links.
- [x] Update `Updated`, `Data stamp`, `Related`, and `Risks`.
- [x] Delete `.tmp/agent/` scratch before finishing.
