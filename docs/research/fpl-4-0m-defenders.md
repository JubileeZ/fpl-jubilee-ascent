# FPL 2026/27 £4.0m Defenders — Partial Fantasy Football Scout Synthesis

**Updated**: 2026-07-31T06:45:00+07:00  
**Data stamp**: Fantasy Football Scout article published 2026-07-24; accessible intro and Coventry section reviewed 2026-07-31  
**Season**: 2026/27  
**Status**: Partial source synthesis · not independently validated  
**Purpose**: Capture accessible £4.0m defender evidence while preserving article access gap  
**Scope**: Accessible article introduction and Coventry City section only. Hull City, Ipswich Town, and remaining-player sections were not transcribed because page content stopped at an account gate.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md)

> Source gap: fetched page states that the remainder is free to read but requires a Fantasy Football Scout user account. No account-authenticated capture was supplied; inaccessible sections are not inferred.

## Sources

- **Primary**: [Best £4.0m defenders for FPL 2026/27: All 46 assessed — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-0m-defenders-for-fpl-2026-27-all-46-assessed) — published 2026-07-24; accessed 2026-07-31; role: £4.0m defender analysis

**Source boundary**: Source claims not independently validated. Only intro and Coventry content accessible in fetched page text; no claims made about inaccessible Hull, Ipswich, or other sections.

## Agent Prompt

```text
Full redo docs/research/fpl-4-0m-defenders.md

1. Re-read https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-0m-defenders-for-fpl-2026-27-all-46-assessed.
2. Confirm title, publication date, accessible sections, prices, roles, and quoted statistics.
3. Check whether account-gated Hull, Ipswich, and remaining sections are available.
4. Do not infer or fill inaccessible player analysis.
5. Keep Source synthesis separate from Project interpretation.
6. Update Updated, Data stamp, Sources, Findings, Decision, and Risks.
7. Keep filename stable; delete .tmp/agent/ scratch before finishing.
```

## Method

**Method type**: Partial primary-source synthesis

**Inputs**:
- Directly fetched Fantasy Football Scout page text
- Accessible article introduction and Coventry City table/discussion

**Procedure**:
1. Record article scope and promoted-team concentration.
2. Extract Coventry player prices, starts, returns, DefCon, and role notes.
3. Mark account-gated sections as unavailable.
4. Translate accessible claims into conditional monitoring rules only.

**Definitions and assumptions**:
- **£4.0m pool**: Article states 46 defenders at this FPL price.
- **DefCon**: Article’s defensive-contribution measure.
- **Accessible evidence**: Text returned before the article’s account gate; not a complete article review.

**Validation boundary**: Partial article-only synthesis. No FPL API, official transfer check, fixture recalculation, or model validation performed.

## Source synthesis

### Accessible article scope

- Article states that 46 defenders are priced at £4.0m, with 26 from promoted Coventry City, Hull City, and Ipswich Town.
- Article frames recent £4.0m availability as easier than before 2023/24, especially among promoted clubs.
- Full article text becomes account-gated at the start of the Hull City section. Hull, Ipswich, and the remaining 2026/27 player assessments are therefore source gaps.

### Coventry City

- **Milan van Ewijk — £4.0m**: 43 starts plus one substitute appearance; 0 goals, eight assists, 6.42 DefCon per 90. Source describes him as first-choice right-back, with only two enforced absences and one final-day benching after promotion was secured. He created 46 chances, including 11 from long throws, and ranked joint-second among Championship defenders for assists. Source compares him with the prior season’s budget full-back profile: assist upside but limited DefCon.
- **Jay Dasilva — £4.0m**: 41 starts plus one substitute appearance; 0 goals, three assists, 5.12 DefCon per 90. Regular left-back, with three absences after a red card and final-day rotation. Created 48 chances, five more than van Ewijk, but Coventry’s links with other left-backs make his minutes less secure.
- **Liam Kitching — £4.0m**: 37 starts plus one substitute appearance; two goals, no assists, 8.90 DefCon per 90. Mainstay centre-half for much of the season, but dropped to the bench in January after a run without clean sheets and returned six matches later. Recorded 46 shots, 41 from set plays.
- **Bobby Thomas — £4.0m**: 33 starts; three goals, four assists, 8.56 DefCon per 90. Other half of the source-described centre-back partnership. Dropped briefly in January, then returned the next match; recurring calf issues and illness interrupted his season. Scored three set-piece goals, with three of four assists also from dead balls, and recorded 37 shots. Article presents him as the main Coventry centre-half hope, conditional on no further signing.
- **Joel Latibeaudiere — £4.0m**: 15 starts; one assist, 7.98 DefCon per 90. Missed the season start through knee injury, then featured more after Christmas, sometimes keeping Kitching out and deputising for Thomas.
- **Luke Woolfenden — £4.0m**: 11 starts plus six substitute appearances; 9.48 DefCon per 90. Eye-catching rate but ended as fourth-choice centre-half and is expected to fall further down the order.
- **Kaine Kesler-Hayden — £4.0m**: five starts plus 17 substitute appearances; two goals, one assist, 8.60 DefCon per 90. Right-back backup behind van Ewijk.
- **Jake Bidwell — £4.0m**: three starts plus eight substitute appearances; one assist, 7.84 DefCon per 90. Left-back backup; veteran role limits source appeal.
- **Miguel Brau — £4.0m**: one start plus eight substitute appearances; 5.97 DefCon per 90. Source describes limited impact and a four-month injury absence.
- **Aurele Amenda — £4.0m**: new signing from Eintracht Frankfurt, where he became a regular late in 2025/26. Source cites 8.97 DefCon per 90 and the required 10-action threshold in seven of 18 starts. Assumed Kitching replacement; preseason needed to confirm.

