# Active Task: Club Occupancy CSV (GW1–19 DEF)

- **Status:** In Progress
- **Objective:** Occupancy source of truth CSV + note Top 10 / best-per-distinct
- **Acceptance:** `def_rotation_club_occupancy.csv` unique 42,104 rows; alpha `occupancy_key`; `club_1`–`club_5`; ordinal `rank_mod_fdr`; note section + INDEX pointer; `tests/test_def_fixture_rotation.py` green
- **Issue/Ticket:** Grill-locked Club Occupancy companion

## Work Packet (SFDBN)

- **Status:** Checkpoint
- **Files:** `docs/research/def-fdr-rotation-gw1-19/`, `tests/test_def_fixture_rotation.py`, `CONTEXT.md`
- **Decisions:** Club Occupancy 2–5 distinct; `total_mod_fdr`; CSV SoT alpha-sorted; rank `(total_mod_fdr, occupancy_key)`; note = global Top 10 + 4-row best-per-distinct; `club_1`–`club_5` separate columns
- **Blocked:** None
- **Next:** Delete this packet after checkpoint commit

## Todo
- [x] Occupancy table builder + unit tests
- [x] Runner writes `def_rotation_club_occupancy.csv`
- [x] Note Findings section + INDEX pointer
- [x] pytest / ruff / verify.sh
- [ ] Delete this packet after checkpoint
