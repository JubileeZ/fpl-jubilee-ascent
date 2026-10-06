# Active Task: zero-gap-3-arm-transfer-plan-caching

- **Status:** In Progress
- **Objective:** Zero-gap MILP default, deterministic input digest caching for re-solve avoidance, CLI 3-arm default with progressive output, and Decision Tree Planner 3-arm branching.
- **Acceptance:** Tests pass, zero-gap default enforced, cached results reused on unchanged digest, 3 arms solved by default in CLI and Decision Tree Planner.
- **Issue/Ticket:** User Request 2026-10-06 / Grilling Rounds 1-2

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** `solver/transfer_plan.py`, `solver/scenarios.py`, `commands/transfer_plan_scenarios.py`, `commands/solve.py`, `commands/dashboard.py`, `dashboard/src/components/DecisionTreeCanvas.jsx`, `docs/adr/0057-zero-gap-digest-caching-3-arm-transfer-plan.md`, `tests/test_*.py`
- **Decisions:** Default gap 0.0 supersedes ADR 0043; SHA-256 digest on operational inputs caches 3-arm transfer plan; CLI and Decision Tree Planner default to 3 arms with progressive results.
- **Blocked:** None
- **Next:** Run gates and commit.

## Todo
- [x] Create ADR 0057
- [x] Implement zero gap default in `solver/transfer_plan.py` and update `tests/test_transfer_plan.py`
- [x] Implement deterministic digest in `solver/scenarios.py` and caching in `commands/transfer_plan_scenarios.py`
- [x] Update `commands/solve.py` to default to 3 arms with progressive terminal printing and cache loading
- [x] Update `commands/dashboard.py` for instant cached load and 3-arm branch solve
- [x] Update `DecisionTreeCanvas.jsx` for 3-arm branching
- [x] Run full test suite and verify
- [ ] Push commit to origin/main and cleanup packet
