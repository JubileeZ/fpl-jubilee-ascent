# Active Task: sidebar-strategy-research-dashboard

- **Status:** In Progress
- **Objective:** Add Left Sidebar navigation to dashboard switching across 5 views: Explorer, Transfer Plan, Strategy Solver, Research, and Model Methodology. Expose soft/hard solver constraints in Strategy Solver. Expose research topics and projection methodology interactively.
- **Acceptance:** Left sidebar navigates all 5 views; Strategy Solver UI exposes hard/soft constraints and executes via API; Research tab renders topic notes and companions; Model Methodology shows 4 projection layers; all existing tests pass and lint clean.
- **Issue/Ticket:** User Request 2026-10-02

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** dashboard/index.html, dashboard/styles.css, dashboard/app.js, commands/dashboard.py, tests/test_dashboard.py, docs/research/INDEX.md, CONTEXT.md
- **Decisions:** Persistent 240px Left Sidebar with slide/collapse toggle (collapsible on mobile, min 44px tap targets); Inter typography per DESIGN.md; robust player name resolution for solver constraints; archived product UI spec to docs/archive/wayfinder-transfer-plan-spec/.
- **Blocked:** None
- **Next:** User browser verification of 5-view navigation and strategy solver.

## Todo
- [x] Add Left Sidebar navigation and 3 new view panels (Strategy Solver, Research, Model Methodology) in `dashboard/index.html`
- [x] Style Left Sidebar and new panels in `dashboard/styles.css` adhering to `DESIGN.md`
- [x] Add backend endpoints in `commands/dashboard.py` for `/api/strategy-solve` and `/api/research/*`
- [x] Implement UI logic in `dashboard/app.js` for view switching, solver constraints submission, research loading, and methodology calculation
- [x] Update tests in `tests/test_dashboard.py`
- [x] Address code review findings:
  - [x] Revert font to `Inter` in `index.html` and `styles.css` per `DESIGN.md`
  - [x] Enforce 44px min tap target on mobile `.sidebar-nav .nav-item`
  - [x] Add explicit type annotations to `fake_start_strategy` in `tests/test_dashboard.py`
  - [x] Extract `_active_job_conflict()` helper in `commands/dashboard.py`
  - [x] Add `_resolve_player_ids()` with player name lookup to avoid matrix key errors in solver
  - [x] Fix companion CSV `total_rows` calculation
  - [x] Make methodology comparison slate and candidate ledger stats dynamic
  - [x] Move `wayfinder-transfer-plan-spec` to `docs/archive/` and update `docs/research/INDEX.md` and `CONTEXT.md`
  - [x] Implement slide/collapse sidebar toggle button
- [x] Verify test suite (504/504) & ruff check & verify.sh (115/115)
- [ ] Live browser verification on http://127.0.0.1:8000

## Blockers / Notes
- antislop active: during (session override)
