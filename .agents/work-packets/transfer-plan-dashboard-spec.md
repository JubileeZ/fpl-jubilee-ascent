# Active Task: Transfer Plan dashboard spec

- **Status:** In Progress — Must+Should + Differentials/EO build shipped; fog remains
- **Objective:** Hand-off remaining Later fog or close map #88.
- **Acceptance:** EO crawl + Differentials Ranking + Explorer Δ£ on main; tests green.
- **Issue/Ticket:** [Transfer Plan dashboard spec](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/88)

## Work Packet (SFDBN)

- **Status:** Differentials Ranking + Top-10k EO ingest implemented. Fog / unticketed Later gaps remain.
- **Files:** `projections/effective_ownership.py`, `projections/differentials_ranking.py`, `commands/effective_ownership_crawl.py`, `commands/dashboard.py`, `commands/export_dashboard.py`, `dashboard/*`
- **Decisions:** Refresh finishes charts first; EO crawl async; panel omitted until complete cache; Δ£ = observed since previous refresh.
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
