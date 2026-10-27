# Active Task: strategic-arm-horizon-scaling-ft-schedule

- **Status:** Complete
- **Objective:** Implement horizon scaling for one-off Strategic penalties (hit_friction, gk_transfer_friction), diminishing emergency Free Transfer Value schedule (ft_value_list), Strategic audit metadata, and ADR 0065.
- **Acceptance:** Full test suite passes, verify.sh clean, ruff clean, unit tests verify scaling and FT schedule, smoke run verifies FT preservation at H=10.
- **Issue/Ticket:** Strategic Arm Horizon Scaling & FT Value Schedule

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:**
  - `solver/scenarios.py`
  - `solver/solver.py`
  - `solver/transfer_plan.py`
  - `commands/solve.py`
  - `docs/adr/0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md`
  - `docs/agents/current-state.md`
  - `tests/test_scenarios.py`
  - `tests/test_solve.py`
  - `tests/test_strategic_solver.py`
  - `tests/test_transfer_plan_scenarios.py`
- **Decisions:**
  - Packet 1 defect check confirmed export_dashboard already sets immediate_next_gw=target_start (GW9) with 0.0 points/minutes for red-flagged assets.
  - Scale one-off strategic penalties by eff(H)/eff(5) using decay_base (0.85).
  - Adopt tapering Strategic FT schedule {"2": 2.0, "3": 1.2, "4": 0.6, "5": 0.2} scaled by eff(H)/eff(5).
  - Keep ft_use_penalty unscaled (0.2).
  - Record active FT schedule and scaled parameters in meta["strategic_audit"].
  - Non-strategic arms (unconstrained, no_hit) clear ft_value_list.
  - Repeated apply_scenario_arm calls are uncompounded and idempotent.
- **Blocked:** None
- **Next:** Commit work packet and changes.

## Todo
- [x] Create tests/test_transfer_plan_scenarios.py assertions for effective_horizon_scale and scaled strategic options
- [x] Implement effective_horizon_scale and scaled arm overrides in solver/scenarios.py
- [x] Wire horizon parameter into apply_scenario_arm and commands/solve.py / scenarios digest
- [x] Enhance solver/solver.py and solver/transfer_plan.py strategic audit reporting
- [x] Draft docs/adr/0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md
- [x] Run pytest, ruff, and smoke test H=6 and H=10
- [x] Run code-review and tests/verify.sh
