# FPL 2026/27: Best £7.0m+ Forwards

**Updated**: 2026-08-13T23:15:00+07:00  
**Data stamp**: Fantasy Football Scout article published 2026-08-11 (modified 2026-08-11); accessed 2026-08-13; cross-checked against expected-role-gw1-5.md and fpl-summer-transfers.md  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Assess £7.0m+ premium forwards for FPL 2026/27 captaincy, ownership, and opening-fixture appeal  
**Scope**: All forwards priced at £7.0m or above in FPL 2026/27 (10 players at time of writing)  
**Related**: [Pre-season guide](fpl-preseason-guide.md) · [£4.5m–£5.5m forwards](fpl-4-5m-5-5m-forwards.md) · [£6.0m–£6.5m forwards](fpl-6-0m-6-5m-forwards.md) · [Summer transfers](fpl-summer-transfers.md)

> Note created 2026-08-13 from new Fantasy Football Scout price-bracket article linked in pre-season guide (published 2026-08-11). Source claims not independently validated.

## Sources

- **Primary**: [Best £7.0m+ forwards for FPL 2026/27 — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/08/11/best-7-0m-forwards-for-fpl-2026-27) — published 2026-08-11; modified 2026-08-11; accessed 2026-08-13; role: premium forward price bracket analysis, ownership context, underlying stats, and fixture appeal
- **Cross-check**: [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — updated 2026-08-13; role: starter status and draft eligibility
- **Cross-check**: [Confirmed Summer Transfers](fpl-summer-transfers.md) — updated 2026-08-13; role: Rogers to Chelsea, Bruno Guimaraes to Arsenal, Garnacho loan to Villa

**Source boundary**: Source claims cross-checked against internal project notes. No live FPL API refresh or solver optimization run performed in this note.

## Agent Prompt

```text
Full redo docs/research/fpl-preseason-guide/fpl-7-0m-forwards.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`).
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Extract full text and analysis for all covered £7.0m+ forwards.
4. Transcribe 100% of relevant statistical images (Haaland shots/xG, fast-start history) into Markdown tables where present.
5. Keep Source synthesis strictly separate from Project interpretation.
6. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
7. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Source synthesis / price bracket analysis & cross-check audit

**Inputs**:
- Fantasy Football Scout article (`best-7-0m-forwards-for-fpl-2026-27`)
- Expected Role GW1–5 note (`expected-role-gw1-5.md`)
- Confirmed Summer Transfers register (`fpl-summer-transfers.md`)

**Procedure**:
1. Extract profiles, ownership, underlying stats, and fixture rationale for all 10 featured £7.0m+ forwards.
2. Group by appeal: premium captaincy (Haaland), high-ownership staples (Pedro, Isak), differential volume (Thiago), and rotation/minutes risks (Watkins, Gyökeres/Havertz, Sesko).
3. Cross-check starter roles and transfer impacts against project notes.

**Definitions and assumptions**:
- **£7.0m+ FWD**: Forwards priced at £7.0m or above in FPL 2026/27.

## Source synthesis

### Overview

- 2025/26 was weak for forwards overall; only 4 of the top 35 scorers still in the game were forwards.
- Five of last season's top seven forwards came from this £7.0m+ bracket; Erling Haaland (£15.5m) led on 239 points.
- 10 players priced at £7.0m+ at time of writing.

### Featured £7.0m+ Forwards

- **Erling Haaland (Man City, £15.5m)**:
  - 27 goals, 8 assists in 2025/26; 126 shots (42 more than next forward); 25.43 xG (league-leading).
  - £1.5m price hike deemed steep but fair given goal gap to second-highest forward scorer.
  - Risks: Guardiola departure, Bernardo Silva and Rodri (£6.5m, injured) absences.
  - Opening fixtures: Bournemouth (H), Crystal Palace (A), Coventry (H) — source expects strong fast start.
- **João Pedro (Chelsea, £7.5m)**:
  - 54.7% ownership (second-most owned after Haaland); 177 points (15 goals, 9 assists).
  - Rested from Brazil World Cup squad; scored hat-trick in first Xavi Alonso friendly.
  - 26 big chances (6th among forwards); 29 chances created, 6 big chances created, 9 assists (joint-4th among forwards).
  - Service from Morgan Rogers (£7.5m) and Cole Palmer (£9.5m) expected to improve chance volume.
- **Alexander Isak (Liverpool, £9.0m)**:
  - Injury-disrupted debut season: first goal GW13, leg break GW17, one further goal after GW32 return.
  - Under Andoni Iraola; creative upturn expected from Florian Wirtz (£7.5m) and Rio Ngumoha (£6.0m).
  - Hugo Ekitiké (£7.5m) out long-term; Liverpool fixtures inviting until Man City (H) in GW6.
