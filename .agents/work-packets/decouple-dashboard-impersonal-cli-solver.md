# Active Task: decouple-dashboard-impersonal-cli-solver

- **Status:** In Progress
- **Objective:** Decouple private credentials and transfer planner from web dashboard; make CLI solve default to single-arm no-hit gap 0; make dashboard export impersonal by default; replace What-If with Watchlist in Explorer.
- **Acceptance:** Tests pass; dashboard runs without credentials or transfer planner; CLI solver runs single arm no-hit gap 0 by default; export_dashboard defaults to impersonal data.
- **Issue/Ticket:** User request: Streamlit deployment without credentials, CLI transfer planner, impersonal refresh, Watchlist

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `pyproject.toml`, `commands/solve.py`, `commands/export_dashboard.py`, `dashboard/streamlit_dashboard.py`, `dashboard/explorer.py`, `tests/test_solve.py`, `tests/test_dashboard.py`, `tests/test_streamlit_dashboard.py`, `docs/product/streamlit-planner-deployment.md`, `AGENTS.md`, `README.md`, `docs/product/dashboard-usage.md`
- **Decisions:** 
  - Remove Transfer Planner and Strategy Solver from web dashboard UI.
  - Explorer replaces Squad What-If with interactive Watchlist table (fixture schedule, FDR, xP, xMins, CSV download).
  - Retain Dream Team in Explorer.
  - `commands.export_dashboard` exports impersonal data by default (`--with-squad` for personal squad).
  - `commands.solve` defaults to single-arm, `--no-hit` (weekly_hit_limit=0), gap=0.0. Added `--allow-hits`, `--scenarios`.
  - Relax `requires-python = ">=3.12"` in `pyproject.toml` for Streamlit Cloud compatibility.
  - Public data refresh in dashboard gated with admin key, optional GitHub commit persistence via GitHub Token.
- **Blocked:** None
- **Next:** Commit implementation; delete completed packet in cleanup checkpoint.

## Todo
- [x] Update `pyproject.toml` to support Python >=3.12
- [x] Update `commands/solve.py` for single-arm, no-hit, gap 0.0 defaults
- [x] Update `commands/export_dashboard.py` for impersonal export by default
- [x] Update `dashboard/explorer.py` and `dashboard/streamlit_dashboard.py` for Watchlist and remove Transfer Planner / Strategy Solver
- [x] Update and fix unit tests
- [x] Verify test suite and lint gate
- [ ] Record delivery and cleanup completed packet

## Blockers / Notes
- None
