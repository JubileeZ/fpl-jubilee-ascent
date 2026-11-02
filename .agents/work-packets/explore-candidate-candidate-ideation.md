# Active Task: explore-candidate (candidate-ideation queue)

- **Status:** In Progress
- **Objective:** Evaluate remaining Open/untested rows (`EXT-08`, `EXT-12`) in `docs/research/candidate-ideation/idea_queue.csv` against active Champion `def_xg_shrink_challenger` under ADR 0064 / ADR 0066 diagnostic & promotion standards.
- **Acceptance:** Frozen Candidate with verified ADR 0066 evidence and registered confirmation queued in Human Queue — or scope exhausted with every attempt recorded in `candidate_ledger.csv`, `idea_queue.csv`, `smoke_results.csv`, and topic note.
- **Issue/Ticket:** `explore-candidate-candidate-ideation`

## Work Packet (SFDBN)

- **Status:** Complete (Exit b: Queue exhausted, all 13 ideation rows evaluated, screened, or blocked; Model Champion `def_xg_shrink_challenger` stands unchanged)
- **Files:** `.agents/work-packets/explore-candidate-candidate-ideation.md`, `docs/research/candidate-ideation/idea_queue.csv`, `docs/research/candidate-ideation/smoke_results.csv`, `docs/research/candidate-ledger/candidate_ledger.csv`, `docs/research/candidate-ledger/candidate-ledger.md`, `docs/research/candidate-ideation/candidate-ideation.md`, `tests/test_injury_triage.py`
- **Decisions:**
  - Mode: Queue (`docs/research/candidate-ideation/idea_queue.csv`, slug `candidate-ideation`).
  - Seasons: `dev` = `2025-26` (`GW1-38`, seed `2024-25`); `confirm` = `2024-25` (`GW1-38`, seed `2023-24`); `holdout` = `2026-27` (sealed).
  - Active Champion: `def_xg_shrink_challenger` (`models/def_xg_shrink_challenger.py`).
  - Step 1 Ledger Screen:
    - `EXT-01`, `EXT-02`, `EXT-03`, `EXT-04`, `EXT-06`: dead-match.
    - `EXT-05`, `EXT-07`, `EXT-09`, `EXT-11`: dev FAIL (Dead).
    - `EXT-10`: blocked on dead `EXT-07` and unavailable seed hazard summaries.
    - `EXT-13`: blocked on historical schedule provenance.
    - `EXT-08` & `EXT-12`: Open, unblocked by subclassing `DefXgShrinkChallengerModel`.
  - Step 2-4 Batch 1 Evaluation on `def_xg_shrink_challenger`:
    - `ext_08`: All 4 variants (`ext_08_k2`, `ext_08_k4`, `ext_08_k8`, `ext_08_k16`) evaluated; AUDIT PASS, no leakage; all 4 failed Tier 2 Oracle Event Gate (`tier2_oracle_fail`). Best variants `ext_08_k8` / `k16` produced `combined_delta = +0.0280`, `segs = 0/3`, `boot_p_gt0 = 0.000 < 0.65`.
    - `ext_12`: All 4 variants (`ext_12_h48_phi05`, `ext_12_h48_phi10`, `ext_12_h24_phi05`, `ext_12_h24_phi10`) evaluated; AUDIT PASS, no leakage; all 4 failed Tier 2 Oracle Event Gate (`tier2_oracle_fail`) with `combined_delta = +0.0000`, `segs = 0/3`, `boot_p_gt0 = 0.000 < 0.65`.
  - Step 5-8 Queue Exhaustion & Ledger Sync:
    - No variant passed the dev gate (`pass=True`).
    - Queue exhausted; `EXT-08` and `EXT-12` updated to `fail` in `idea_queue.csv`.
    - Logged dead in `candidate_ledger.csv` and `candidate-ledger.md` until `2027-11-01`.
    - Preserved evaluated prototype sources under `docs/research/candidate-ideation/prototypes/`.
    - Champion `def_xg_shrink_challenger` unchanged. Exit (b).
  - Test Suite Hygiene:
    - Isolated `tests/test_injury_triage.py::test_build_broad_pool_shield` using hermetic `tmp_path` fixture tables to decouple unit assertions from live API parquet mutation.
- **Blocked:** None for Batch 1. Remaining queue rows `EXT-10` and `EXT-13` retained in Human Queue.
- **Next:** User to review Human Queue or generate fresh ideation proposals via `ideate-candidate`.

## Todo
- [x] 0. Ground (arm goal, packet)
- [x] 1. Ledger screen
- [x] 2. Lane plan
- [x] 3. Dispatch subagents (`ext_08`, `ext_12`)
- [x] 4. Audit + verify results
- [x] 5. Iterate to paper win (no win)
- [x] 8. Record + Exit (Exit b)

## Report

**Verdict:** no win (Model Champion `def_xg_shrink_challenger` stands unchanged)
**Lanes:**
- `ext_08` · Joint xGI intensity & allocation (Beta-Gamma coupling) · `ext_08_k8` / `ext_08_k16` · `combined_delta = +0.0280` · `segs = 0/3` · `boot_p_gt0 = 0.000` (`tier2_oracle_fail`)
- `ext_12` · Sequential opportunity change detection (Tweedie filter) · `ext_12_h48_phi05` · `combined_delta = +0.0000` · `segs = 0/3` · `boot_p_gt0 = 0.000` (`tier2_oracle_fail`)
**Audit:** all prototypes AUDIT PASS, no LEAKAGE FAIL
**Ledger:** `EXT-08` and `EXT-12` updated from `open` to `dead` (`revisit_after = 2027-11-01`) in `candidate_ledger.csv` and `candidate-ledger.md`
**Human Queue:** 2 open items below retained for user decision

## Human Queue
- [x] 1. **EXT-10 (`Full-Duration Survival Likelihood for Starting Players`)**: User resolved: Keep blocked (EXT-07 prerequisite is Dead; prior-season seed hazard summaries absent).
- [x] 2. **EXT-13 (`Habit-Adjusted Cumulative Playing Dose`)**: User resolved: Keep blocked (historical schedule provenance unresolved).
- [ ] 3. **Next ideation cycle**: Queue is fully exhausted. User may run `ideate-candidate` to generate and ingest fresh candidate briefs when ready.
