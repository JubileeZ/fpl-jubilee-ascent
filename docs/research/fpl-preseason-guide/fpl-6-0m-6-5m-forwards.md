# FPL 2026/27: Best £6.0m–£6.5m Forwards

**Updated**: 2026-08-01T15:52:00+07:00  
**Data stamp**: Fantasy Football Scout article published 2026-07-31; accessed 2026-08-01  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Assess £6.0m–£6.5m forwards for FPL 2026/27 forward line composition  
**Scope**: Forwards priced at £6.0m and £6.5m  
**Related**: [Pre-season guide](fpl-preseason-guide.md) · [Confirmed summer transfers](fpl-summer-transfers.md) · [Expected Role GW1–5](expected-role-gw1-5.md)

> Note revision updated 2026-08-01. Source claims not independently validated.

## Sources

- **Primary**: [Best £6.0m-£6.5m forwards for FPL 2026/27 — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/31/best-6-0m-6-5m-forwards-for-fpl-2026-27) — published 2026-07-31; accessed 2026-08-01; role: £6.0m–£6.5m forward price bracket analysis

**Source boundary**: Source claims not independently validated. No FPL API refresh, fixture recalculation, projection run, or lineup verification performed.

## Agent Prompt

```text
Full redo docs/research/fpl-6-0m-6-5m-forwards.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`).
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Extract full text and tables for all covered £6.0m–£6.5m forwards.
4. Keep Source synthesis strictly separate from Project interpretation.
5. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
6. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Source synthesis / price bracket analysis

**Inputs**:
- Fantasy Football Scout article (`best-6-0m-6-5m-forwards-for-fpl-2026-27`)

**Procedure**:
1. Extract player prices, goal returns, underlying xG metrics, and minutes risk for 16 players in £6.0m–£6.5m bracket.
2. Identify leading options, rotation risks, and pending transfer movements.
3. Record source rationale and team-structure implications.

**Definitions and assumptions**:
- **£6.0m–£6.5m FWD**: Forwards priced at £6.0m or £6.5m in FPL 2026/27.

**Validation boundary**: Source-led analysis. Final starter status depends on pre-season lineups, manager hires, and transfer completions.

## Source synthesis

### Leading Contenders

- **Dominic Calvert-Lewin (Leeds, £6.0m)**: 17.9% ownership following 14 goals last season. Highest value forward (0.68 points/m/match). 3rd among forwards for xG (15.81), 4th for box shots (68) and big chances (33). On penalties; favourable fixtures until GW6.
- **Brian Brobbey (Sunderland, £6.0m)**: Highest owned in bracket (22.5%). Established starter from GW16 last season; 3 World Cup goals for Netherlands. Not on penalties; European fixture rotation risk; tough opening schedule.
- **Will Osula / Nick Woltemade (Newcastle, £6.0m)**: Newcastle rank 1st on Fixture Ticker for opening 10 matches. Osula started final 7 matches in 2025/26 (5 goals). Managerial change (Howe departure, potential Jaissle appointment) creates selection uncertainty.
- **Evanilson (Bournemouth, £6.0m)**: Maintained starting role due to Kroupi (£7.5m) long-term injury, but £25.7m signing of Alvaro Rodriguez (£6.0m) adds competition. High volume (87 box passes received, 15 six-yard box shots) but poor conversion (6 goals, -4.59 xG underperformance). Tough early fixtures until GW6 under Marco Rose.
- **Jean-Philippe Mateta (Crystal Palace, £6.5m)**: 31 big chances last season (5th among forwards). Competition from Strand Larsen (£6.0m) and World Cup fatigue may prompt new manager Pierre Sage to ease him in despite good GW1–6 fixtures (5th on Ticker).
- **Igor Jesus (Nottingham Forest, £6.0m)**: 7 goals in Europa League but low top-flight xG efficiency (0.09 xG per shot). Strong pre-season form (3 friendly goals); Oliver Glasner could pick him over Wood (£6.0m) or Awoniyi (£5.5m).
- **Dominic Solanke (Spurs, £6.5m)**: Proven 19-goal season in 2023/24; rotation/injury history. Spurs fixtures improve from GW7.

### Pending Transfers & Other Options

- **Danny Welbeck (£6.0m)**: Imminent move to Chelsea as backup to Joao Pedro (£7.5m).
- **Nicolas Jackson (£6.5m)**: Linked with Villa if Welbeck joins Chelsea; appeal tied to Ollie Watkins (£8.0m) status.

## Project interpretation

### Cross-model role alignment (expected-role-gw1-5.md)

- **Nailed Starters**: Dominic Calvert-Lewin (Leeds, £6.0m) and Brian Brobbey (Sunderland, £6.0m) are confirmed Nailed Starters in `expected-role-gw1-5.md`.
- **Regular Starters**: Dominic Solanke (Spurs, £6.5m), Igor Jesus (Nott'm Forest, £6.0m), Strand Larsen (Crystal Palace, £6.0m), and Beto (Everton, £6.0m) are listed as Regular Starters.
- **Rotation / Competition**: Mateta (Palace, £6.5m, behind Strand Larsen), Evanilson (Bournemouth, £6.0m, alongside Alvaro Rodriguez behind Kroupi Jr), Chris Wood (Forest, £6.0m), Osula (Newcastle, £6.0m), and Welbeck (Brighton, £6.0m) are classified as Rotation options.

### Decision rules

- If seeking a budget starting forward with penalty duty and strong underlying xG, evaluate Calvert-Lewin (£6.0m).
- If selecting Newcastle forwards (Osula/Woltemade), await pre-season lineup confirmation under new manager before GW1 deadline.
- Prefer Strand Larsen (£6.0m) over Mateta (£6.5m) for Crystal Palace forward coverage based on GW1–5 expected starting role.
- Avoid Welbeck (£6.0m) due to impending backup role / transfer uncertainty.

### Practical implications

- £6.0m–£6.5m forward bracket features high volatility due to managerial changes (Newcastle, Palace, Forest, Bournemouth) and pending transfers.
- Cross-checking against `expected-role-gw1-5.md` reveals Calvert-Lewin (£6.0m) and Brobbey (£6.0m) as the safest starter picks in this price bracket.

## Findings

### Evidence

- Calvert-Lewin (£6.0m) posted highest xG (15.81) among £6.0m–£6.5m options.
- 16 players priced in £6.0m–£6.5m bracket, but majority carry rotation or transfer uncertainty.
- Cross-check against `expected-role-gw1-5.md` confirms 2 Nailed Starters (Calvert-Lewin, Brobbey) and 4 Regular Starters (Solanke, Igor Jesus, Strand Larsen, Beto) in this price tier.

### Alternatives

- **£7.5m+ Forwards**: Pay premium for guaranteed minutes and proven finishing.
- **5-Midfielder Formation (3-5-2 / 4-5-1)**: Limit forward spending to one budget option.

## Decision

**Verdict**: Track Dominic Calvert-Lewin (£6.0m) as primary budget forward target; monitor Newcastle (Osula) and Forest (Igor Jesus) pre-season lineups.

**Recommended action**:
- Monitor Leeds and Newcastle pre-season friendlies for starting XI clarity.
- Re-check transfer completions for Welbeck and Jackson before GW1.

**Trigger / kill switch**:
- New manager tactical setup at Newcastle or Forest favoring alternative strikers.

## Risks and unknowns

- Managerial changes at Newcastle, Palace, Bournemouth, and Forest introduce early-season rotation risk.
- Expected goals underperformance (Calvert-Lewin, Evanilson) may persist if finishing quality does not improve.

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.

