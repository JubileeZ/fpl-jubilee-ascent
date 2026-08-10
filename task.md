# Active Task: 5-Defender Fixture Rotation & Long-Term Diversification Study (GW1–19)

- **Status:** Complete
- **Objective:** Execute exhaustive combinatorial 5-DEF fixture rotation research across GW1–3, GW4–19, GW1–19, and full season; evaluate multi-tier player lineups; produce durable research artifacts and note.
- **Acceptance:** 15,504 5-club combinatorial matrix + player tier simulations generated in data/research/def-fixture-rotation/; research note registered in docs/research/INDEX.md; unit tests in tests/test_def_fixture_rotation.py passing; verify.sh green.
- **Issue/Ticket:** 5-DEF Fixture Diversification `/grill-with-docs`

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** docs/research/def-fixture-rotation/**, data/research/def-fixture-rotation/**, tests/test_def_fixture_rotation.py, docs/research/INDEX.md, docs/agents/current-state.md, task.md
- **Decisions:** Fixed 3 DEF starters (all 5 DEF active on GW1 BB); zero GW1 opponent clashes; GW1 max FDR <= 3.0; multi-tier brackets (Budget £21.5-£22.5m, Anchor £23.5-£24.5m); DEF-RQI and BB-RQI indices; dual reporting for Overall vs PL-Proven.
- **Blocked:** None
- **Next:** Integrate findings into pre-season draft selection and solver constraints.

## Todo
- [x] Grill Q1–Q6 lock (5-DEF rotation study)
- [x] Scenario Grill Q1–Q5 lock (GW1 BB + GW4 WC pre-wildcard)
- [x] Implement 5-club + player tier simulation script with BB1+WC4 module (`run_def_rotation_analysis.py`)
- [x] Generate CSV companions in `data/research/def-fixture-rotation/` (including `def_bb1_wc4_club_matrix.csv` and `def_bb1_wc4_tier_lineups.csv`)
- [x] Update research note `docs/research/def-fixture-rotation/def-fixture-rotation.md`
- [x] Register in `docs/research/INDEX.md`
- [x] Unit tests in `tests/test_def_fixture_rotation.py`
- [x] Delivery gate checks green (152 tests passing)

## Blockers / Notes
- None
