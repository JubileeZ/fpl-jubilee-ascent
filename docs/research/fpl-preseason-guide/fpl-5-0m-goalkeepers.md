# FPL 2026/27: Best £5.0m+ Goalkeepers

**Updated**: 2026-08-18T15:05:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-07-31 (unchanged on 2026-08-13 recheck); accessed 2026-08-13; Playwright recheck 2026-08-18: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Assess £5.0m+ goalkeepers for FPL 2026/27 squad structure and goalkeeper selection  
**Scope**: Goalkeepers priced at £5.0m, £5.5m, and £6.0m  
**Related**: [Pre-season guide](fpl-preseason-guide.md) · [Budget goalkeepers](fpl-budget-goalkeepers.md) · [Expected role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) · [Summer transfers](fpl-summer-transfers.md)

> Note revision updated 2026-08-01. Source claims cross-checked with expected-role-gw1-5.md and fpl-summer-transfers.md.

## Sources

- **Primary**: [Best £5.0m+ goalkeepers for FPL 2026/27 — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/07/31/best-5-0m-goalkeepers-for-fpl-2026-27) — published 2026-07-31; accessed 2026-08-13; role: £5.0m+ goalkeeper price bracket analysis
- **Cross-check**: [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — updated 2026-07-31; role: player availability, pre-season friendly minutes, starter roles
- **Cross-check**: [Confirmed Summer Transfers](fpl-summer-transfers.md) — register through 2026-07-30; role: confirmed transfer moves and squad context

**Source boundary**: Source claims cross-checked against internal research notes. No direct FPL API live refresh or solver optimization run performed in this note.

## Agent Prompt

```text
Full redo docs/research/fpl-5-0m-goalkeepers.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`).
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Cross-check player prices, roles, transfers, and availability against expected-role-gw1-5.md and fpl-summer-transfers.md.
4. Extract full text and tables for all covered £5.0m+ goalkeepers.
5. Keep Source synthesis strictly separate from Project interpretation.
6. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
7. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Source synthesis / price bracket analysis & cross-check audit

**Inputs**:
- Fantasy Football Scout article (`best-5-0m-goalkeepers-for-fpl-2026-27`)
- Expected Role GW1–5 note (`expected-role-gw1-5.md`)
- Confirmed Summer Transfers register (`fpl-summer-transfers.md`)

**Procedure**:
1. Extract player prices, clean sheet records, fixture rankings, and rotation concerns for £5.0m–£6.0m goalkeepers.
2. Cross-check roles, minutes, injuries, and transfer moves against project research notes (`expected-role-gw1-5.md` and `fpl-summer-transfers.md`).
3. Group options into £6.0m, £5.5m, standout £5.0m, and avoided £5.0m picks.
4. Record source rationale, cross-check nuances, and team-structure implications.

**Definitions and assumptions**:
- **£5.0m+ GKP**: Goalkeepers priced at £5.0m, £5.5m, or £6.0m in FPL 2026/27.

**Validation boundary**: Source-led analysis with internal cross-checks. Final starter status depends on pre-season line-ups and transfer movements.

## Source synthesis

### £6.0m Goalkeepers

- **David Raya (Arsenal, £6.0m)**: Most expensive goalkeeper in FPL following 19 clean sheets in 2025/26. Premium entry into Arsenal's defensive line with Gabriel (£8.0m) expensive, Saliba (£6.0m) out due to extended rehab (`expected-role-gw1-5.md`), and full-back spots rotated.

### £5.5m Goalkeepers

- **Jordan Pickford (Everton, £5.5m)**: Favourable opening 6 fixtures (tops Fixture Ticker, facing 2 promoted teams, Palace, Bournemouth). More appealing than Tarkowski (£6.0m) or Branthwaite (£5.5m fitness building).
- **Alisson Becker (Liverpool, £5.5m)** & **Gianluigi Donnarumma (Man City, £5.5m)**: Secure access to top defenses, but lacked save/bonus upside to justify premium price over cheaper alternatives.

