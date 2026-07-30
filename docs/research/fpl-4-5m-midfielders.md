# FPL 2026/27 £4.5m Midfielders — Partial Fantasy Football Scout Synthesis

**Updated**: 2026-07-31T06:45:00+07:00  
**Data stamp**: Fantasy Football Scout article published 2026-07-24; accessible introduction and Coventry section reviewed 2026-07-31  
**Season**: 2026/27  
**Status**: Partial source synthesis · not independently validated  
**Purpose**: Capture accessible £4.5m midfielder minutes evidence and preserve article access gap  
**Scope**: Accessible introduction, price-pool context, and Coventry City section only. Ipswich, Hull, and remaining-player sections were not transcribed because page content stopped at an account gate.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md)

> Source gap: fetched page states that the remainder is free to read but requires a Fantasy Football Scout user account. No account-authenticated capture was supplied; inaccessible sections are not inferred.

## Sources

- **Primary**: [Best £4.5m midfielders for FPL 2026/27: All 25 assessed — FPL Marc, Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-5m-midfielders-for-fpl-2026-27-all-25-assessed) — published 2026-07-24; accessed 2026-07-31; role: £4.5m midfielder analysis

**Source boundary**: Source claims not independently validated. Only introduction and Coventry content accessible; no claims made about inaccessible Ipswich, Hull, or other sections.

## Agent Prompt

```text
Full redo docs/research/fpl-4-5m-midfielders.md

1. Re-read https://www.fantasyfootballscout.co.uk/2026/07/24/best-4-5m-midfielders-for-fpl-2026-27-all-25-assessed.
2. Confirm title, author, publication date, accessible sections, prices, roles, starts, and quoted statistics.
3. Check whether account-gated Ipswich, Hull, and remaining sections are available.
4. Do not infer or fill inaccessible player analysis.
5. Keep Source synthesis separate from Project interpretation.
6. Update Updated, Data stamp, Sources, Findings, Decision, and Risks.
7. Keep filename stable; delete .tmp/agent/ scratch before finishing.
```

## Method

**Method type**: Partial primary-source synthesis

**Inputs**:
- Supplied article capture
- Accessible article introduction and Coventry City table/discussion

**Procedure**:
1. Record article scope and promoted-team concentration.
2. Extract accessible player prices, starts, goals, assists, DefCon, and role notes.
3. Mark account-gated sections as unavailable.
4. Translate accessible claims into conditional minutes rules only.

**Definitions and assumptions**:
- **£4.5m pool**: Article states 25 midfielders at this price.
- **DefCon per 90**: Article’s defensive-contribution rate.
- **Accessible evidence**: Text returned before the article’s account gate; not a complete article review.

**Validation boundary**: Partial article-only synthesis. No FPL API, official transfer check, fixture recalculation, or model validation performed.

## Source synthesis

### Accessible article scope

- Article says budget midfielders differ from budget defenders because regular minutes are harder to find.
- Article cites Andreas Pereira’s 2022/23 example: four goals, 10 assists, and 123 points, with many returns left on benches. Source says the current objective is primarily to find a regular starter.
- Eleven of the 25 £4.5m midfielders play for promoted Coventry City, Ipswich Town, or Hull City.
- Content becomes account-gated at the Ipswich Town heading. Ipswich, Hull, and the remaining 4.5m midfielder assessments are source gaps.

### Coventry City

- **George Shepherd — £4.5m**: 0 starts and 0 substitute appearances; 0 goals, 0 assists, 0 DefCon per 90. Source says he has not made a senior debut.
- **Raphael Borges Rodrigues — £4.5m**: 0 starts plus two substitute appearances; 0 goals, one assist, 12.86 DefCon per 90. Source says the rate comes from only 35 minutes and is insufficient to judge DefCon potential. He started 29 times for Wigan Athletic in League One, producing one goal and three assists.
- **Kai Andrews — £4.5m**: 0 starts plus seven substitute appearances; 0 goals, 0 assists, 4.26 DefCon per 90. Source says he played 74 minutes across seven cameos after joining Hibernian in January and was mostly a substitute, although he scored a winner against Celtic.

### Source rationale

- Source finds almost no positive evidence for the accessible Coventry trio.
- Shepherd lacks senior minutes; Andrews was largely a substitute; Borges Rodrigues’ limited Championship sample and League One record do not establish Premier League readiness.
- Expected summer recruitment further reduces confidence that these players will become regular starters.
- Article’s Coventry table is summarized, not reproduced as a complete visual table.

## Project interpretation

### Decision rules

- Treat accessible Coventry midfielders as non-selection candidates unless preseason provides new starting evidence.
- Reject tiny DefCon samples as predictive evidence for minutes or points.
- Require regular senior starts and stable role before considering any £4.5m midfielder as a bench enabler.
- Do not rank inaccessible Ipswich, Hull, or remaining players from memory or inference.

### Practical implications

- The accessible section supports a strong minutes-first filter for £4.5m midfielders.
- Cheap midfield budget can be stranded if a player starts only as a substitute; source’s Pereira example illustrates this benching risk.
- Promoted-team recruitment is a central unknown for the whole price pool.

## Findings

### Evidence

- Accessible text covers three Coventry midfielders and states that 11 of 25 £4.5m midfielders come from promoted teams.
- None of the accessible Coventry players has a 2025/26 starting record supporting immediate Premier League selection.
- Borges Rodrigues has the highest cited DefCon rate, but only across 35 minutes.
- Complete article assessment is unavailable in current access state.

### Alternatives

- **Wait for promoted-team lineups**: preserves flexibility and improves minutes evidence.
- **Use a proven higher-priced midfielder**: costs more but avoids relying on an untested £4.5m starter.
- **Select a £4.5m placeholder**: only rational if transfer rules and bench role tolerate zero or low minutes.

## Decision

**Verdict**: Do not select an accessible Coventry £4.5m midfielder on current evidence; keep the full price-pool decision open because most article content is inaccessible.

**Recommended action**:
- Recheck source access and preseason lineups.
- Obtain complete source evidence before creating a full £4.5m shortlist.
- Keep article claims separate from project projections.

**Trigger / kill switch**:
- Reopen selection if a player becomes a confirmed regular starter with a stable role.
- Reopen note when account-gated Ipswich, Hull, and remaining sections become available.

## Risks and unknowns

- Ipswich, Hull, and 14 remaining player assessments are inaccessible without a Fantasy Football Scout account.
- No complete article ranking or full 25-player comparison is available.
- Championship, League One, and cameo statistics may not transfer to Premier League minutes or output.
- Transfer recruitment can change promoted-team depth charts.
- Article’s historical Pereira example is illustrative, not a forecast.

## Refresh checklist

- [ ] Recheck source access and account gate.
- [ ] Confirm title, author, publication date, prices, and accessible sections.
- [ ] Do not infer unavailable Ipswich, Hull, or remaining assessments.
- [ ] Confirm promoted-team preseason roles and transfers.
- [ ] Keep partial status and source gap explicit.
- [ ] Update `Updated`, `Data stamp`, and `Risks`.
- [ ] Delete `.tmp/agent/` scratch before finishing.
