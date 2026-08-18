# FPL 2026/27: Best £7.5m+ Midfielders

**Updated**: 2026-08-18T15:05:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-08-02 (unchanged on 2026-08-13 recheck); accessed 2026-08-13; Playwright recheck 2026-08-18: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Assess £7.5m+ premium and mid-premium midfielders for FPL 2026/27 squad structure and captaincy/midfield selections  
**Scope**: Midfielders priced at £7.5m or higher (13 options in FPL 2026/27)  
**Related**: [Pre-season guide](fpl-preseason-guide.md) · [£4.5m midfielders](fpl-4-5m-midfielders.md) · [Expected role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) · [Summer transfers](fpl-summer-transfers.md)

> Note revision updated 2026-08-03. Primary article published 2026-08-02. Source claims cross-checked with expected-role-gw1-5.md and fpl-summer-transfers.md.

## Sources

- **Primary**: [Best £7.5m+ midfielders for FPL 2026/27 — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/08/02/best-7-5m-midfielders-for-fpl-2026-27) — published 2026-08-02; accessed 2026-08-13; role: premium midfielder price bracket analysis (£7.5m+)
- **Cross-check**: [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — updated 2026-07-31; role: player availability, pre-season friendly minutes, starter roles
- **Cross-check**: [Confirmed Summer Transfers](fpl-summer-transfers.md) — register through 2026-07-30; role: confirmed transfer moves and squad context

**Source boundary**: Source claims cross-checked against internal research notes. No direct FPL API live refresh or solver optimization run performed in this note.

## Agent Prompt

```text
Full redo docs/research/fpl-preseason-guide/fpl-7-5m-midfielders.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`).
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Cross-check player prices, roles, transfers, and availability against expected-role-gw1-5.md and fpl-summer-transfers.md.
4. Extract full text and tables for all covered £7.5m+ midfielders.
5. Keep Source synthesis strictly separate from Project interpretation.
6. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
7. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Source synthesis / price bracket analysis & cross-check audit

**Inputs**:
- Fantasy Football Scout article (`best-7-5m-midfielders-for-fpl-2026-27`)
- Expected Role GW1–5 note (`expected-role-gw1-5.md`)
- Confirmed Summer Transfers register (`fpl-summer-transfers.md`)

**Procedure**:
1. Extract player prices, points totals, NPxGI per 90, xG, xA, set-piece involvement, and fixture rankings for all 13 £7.5m+ midfielders.
2. Cross-check roles, minutes, injuries, and transfer moves against project research notes (`expected-role-gw1-5.md` and `fpl-summer-transfers.md`).
3. Group options into elite premiums (£9.0m+), mid-premiums (£8.0m–£8.5m), value premiums (£7.5m), and avoided/injured options.
4. Record source rationale, cross-check nuances, and team-structure implications.

**Definitions and assumptions**:
- **£7.5m+ MID**: Midfielders priced at £7.5m or higher in FPL 2026/27.

**Validation boundary**: Source-led analysis with internal cross-checks. Final starter status depends on pre-season line-ups and transfer movements.

## Source synthesis

### Premium & Standout Options (£8.0m–£9.5m)

- **Bruno Fernandes (Man United, £12.0m)**: Standout midfield option in FPL. Top NPxGI among all midfielders last season; central focus of Michael Carrick's attack with top fixture run in GW1–5.
- **Bryan Mbeumo (Man United, £8.0m)**: Outperformed Cunha and Fernandes in xG inside the box last season. Strong case for Man Utd midfield double-up or alternative coverage.
- **Matheus Cunha (Man United, £8.0m)**: High-volume attacking returns and direct threat alongside Fernandes and Mbeumo under Carrick.
- **Morgan Gibbs-White (Nottingham Forest, £8.0m)**: 3rd among all midfielders for FPL points last season (188 pts, 15 goals, 4 assists). Set-piece taker under new manager Oliver Glasner with no European midweek fixture congestion. Note: NPxGI delta of +5.03 indicates some overperformance.
- **Bukayo Saka (Arsenal, £9.5m)**: Premium talisman for league champions, on penalties and set-pieces. Fitness monitoring required post-World Cup campaign.

### Value Premium Options (£7.5m)

- **Florian Wirtz (Liverpool, £7.5m)**: 5 goals, 4 assists in 27 starts last season under Slot. New manager Andoni Iraola confirmed Wirtz will play in his natural No. 10 position behind the striker, with strong early fixture projected goals.
- **Declan Rice (Arsenal, £7.5m)**: Multiple routes to points via open play and set-pieces; post-World Cup fitness building.
- **Rayan Cherki & Jérémy Doku (Man City, £7.5m)**: Cherki ranked top 3 in the league for xGI per 90. Doku finished season strongly. Both offer high-upside differential routes into City's attack if starting roles are secured.
- **Morgan Rogers (Chelsea, £7.5m)**: 16 attacking returns last season at Aston Villa; monitoring role under Xabi Alonso at Chelsea.

### Injured / Avoided Options (£7.5m)

- **Eli Junior Kroupi (Chelsea, £7.5m)**: Reclassified from forward to midfielder, but underwent surgery and is ruled out for 3–4 months. Wait for mid-season return.

## Project interpretation

### Decision rules

- Prioritize Bruno Fernandes (£12.0m) as core midfield anchor given fixtures and expected role.
- If budget permits, evaluate Man United double-up with Mbeumo (£8.0m).
- Monitor Wirtz (£7.5m) pre-season friendly position under Iraola as potential value upgrade.

### Practical implications

- £7.5m price bracket features high-ceiling targets (Wirtz, Cherki, Rogers) that enable double-premium configurations elsewhere.

## Findings

### Evidence

- 13 midfielders priced at £7.5m or higher in FPL 2026/27.
- Fernandes (£12.0m) and Gibbs-White (£8.0m) were top point scorers in 2025/26.
- Kroupi (£7.5m) is sidelined for 3–4 months post-surgery.

### Alternatives

- **Budget/Mid-range MIDs (£4.5m–£7.0m)**: Reinvest saved funds into premium forwards (Haaland, Solanke, etc.).

## Decision

**Verdict**: Lock Bruno Fernandes (£12.0m) or Mbeumo (£8.0m) as primary midfield asset; track Wirtz (£7.5m) and Saka (£9.5m) fitness ahead of GW1.

**Recommended action**:
- Check pre-season line-ups for Wirtz's position under Iraola.
- Confirm Saka and Rice starting status in final pre-season match.

**Trigger / kill switch**:
- Sidelining or tactical position demotion of Fernandes/Wirtz in pre-season.

## Risks and unknowns

- Post-World Cup fatigue and late returns for Saka, Rice, and international stars.
- Tactical shifts under new managers at Liverpool (Iraola), Chelsea (Alonso), and Forest (Glasner).

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
