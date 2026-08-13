# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete / Verified
- **Files:** `docs/research/def-fixture-rotation/wc4-sun-bridge.md`, `docs/research/def-fixture-rotation/wc4-overall-bridge.md`, `docs/research/def-fixture-rotation/def-fixture-rotation.md`, `docs/research/def-fixture-rotation/run_def_rotation_analysis.py`, `data/research/def-fixture-rotation/def_wc4_overall_bridge_matrix.csv`, `tests/test_def_fixture_rotation.py`, `docs/research/INDEX.md`
- **Decisions:** Child notes for constrained WC4. Overall pick `LIV-MCI-MUN-MUN-NFO`. SUN pick unchanged. Separate CLI flags.
- **Blocked:** None.
- **Next:** None.
- **Objective:** Split SUN WC4 bridge into a standalone sub-report; add unrestricted overall 1–2 swap bridge as a second sub-report with independent refresh.
- **Acceptance:**
  - [x] Parent §1.4 hubs to both children with refresh commands
  - [x] `wc4-sun-bridge.md` and `wc4-overall-bridge.md` open standalone
  - [x] `--sun-bridge-only` / `--overall-bridge-only` / `--bridges-only` work
  - [x] Overall CSV 5,623 rows; #1 is 0-SUN `LIV-MCI-MUN-MUN-NFO`
  - [x] Tests green; ruff clean
