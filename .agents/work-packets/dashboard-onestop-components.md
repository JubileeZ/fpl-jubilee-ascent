# Active Task: Dashboard one-stop + component view

- **Status:** In Progress
- **Objective:** Open dashboard without CLI ingest; Click Refresh to ingest; xMins not appearance xP; selected-player component averages on the Planning Horizon
- **Acceptance:** `should_project_on_open` when processed newer than JSON; Component Profile first row is xMins; player component card; `uv run pytest tests/test_dashboard.py tests/test_ownership_explorer_view.py`; ruff
- **Issue/Ticket:** ADR 0021 / 0026

## Work Packet (SFDBN)

- **Status:** Implementing
- **Files:** `commands/dashboard.py`, `dashboard/index.html`, `dashboard/explorer.js`, `dashboard/squad.js`, `dashboard/app.js`, tests
- **Decisions:** Start projects from processed only when parquet newer than JSON (no HTTP). Refresh button still ingest+project. Minutes row = `xmins`; appearance points stay `xp_minutes`.
- **Blocked:** None
- **Next:** Restart long-running dashboard process so project-on-open is in the Python server

## Todo
- [x] Project on open when processed newer than JSON
- [x] Component Profile xMins vs Appearance xP
- [x] Selected-player component averages
- [x] Browser check Egan xMins after project
- [ ] Restart dashboard process so open-time project-on-open is live

## Blockers / Notes
- Stale JSON was empty-tenure 30.7; re-project Egan 70.3. CLI refresh_data does not rewrite JSON; Open projects when parquet newer.
- Yellow/red/OG xP still omitted from component table (~0.1 vs Total).
