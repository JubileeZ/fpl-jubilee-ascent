# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete / Verified
- **Files:** `docs/research/def-fixture-rotation/run_def_rotation_analysis.py`, `tests/test_def_fixture_rotation.py`, `def-fixture-rotation.md`, `wc4-sun-bridge.md`, `wc4-overall-bridge.md`, `def_club_5way_rotation_matrix.csv`, bridge CSVs
- **Decisions:** GW4–19 ranking = correlation-first among min rot FDR + 100% zero-diff. Canonical dest `AVL-BOU-CHE-LIV-NFO`. Bridge dest picker same tie-break; City-core dest only when it is the sole 2-swap 2.4375 option.
- **Blocked:** None.
- **Next:** None for this packet.
- **Objective:** Align DEF rotation parent + WC4 bridge notes to one correlation-first ranking lens.
- **Acceptance:**
  - [x] Ranking lens constants in `run_def_rotation_analysis.py`
  - [x] Club 5-way sort: rot FDR → zero-diff% → corr (asc) → easy%
  - [x] Bridge dest picker prefers more negative dest corr before easy%
  - [x] Parent + both bridge notes match CSV ranks
  - [x] Tests green; ruff clean