- **Igor Thiago (Brentford, £8.0m)**:
  - 22 goals (5 fewer than Haaland), 20.57 xG; 84 shots, 41 big chances (2nd among forwards).
  - 8 penalty goals; 6 big chances created (joint-4th among forwards in position).
  - 15.8% ownership; no European football in 2026/27 reduces rotation risk vs peers.
  - More appetising opening fixtures than Ollie Watkins (£8.0m).
- **Ollie Watkins (Aston Villa, £8.0m)**:
  - 16 goals, 4 assists; 24 big chances (3rd), 15.14 xG (4th among forwards).
  - Villa slow start in 2025/26 (no goal until GW5; Watkins until GW6).
  - Morgan Rogers departure; Garnacho (£6.0m) and Johan Manzambi (£6.0m) expected to supply service.
  - Rogers + Lucas Digne (£4.5m) produced 15 assists combined last season; new midfield unknown.
  - Linked with move away; source suggests watching brief for opening fixtures.
- **Viktor Gyökeres (Arsenal, £7.5m)**:
  - 14 goals in 2025/26 (only 4 forwards scored more); weak record vs big-six.
  - Acclimatisation season; played more than Arteta intended with Kai Havertz (£7.5m) injured.
  - Havertz started CL final ahead of Gyökeres and scored; minutes likely shared with Havertz and Bruno Guimaraes (£7.0m) in midfield reducing Havertz midfield use.
- **Kai Havertz (Arsenal, £7.5m)**:
  - Injury-hampered 2025/26; 7 PL starts, 3 assists (more than Gyökeres), 2 late goals vs Man City and Burnley.
  - Preferred for big occasions per source; rotation with Gyökeres expected.
- **Hugo Ekitiké (Liverpool, £7.5m)**:
  - Torn Achilles; months away; 11 goals, 4 assists from 21 starts when fit — high quality but not GW1 option.
- **Omar Marmoush (Man City, £7.0m)**:
  - Classy but blocked by Haaland in forward line.
- **Benjamin Sesko (Man United, £7.0m)**:
  - Used sparingly in 2025/26 adaptation year; 6 goals in last 10 league matches.
  - Champions League fixture load may complicate minutes; working back to full fitness pre-GW1.
  - Man United have second-easiest opening six-match sequence on paper.

## Project interpretation

### Decision rules

1. **Captain default**: Haaland (£15.5m) remains source's premium captaincy anchor on fixtures and volume.
2. **High-ownership pivot**: João Pedro (£7.5m) and Isak (£9.0m) are source's main non-Haaland premium forward staples.
3. **Differential volume**: Igor Thiago (£8.0m) offers comparable goal threat to Watkins at lower ownership with cleaner minutes profile.
4. **Defer / monitor**: Watkins (slow-start history, Rogers exit, transfer links), Gyökeres/Havertz (minutes share), Sesko (fitness + Europe), Ekitiké (injured).

### Practical implications

- £7.0m+ bracket concentrates captaincy and premium forward spend; source frames Haaland + one of Pedro/Isak/Thiago as the core premium forward cluster.
- Arsenal forward minutes split (Gyökeres vs Havertz) and Liverpool injury context (Ekitiké out, Isak recovery) are key pre-GW1 monitoring items.

## Findings

### Evidence

- 10 forwards priced £7.0m+; Haaland at 75% ownership, Pedro at 54.7%.
- Haaland: 126 shots, 25.43 xG, 27 goals in 2025/26.
- Igor Thiago: 22 goals, 20.57 xG, 41 big chances at 15.8% ownership.
- New article published 2026-08-11; added to pre-season guide index 2026-08-13.

## Decision

**Verdict**: Haaland (£15.5m) remains the source's premium forward anchor; João Pedro (£7.5m) and Igor Thiago (£8.0m) are the standout non-Haaland picks on ownership/value balance; Watkins and Arsenal forward minutes require monitoring.

## Risks and unknowns

- Guardiola departure and City midfield injuries may affect Haaland service.
- Isak fitness and Ekitiké absence timeline uncertain.
- Watkins transfer speculation and post-Rogers Villa attack untested.
- Gyökeres/Havertz minutes split unresolved before GW1.

## Refresh checklist

- [x] Recheck source page using Playwright rendering.
- [x] Extract full player analysis for all 10 £7.0m+ forwards.
- [x] Cross-check with `expected-role-gw1-5.md` and `fpl-summer-transfers.md`.
- [x] Update parent guide index with new child note link.
- [x] Delete `.tmp/agent/` scratch files before completion.
