# Active Task: Transfer Plan dashboard spec

- **Status:** In Progress — Explorer rename + layout + /GW columns; fog remains
- **Objective:** Hand-off remaining Later fog or close map #88.
- **Acceptance:** Tab renamed Explorer; layout Squad → Differentials → table → charts → Player components; Total · /GW · /90; tests green.
- **Issue/Ticket:** [Transfer Plan dashboard spec](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88)

## Work Packet (SFDBN)

- **Status:** Explorer product rename; layout reorder; rank + Differentials **/GW**; chart polish.
- **Files:** `dashboard/index.html`, `dashboard/explorer.js`, `dashboard/app.js`, `dashboard/styles.css`, `CONTEXT.md`, `README.md`, `AGENTS.md`, `docs/agents/current-state.md`, `docs/model_name.md`, `commands/dashboard.py`, `tests/test_ownership_explorer_view.py`
- **Decisions:** Glossary primary **Explorer** (_Avoid_ Ownership Explorer). Keep all sections. Order: Squad Board → Differentials → rank table → charts → Player components. Columns Total · /GW · /90 · xMins.
- **Blocked:** none.
- **Next:** Graduate fog into tickets or close map #88.

## Todo

- [x] Must grilling
- [x] Should grilling
- [x] Implement Must+Should
- [x] Later: Differentials Ranking intent (#104)
- [x] Later: Effective Ownership product (#105)
- [x] Implement EO crawl + Differentials Ranking + Δ£
- [ ] Fog / remaining Later gaps or close map

## Blockers / Notes

- EO crawl is Official HTTP volume (~10k picks); fail closed; last complete cache kept.
- Fog: mini-league, price forecast, walk-forward product, plain Top-10k Own%, manual C/VC, …
