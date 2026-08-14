# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete / Verified
- **Files:** `docs/research/def-fixture-rotation/run_def_rotation_analysis.py`, `docs/research/gkp-fixture-rotation/run_gkp_rotation_analysis.py`, `docs/research/def-fixture-rotation/def-fixture-rotation.md`, `docs/research/gkp-fixture-rotation/gkp-fixture-rotation.md`, `docs/research/INDEX.md`, `tests/test_def_fixture_rotation.py`, `tests/test_gkp_fixture_rotation.py`, `task.md`
- **Decisions:** Implemented unconditional max(xP) weekly selection, Poisson clean sheets, Fixture Overlap Index (FOI), data-derived outfield shadow price slope ($\gamma \approx 0.24-0.25$), Opportunity-Cost Adjusted Net Value (OC-RQI), intra-club diagonal correlation ($r=1.0$), and auto-sub defender EV (12% 4th def, 3% 5th def); executed full downstream refresh pipeline across Stage 2, Stage 3, GKP rotation, DEF rotation, and Ownership Value Explorer; updated research documentation tables and findings; verified full test suite (170/170 passed) and delivery gate checks (29/29 green).
- **Blocked:** None.
- **Next:** Propose commit for metrics redesign and research documentation update.
- **Objective:** Redesign DEF and GKP rotation ranking metrics to eliminate legacy FDR artifacts, implement OC-RQI and FOI, execute full downstream refresh, and update research documentation.
- **Acceptance:**
  - [x] Multi-agent mathematical & decision audit completed with concrete failure modes diagnosed
  - [x] Grilling session completed with agreed replacement metrics (max(xP), Poisson xCS, OC-RQI, FOI)
  - [x] Implemented OC-RQI, FOI, diagonal fix, auto-sub EV, and max(xP) in GKP and DEF rotation scripts
  - [x] Full downstream pipeline executed (`refresh_downstream.py`) regenerating all CSV artifacts
  - [x] Research markdown notes updated with new tables, formulas, and findings
  - [x] Test suite and linting 100% clean (170 tests passed, ruff clean, verify.sh 29/29 green)

