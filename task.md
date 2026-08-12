# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete / Verified
- **Files:** `docs/research/def-fixture-rotation/run_def_rotation_analysis.py`, `docs/research/def-fixture-rotation/def-fixture-rotation.md`, `tests/test_def_fixture_rotation.py`, `data/research/def-fixture-rotation/*`, continuity docs
- **Decisions:** Extended 5-DEF fixture analysis to 2-5 unique club partitions; capped top-4 attack clubs (MCI, ARS, LIV, CHE) at max 2 DEF to protect attack quotas; restructured research note to be team-first across GW1-3 BB1 early sprint, GW4-19 post-WC, and GW1-19 set-and-forget.
- **Blocked:** None.
- **Next:** Review defender research note and team recommendations.
- **Objective:** Evaluate multi-club partitions (2-5 unique clubs) for defender rotation and establish team-level recommendations.
- **Acceptance:**
  - [x] Evaluated all 41,344 valid club combinations across 2-5 unique clubs
  - [x] Computed optimal team sets for GW1-3 BB1, GW4-19 post-WC, and GW1-19
  - [x] Updated all 5 research CSV artifacts in data/research/def-fixture-rotation/
  - [x] Restructured def-fixture-rotation.md to be team-first with trade-off matrix
  - [x] Tests green (153 passed); ruff clean; verify.sh passed
