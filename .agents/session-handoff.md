# Session Handoff (SFDBN)

- **Status:** ADR 0016 Feature Contract ingest shipped. Full pytest 209; ruff clean.
- **Files:** `features/expected_role_prior.py`; `features/builder.py`; `commands/refresh_data.py`; `docs/adr/0016-expected-role-prior-cold-start-minutes.md`; `tests/test_expected_role_prior.py`
- **Decisions:** Snapshot `season` is availability-snapshot identity only. Table identity = `expected_role_season` or `LIVE_SEASON` (`2026-27`). Archive backtests keep this-season table; GW15+ blend is full current-season minutes.
- **Blocked:** none
- **Next:** User runs `--rebuild-roles` when Stage 1 adapters should refresh Dual-Source extract. No further ingest work.
