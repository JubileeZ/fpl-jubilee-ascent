# Active Task: transfer-planner-skill-and-xmins

- **Status:** In Progress
- **Objective:** Implement first-class `--xmins-override` engine support in features, models, and CLI, alongside the user-invoked `/transfer-planner` skill.
- **Acceptance:**
  - Unit tests in `tests/test_xmins_override.py` pass.
  - `--xmins-override` accepted by `commands.run_model` and `commands.solve`.
  - Skill written at `.agents/skills/transfer-planner/SKILL.md` adhering to `writing-for-agents`.
  - Ruff, pytest, and `bash tests/verify.sh` pass clean.
- **Issue/Ticket:** User request

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:**
  - `features/builder.py`
  - `models/participation_state_hybrid.py`
  - `commands/run_model.py`
  - `commands/solve.py`
  - `tests/test_xmins_override.py`
  - `.agents/skills/transfer-planner/SKILL.md`
- **Decisions:**
  - `external_xmins` column attached in `build_features` when `xmins_override` path is provided.
  - `ParticipationStateHybridModel` checks `external_xmins` and decomposes into `(p_start, p_sub_in, p_dnp, start_minutes, sub_minutes)`, preserving Champion rate and bonus Plackett-Luce math.
  - Skill is user-invoked (`disable-model-invocation: true`), presenting consolidated preflight card with default horizon 8, hits 0, gap 0.0, and warning when horizon > 10.
- **Blocked:** None
- **Next:** User testing and feedback.

## Todo
- [x] Write unit tests in `tests/test_xmins_override.py` (TDD red)
- [x] Implement `xmins_override` in `features/builder.py`
- [x] Implement state decomposition in `models/participation_state_hybrid.py`
- [x] Wire `--xmins-override` flag in `commands/run_model.py` and `commands/solve.py`
- [x] Verify test suite `tests/test_xmins_override.py` (TDD green)
- [x] Create skill `.agents/skills/transfer-planner/SKILL.md`
- [x] Run ruff, pytest, and verify.sh
- [ ] User testing and feedback on `/transfer-planner`

## Blockers / Notes
- None
