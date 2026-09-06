# Active Task: Official FPL this-season Feature Contract

- **Status:** In Progress
- **Objective:** Ship ADR 0023–0025: Official FPL Operational Dataset, This-Season Evidence shrinkage, retire Expected Role
- **Acceptance:** `build_features` Cold-Start uses Prior-Season Seed; after any this-season history row, this-season Position-Price only. Refresh pins Season Archive, no Dual-Source scrape. Explorer has xMins, no Role. `uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`
- **Issue/Ticket:** ADR 0023, 0024, 0025

## Work Packet (SFDBN)

- **Status:** Core shipped; leftover Dual-Source files not production-called
- **Files:** `features/builder.py`, `commands/refresh_data.py`, `commands/snapshot_season.py`, `commands/dashboard.py`, `commands/export_dashboard.py`, `dashboard/explorer.js`, `dashboard/index.html`, tests, ADRs 0023–0025
- **Decisions:** This-Season Evidence = non-empty `history_before_target`. Pin Season Archive on every refresh; git commit is deadline cadence. `--from-vaastav-dir` 2024-25 only. Role flags ignored.
- **Blocked:** None
- **Next:** Optional: remove unused `rebuild_expected_role.py` / `lineup-signals.json` from tree (research still reads `expected_roles.csv`)

## Todo
- [x] ADR 0024 Feature Contract clock
- [x] ADR 0023 Season Archive pin + vaastav reconstruct-only
- [x] ADR 0025 retire Role from refresh/dashboard/Explorer
- [x] Lint, pytest, verify.sh
- [ ] Remove unused Dual-Source rebuild module from tree (not on live ingest)