### Source rationale

- Source favors van Ewijk for likely starts and assist route, Thomas for set-piece threat, and Amenda only if his assumed starting role is confirmed.
- Dasilva is downgraded by possible left-back recruitment; Kitching and Thomas carry role/fitness history; backups carry low-start evidence.
- Coventry’s table is summarized, not reproduced as a complete visual table.

## Project interpretation

### Decision rules

- Treat van Ewijk, Thomas, and Amenda as Coventry monitoring candidates, not confirmed picks.
- Require preseason lineup evidence before selecting any £4.0m defender.
- Prefer sustained starting probability over isolated DefCon rates or Championship attacking returns.
- Do not rank inaccessible Hull, Ipswich, or other players from memory or inference.

### Practical implications

- Coventry supplies accessible evidence for one likely full-back route, one set-piece centre-half route, and one transfer-dependent centre-half route.
- The article’s promoted-team thesis cannot be evaluated fully without the gated sections.
- £4.0m value remains especially sensitive to one lineup change because bench players provide little immediate utility.

## Findings

### Evidence

- Accessible article text covers 10 Coventry defenders and identifies 26 promoted-team defenders across the full £4.0m pool.
- Van Ewijk has the strongest accessible minutes-plus-assist case.
- Thomas has the strongest accessible goal/set-piece case among established Coventry defenders.
- Amenda has an encouraging cited DefCon rate but no confirmed Coventry starting role.
- Article’s complete 46-player assessment is unavailable in current access state.

### Alternatives

- **Van Ewijk**: start security plus assist route; lower cited DefCon.
- **Thomas**: set-piece upside; fitness, rotation, and future signing risk.
- **Amenda**: possible replacement starter; Premier League transition and role uncertainty.
- **No £4.0m Coventry pick**: preserves flexibility until account-gated evidence and preseason lineups are available.

## Decision

**Verdict**: Keep van Ewijk, Thomas, and Amenda on a conditional Coventry watchlist; do not treat this partial note as a complete £4.0m ranking.

**Recommended action**:
- Obtain or recheck accessible source text before final selection.
- Confirm Coventry lineup and transfer activity during preseason.
- Leave Hull, Ipswich, and other player decisions unresolved.

**Trigger / kill switch**:
- Kill a candidate if projected starting role changes or another defender arrives.
- Reopen note when account-gated sections become available or source content updates.

## Risks and unknowns

- Hull, Ipswich, and remaining sections are inaccessible without a Fantasy Football Scout account.
- No complete article ranking or comparison across all 46 defenders is available.
- Championship starts, assists, and DefCon rates may not transfer to the Premier League.
- Amenda’s assumed replacement role is not confirmed by accessible evidence.
- Coventry transfer activity can change all listed defender roles.

## Refresh checklist

- [ ] Recheck source access and account gate.
- [ ] Confirm title, publication date, prices, and accessible sections.
- [ ] Do not infer unavailable Hull, Ipswich, or remaining assessments.
- [ ] Confirm Coventry preseason roles and transfers.
- [ ] Keep partial status and source gap explicit.
- [ ] Update `Updated`, `Data stamp`, and `Risks`.
- [ ] Delete `.tmp/agent/` scratch before finishing.
