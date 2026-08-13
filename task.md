# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete / Verified
- **Files:** `docs/research/gw1-6-preseason-pipeline/refresh_downstream.py`, `build_expected_stats.py` (`CAREER_INDIVIDUAL_RATES` + `raise_if_draft_on_fallback`), pipeline README / Stage 2–3 / GKP / DEF / ownership notes, `tests/test_expected_stats_blend.py`, `tests/test_gkp_fixture_rotation.py`
- **Decisions:** Two runners — `run_pipeline.py` when roles change (HTTP); `refresh_downstream.py` when rates / new-player packages change. New Draft no-seed player → `CAREER_INDIVIDUAL_RATES` then downstream refresh. Fail-closed if Nailed/Regular on fallback.
- **Blocked:** None.
- **Next:** None for this packet. Next Draft inject: add career package, run `refresh_downstream.py`, restamp Findings tables.
- **Objective:** Re-run ADR-0014 consumers and document the new-player refresh path.
- **Acceptance:**
  - [x] Stage 3 / GKP / DEF / ownership artifacts rebuilt on ADR-0014 rates
  - [x] `refresh_downstream.py` orchestrates Stage 2 → 3 → GKP → DEF → ownership
  - [x] New-player path documented (CAREER_INDIVIDUAL_RATES + fail-closed)
  - [x] Research notes + INDEX restamped; GKP Sources point at pipeline CSVs
  - [x] IPS tagged promoted in GKP; draft-fallback unit tests green
