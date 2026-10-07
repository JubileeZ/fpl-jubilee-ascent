# Active Task: straight-line-decision-tree-horizon-planner

- **Status:** In Progress
- **Objective:** Align Decision Planner with MILP solver and Planning Horizon: lock boxes to horizon length, layout branches as fixed straight-line lanes, enable per-box solving with parent squad inheritance, support instant revert to solver recommendation, and anchor to pre-deadline Current User Squad origin.
- **Acceptance:** Full Planning Horizon boxes generated; strict horizontal straight-line matrix layout with disabled node dragging; per-box solving from target GW to horizon end; cached solver recommendations with instant revert; ADR 0058 recorded; CONTEXT.md updated; frontend build passes; pytest and verify.sh pass.
- **Issue/Ticket:** Decision Tree Planner Horizon & Layout Realignment

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** `dashboard/src/store/usePlanStore.js`, `dashboard/src/components/DecisionTreeCanvas.jsx`, `dashboard/src/components/nodes/PlanNode.jsx`, `dashboard/src/components/nodes/RootNode.jsx`, `dashboard/src/components/SquadPitchDrawer.jsx`, `commands/dashboard.py`, `dashboard/app.js`, `docs/adr/0058-straight-line-horizon-decision-tree.md`, `CONTEXT.md`, `tests/test_dashboard.py`
- **Decisions:** ADR 0058 straight-line multi-lane layout, horizon-locked box depth, per-box solve with parent state inheritance, dual solver/custom state with instant revert.
- **Blocked:** None
- **Next:** Push commit to origin/main and cleanup packet.

## Todo
- [x] Create ADR 0058 and update CONTEXT.md
- [x] Update backend `commands/dashboard.py` (default plan horizon generator and branch solve horizon handling)
- [x] Update `usePlanStore.js` (horizon sync, full-chain branch splitting, solverRecommendation caching and revert)
- [x] Update `DecisionTreeCanvas.jsx` (strict matrix straight-line layout, disable dragging, per-box solve)
- [x] Update `PlanNode.jsx` and `RootNode.jsx` (solve and revert buttons, solver vs custom badges, current squad title)
- [x] Update `dashboard/app.js` (sync `#plan-horizon` with React planner store)
- [x] Build dashboard (`npm run build`)
- [x] Run test suite and gate verification
- [ ] Push commit to origin/main and cleanup packet