### Standout £5.0m Goalkeepers

- **Senne Lammens (Man United, £5.0m)**: Only £5.0m GKP ranked top 5 in Rate My Team projections. Excellent opening fixtures under Carrick. Main drawback is Luke Shaw (£4.5m) offering cheaper defensive cover.
- **Robert Sánchez (Chelsea, £5.0m)**: Cheapest secure route into Chelsea defense under new management with no European fixtures. Teammates Lacroix (£6.0m transfer from CRY per `fpl-summer-transfers.md`), James (£5.5m), Palestra (£5.5m) cost more.
- **Caoimhín Kelleher (Brentford, £5.0m)**: 2nd highest scoring FPL goalkeeper in 2025/26 despite Brentford keeping only 10 clean sheets, driven by save volume (2nd to Dubravka).
- **Nick Pope (Newcastle, £5.0m)**: 3rd best opening 6 fixtures on Fixture Ticker. Managerial change/instability offset by strong schedule (promoted sides, Leeds, Bournemouth). *Cross-check note*: Demoted from Nailed to Regular Starter in `expected-role-gw1-5.md` following shared pre-season minutes with Ewen Jaouen (who started vs Bristol City).

### Avoided £5.0m Goalkeepers

| Club | Player | Reason to Avoid | Cross-Check Status |
|---|---|---|---|
| Arsenal | Kepa Arrizabalaga | Rumoured departure / Backup | Backup to Raya |
| Arsenal | Illan Meslier | Backup | Confirmed transfer from Leeds (`fpl-summer-transfers.md`) |
| Chelsea | Filip Jörgensen | Likely to leave | Backup / exit candidate |
| Everton | Mark Travers | Backup | Backup behind Pickford (£5.5m) |
| Liverpool | Giorgi Mamardashvili | Backup | Backup behind Alisson (£5.5m) |
| Man City / Leeds | James Trafford | Backup at Man City; monitor if Leeds transfer completes | Transfer to Leeds practically confirmed (`expected-role-gw1-5.md` / `fpl-summer-transfers.md`) |

## Project interpretation

### Decision rules

- If prioritizing Arsenal defense without rotation risk, evaluate Raya (£6.0m) over full-backs.
- If selecting a £5.0m GKP, prioritize Lammens (£5.0m) or Sánchez (£5.0m) over £5.5m options unless Pickford's opening 6 fixtures are targeted.
- If Trafford completes transfer to Leeds at £5.0m, re-evaluate as potential starter.

### Practical implications

- £5.0m price bracket offers viable starting options (Lammens, Sánchez, Kelleher), reducing need to spend £5.5m–£6.0m on goalkeepers.

## Findings

### Evidence

- Raya (£6.0m) is sole top-tier goalkeeper price.
- 14 goalkeepers priced at £5.0m; at least 5 are non-starting backups.

### Alternatives

- **Budget GKP (£4.0m–£4.5m)**: Save £0.5m–£1.0m to reinvest in outfield positions.
- **Premium DEF (£6.0m+)**: Pair budget GKP with attacking defenders for higher ceiling.

## Decision

**Verdict**: Monitor Lammens (£5.0m) and Sánchez (£5.0m) as top £5.0m goalkeeper options; reserve Raya (£6.0m) for premium Arsenal defense double-ups.

**Recommended action**:
- Compare Lammens/Sánchez projected points against £4.5m defenders before finalizing GKP budget.
- Track James Trafford transfer status.

**Trigger / kill switch**:
- Trafford transfer to Leeds or confirmed starting status for Lammens/Sánchez in final pre-season friendlies.

## Risks and unknowns

- Managerial changes at Newcastle and Chelsea could alter defensive structures and starting selections.
- Transfer movements (Trafford, Kepa, Jörgensen) may change starter availability at £5.0m.

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
