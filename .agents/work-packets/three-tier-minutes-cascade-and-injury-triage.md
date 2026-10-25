# Active Task: three-tier-minutes-cascade-and-injury-triage

- **Status:** In Progress
- **Objective:** Implement Three-Tier Minutes Cascade, sparse xMins fallback, Broad Pool Shield, and Injury Triage module & skill alignment.
- **Acceptance:**
  - Unit tests in `tests/test_xmins_override.py` and `tests/test_injury_triage.py` pass.
  - `load_xmins_override` and `build_features` support sparse overrides with `NaN` fallback to Native Champion.
  - `AdaptiveCausalChallengerModel` preserves native ML Head 1/3 and points for unlisted players when sparse overrides exist.
  - `features/injury_triage.py` and `commands/injury_triage.py` parse FPL dates, build Broad Pool Shield, and select price-bracket scouting targets.
  - `.agents/skills/transfer-planner/SKILL.md` updated with Step 2 Injury & Availability Triage.
  - Domain glossary in `CONTEXT.md` updated.
  - `ruff check .`, `pytest`, and `tests/verify.sh` pass.
- **Issue/Ticket:** Spec in `implementation_plan.md`

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:**
  - `features/builder.py`
  - `models/ml_component_challenger.py`
  - `features/injury_triage.py`
  - `commands/injury_triage.py`
  - `.agents/skills/transfer-planner/SKILL.md`
  - `CONTEXT.md`
  - `tests/test_xmins_override.py`
  - `tests/test_injury_triage.py`
- **Decisions:** 3-tier cascade with NaN fallback; automated Broad Pool Shield on fixture kickoff dates; price-bracket scouting; non-linear injury return curves.
- **Blocked:** None
- **Next:** Pre-deadline operational run validation on live GW8 picks.

## Todo
- [x] Seam 1: Write TDD test for sparse override & Champion fallback in `tests/test_xmins_override.py` (Red)
- [x] Seam 1: Implement sparse override in `features/builder.py` & `models/ml_component_challenger.py` (Green)
- [x] Seam 2: Write TDD tests for `features/injury_triage.py` (Red)
- [x] Seam 2: Implement `features/injury_triage.py` and `commands/injury_triage.py` (Green)
- [x] Seam 3: Update `.agents/skills/transfer-planner/SKILL.md` and `CONTEXT.md`
- [x] Verification: Run ruff, pytest, verify.sh, and code-review
- [ ] Pre-deadline operational run validation on live GW8 picks

## Blockers / Notes
- All 650 suite tests pass. 211 verify checks pass. Ruff clean.
