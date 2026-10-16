# Active Task: explorer-underlying-actuals-table

- **Status:** In Progress
- **Objective:** Add Season-to-Date Underlying Actuals (xG, xA, xGI, Goals, Assists, GI, CS, GC, xGC, Defcon, Saves across Totals, /90, and /App) to Explorer table with dedicated presets and interactive actual minutes filter.
- **Acceptance:** Tests verify calculation, zero-minute handling, preset definitions, and dashboard rendering; ruff, pytest, and verify.sh pass.
- **Issue/Ticket:** User request /grill-with-docs + /implement

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `commands/export_dashboard.py`, `dashboard/explorer.py`, `dashboard/streamlit_dashboard.py`, `tests/test_underlying_actuals.py`, `CONTEXT.md`
- **Decisions:** Cumulative Season-to-Date grain; Total Appearances (`minutes > 0`) for `/App` and percentage denominators; Defcon threshold 10 DEF / 12 MID/FWD; Minimum Actual Minutes slider defaulting to 0; `—` for zero-sample players; two dedicated presets `"Underlying Attack"` and `"Underlying Defence"`.
- **Blocked:** None
- **Next:** Verify gate and commit.

## Todo
- [x] Write unit tests for underlying actuals computation and table presets (Red)
- [x] Implement data extraction and rate calculations in `commands/export_dashboard.py`
- [x] Update `dashboard/explorer.py` `player_slice` to include underlying metrics
- [x] Update `dashboard/streamlit_dashboard.py` with presets, column configs, and actual minutes filter
- [x] Pass all tests (Green)
- [x] Run typecheck / lint (`uv run ruff check .`) and full suite (`uv run pytest`)
- [x] Run code review and verify gate (`bash tests/verify.sh`)
- [ ] Monitor user feedback and live usage on dashboard

## Blockers / Notes
- None
