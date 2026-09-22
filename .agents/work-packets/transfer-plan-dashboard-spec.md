# Active Task: Transfer Plan dashboard spec

- **Status:** In Progress — Explorer rename + layout + /GW; EO/Differentials retired; fog remains
- **Objective:** Hand-off remaining Later fog or close map #88.
- **Acceptance:** Tab renamed Explorer; layout Squad → table → charts → Player components; Total · /GW · /90; Top-10k EO + Differentials Ranking retired; tests green.
- **Issue/Ticket:** [Transfer Plan dashboard spec](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88)

## Work Packet (SFDBN)

- **Status:** EO crawl + Differentials Ranking product removed (crawl unreliable). Δ£ kept. Fog remains.
- **Files:** EO teardown via retire commit; `dashboard/*`, `commands/dashboard.py`, `commands/export_dashboard.py`, projections EO modules deleted, CONTEXT/README/current-state
- **Decisions:** Glossary primary **Explorer**. Order: Squad Board → rank table → charts → Player components. Top-10k EO / Differentials Ranking retired (not fog).
- **Blocked:** none.
- **Next:** Graduate fog into tickets or close map #88.

## Todo

- [x] Must grilling
- [x] Should grilling
- [x] Implement Must+Should
- [x] Later: Differentials Ranking intent (#104) — shipped then retired with EO
- [x] Later: Effective Ownership product (#105) — shipped then retired (crawl failed)
- [x] Implement EO crawl + Differentials Ranking + Δ£ — Δ£ remains; EO/Differentials removed
- [x] Retire Top-10k EO crawl + Differentials Ranking product
- [ ] Fog / remaining Later gaps or close map

## Blockers / Notes

- Fog: mini-league, price forecast, walk-forward product, plain Top-10k Own%, manual C/VC, …
