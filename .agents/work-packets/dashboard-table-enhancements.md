# Active Task: Dashboard Table Enhancements

- **Status:** In Progress
- **Objective:** Improve table column arrangement, pinning, 3-way Reality Check view, and Watchlist comparison with score heatmap.
- **Acceptance:**
  - Invariant lead sequence: `[Player, Position, Club, Price, xP, xP / GW]` across all views.
  - Native column pinning (`pinned=True`) for `Player`, `Position`, `Club`.
  - New "Reality Check" view preset pairing Actual, Underlying Expected, and Model Projections side-by-side.
  - Player Watchlist supports view presets (`Schedule (Heatmap)`, `Overview`, `Reality Check`, `Attacking`, `Defensive`).
  - Score heatmap styling on `xP`/`xP / GW` and Watchlist schedule cells.
  - Test suite passes, Ruff and verify.sh clean.
- **Issue/Ticket:** User request /implement confirm

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `dashboard/streamlit_dashboard.py`, `dashboard/explorer.py`, `tests/test_streamlit_dashboard.py`, `CONTEXT.md`
- **Decisions:** Clustered 3-way triad columns, 4-tier emerald heatmap palette, 3 pinned columns with compact widths.
- **Blocked:** None
- **Next:** Implement TDD tests for new presets and column configurations.

## Todo
- [x] Add unit/integration tests for column arrangement, pinning, and Reality Check preset
- [x] Implement standardized lead columns and column pinning in `dashboard/streamlit_dashboard.py`
- [x] Implement Reality Check view preset in `dashboard/streamlit_dashboard.py`
- [x] Implement Watchlist view selector and comparison modes in `dashboard/streamlit_dashboard.py` and `dashboard/explorer.py`
- [x] Implement score heatmap styling
- [x] Update domain documentation in `CONTEXT.md`
- [x] Run full test suite, ruff, and verify.sh
- [x] Perform two-axis code-review
- [ ] Monitor live usage and user feedback in Streamlit Explorer

## Blockers / Notes
- None
