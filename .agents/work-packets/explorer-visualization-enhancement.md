# Active Task: Explorer Visualization Enhancement

- **Status:** In Progress
- **Objective:** Scale scatter chart markers by expected minutes (xMins / GW) and enhance player inspection with component breakdown, reality check rates, and selection verdict.
- **Acceptance:**
  1. Chart bubble sizes scale by xMins / GW (bounded 15m–180m scaling with max size 18) with inline toggle, handling zero/missing minutes gracefully.
  2. Chart hover tooltip includes xMins / GW and customdata ID preservation.
  3. Player inspection dialog displays structured cards:
     - Selection verdict & Position/Price benchmark (xP, xP/£m value, xMins reliability, position rank, 1-click peer comparison)
     - Predicted component breakdown (visual share + side-by-side projected points vs historical per-90 rates)
     - Historical match log & underlying stats (xG, xA, goals, assists, bonus, pts/90)
  4. Tests pass (`uv run pytest` - 546 passed), lint clean (`uv run ruff check .`), delivery gate passes (`bash tests/verify.sh` - 131 passed).
- **Issue/Ticket:** User request

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:**
  - `dashboard/streamlit_dashboard.py`
  - `dashboard/planner_service.py`
  - `commands/export_dashboard.py`
  - `tests/test_streamlit_dashboard.py`
- **Decisions:**
  - Bounded size scaling (floor 15m to 180m) so 0/low xMins players remain clickable.
  - Inline checkbox toggle `explorer-bubble-scale`. Retired legacy assume-90 toggle per CONTEXT.md.
  - Side-by-side predicted component score vs historical underlying rates (Option A).
  - Position peer rank & value efficiency benchmark card in inspection dialog (Option A).
  - 1-click peer comparison button (`details-compare-peer`).
  - Scoring multipliers imported from `models/scoring_matrix.py`.
- **Blocked:** None
- **Next:** Record delivery and cleanup completed packet.

## Todo
- [x] Implement bubble size scaling by xMins / GW with toggle in `dashboard/streamlit_dashboard.py`
- [x] Implement enhanced inspection view (selection verdict, component share, side-by-side predicted vs actual rates)
- [x] Add 1-click peer comparison action
- [x] Add tests for new explorer visualization features
- [x] Run ruff, pytest, and verify.sh
- [ ] Record delivery and cleanup completed packet

## Blockers / Notes
- None
