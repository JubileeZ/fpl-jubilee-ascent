# Session Handoff (SFDBN)

- **Status:** Availability snapshot CI fix on `main` this commit. OP1 still `17f8d23`. Nested FPL list hash unblocked hourly Capture. Promotion workflow already green.
- **Files:** `features/availability_snapshots.py`; `tests/test_availability_snapshots.py`; `.github/workflows/*.yml`; `task.md`; `docs/agents/current-state.md`
- **Decisions:** Keep both GitHub workflows. Nested FPL JSON → canonical strings before sort/hash. `checkout@v5`, `setup-uv@v7`, Python 3.14.
- **Blocked:** none
- **Next:** Next hourly/manual Capture should write GW1 package and may create `availability-snapshots`. User copy pre-WC 15 into FPL app before GW1 deadline (`operational_squads.csv` `pre-WC`; XI `operational_select_11.csv` `gw=1`; Bench Boost).
