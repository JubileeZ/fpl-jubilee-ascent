# Active Task: solio-decision-planner-rebuild

- **Status:** In Progress
- **Objective:** Chart Wayfinder Map #135 and child decision tickets to rebuild the dashboard with a unified Solio-style Decision Tree Planner, and resolve #136 (DDP and autosub math).
- **Acceptance:** Map #135 and child issues #136-#142 created on GitHub; #136 researched and closed with research note in `docs/research/ddp-autosub-formulation/`; tracking docs updated; tests pass.
- **Issue/Ticket:** [#135](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/135)

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `dashboard/package.json`, `dashboard/vite.config.js`, `dashboard/src/`, `commands/dashboard.py`, `dashboard/index.html`, `dashboard/app.js`, `dashboard/styles.css`
- **Decisions:** Unified Solio Decision Tree Planner replaces Transfer Plan & Strategy tabs; React 19 + @xyflow/react + Vite frontend pipeline; static script copying to dist.
- **Blocked:** None
- **Next:** Close #137 and resolve #138 (Build React Flow Decision-Tree Canvas and multi-scenario state store).

## Todo
- [x] Settle rebuild destination and architecture via breadth-first grilling
- [x] Create Wayfinder Map #135 and tickets #136-#142 on GitHub
- [x] Research DDP and autosub probability math (#136)
- [x] Close #136 and link research note in INDEX
- [x] Claim and complete #137 (Scaffold React + Vite pipeline and retire legacy Strategy tab)
- [ ] Claim #138: Build React Flow Decision-Tree Canvas and multi-scenario state store
- [ ] Claim #139: Build Interactive Squad Pitch Drawer and Lineup Scrubber
- [ ] Claim #140: Build In-Pitch Transfer Replacement Drawer with Delta xP
- [ ] Claim #141: Implement Python Highs MILP API endpoint for multi-gameweek branch optimization & DDP presets
- [ ] Claim #142: Build Multi-Scenario Plans Suite & Evaluation Scatter/Distribution view

## Blockers / Notes
- None
