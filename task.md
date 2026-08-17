# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** `docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py`, `tests/test_expected_role_name_match.py`, role/stats/projection CSVs, research notes, `task.md`
- **Decisions:** Score matrix correct. Role matcher was wrong: single-token source names hit middle/given names. Incoming transfers kept vacated Out of Contention. Floor those to Rotation; rebuild downstream.
- **Blocked:** None.
- **Next:** None. Dual NEW GKP (Pope Meerkat + Horníček FFS) left as two Regulars — conflict rules, not two Nailed.
- **Objective:** Role, event rates, and xP for transferred/new starters match live FPL clubs and Stage 1 conflict rules.
- **Acceptance:**
  - [x] Role `club_short` equals API club for every contention row.
  - [x] No club with two Nailed GKs; transferred #1s keep Draft role when FFS/Meerkat still start them.
  - [x] Trafford/Rushworth dest GC from LEE/COV, not old clubs.
  - [x] `uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh` green.
