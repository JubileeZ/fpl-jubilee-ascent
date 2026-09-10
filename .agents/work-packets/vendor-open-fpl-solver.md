# Active Task: Vendor current open-fpl-solver

- **Status:** Done
- **Objective:** Replace sasoptpy solver copy with upstream highspy `dev/solver.py`; keep planning + Transfer Plan as our layer
- **Acceptance:** `uv run pytest` 316 passed; `solver/solver.py` has no sasoptpy; vendor SHA `2ff829f`
- **Issue/Ticket:** ADR 0030

## Work Packet (SFDBN)

- **Status:** Gates green; ready to commit
- **Files:** `solver/solver.py`, `solver/vendor.py`, `solver/planning.py` (unchanged), `solver/transfer_plan.py` (unchanged), `pyproject.toml`, `tests/test_solver_static.py`, ADR 0030
- **Decisions:** Vendor = open-fpl-solver `main` @ `2ff829fff2a4740e71e637f2c5823dbb2fb0a93d`. Keep planning + Transfer Plan. Re-apply load_solver_static, code merge, force_keep/ban, enabled chips, HiGHS parallel/threads. Drop sasoptpy. Preseason ITB £100.0m.
- **Blocked:** none
- **Next:** none

## Todo
Vendored this session. Checkpoint record for commit-gate.

## Blockers / Notes
- None
