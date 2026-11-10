# Active Task: Candidate Prototype Integrity Audit & Idea Revival

- **Status:** In Progress
- **Objective:** Rigorous audit of candidate prototypes (Batches 1–6, EXT-01 to EXT-31) and evaluation harness mechanics; formulate exact fix plans and retest plans for flawed prototypes; revive compromised candidate ideas in idea_queue.csv without executing retests yet.
- **Acceptance:** Full audit report categorizing all 31 candidate ideas as LEGIT or NEEDS RETEST / FIX; exact root cause, fix plan, and retest plan for each flawed idea; idea_queue.csv updated with revived status; verify.sh passes.
- **Issue/Ticket:** Candidate Ideation Integrity Audit

## Work Packet (SFDBN)

- **Status:** In Progress — Phase 2 complete (EXT-21, EXT-22, EXT-25 all patched, reviewed, and retested); Phase 3 active: EXT-28 next.
- **Files:** `docs/research/candidate-ideation/idea_queue.csv`, `docs/research/candidate-ideation/prototypes/ext_25/prototypes.py`, `docs/research/candidate-ideation/smoke_results.csv`, `docs/research/candidate-ledger/candidate_ledger.csv`, `.agents/work-packets/candidate-prototype-integrity-audit.md`
- **Decisions:** 
  1. Revived EXT-21, EXT-22, EXT-23, EXT-24, EXT-25, EXT-27, EXT-28, and EXT-31 in idea_queue.csv due to verified prototype implementation defects.
  2. EXT-23: Implemented Empirical Bayes club attacking rates with K_cs shrinkage, overrode _apply_hard_fixture_defence to eliminate double-penalty, passed parallel Spec/Math and Standards code-reviews, and completed smoke retest on Dev 2025-26. 5/6 passed Tier 2, best ext_23_a20_k4 delta +0.2338, failed Tier 3 on early_mid regression (-0.693 < -0.15). Logged diagnostic fail in idea_queue.csv with open status in candidate_ledger.csv.
  3. EXT-24: Implemented budget MID/FWD fixture multiplier inside _project_event_components preserving assist signals and isolating HoldChase minutes thresholds. Passed parallel Spec/Math and Standards reviews. Completed smoke retest on Dev 2025-26: all 6 variants failed Tier 2 Oracle Event Gate (best ext_24_g20_c60 delta -0.0282, boot P 0.176). Logged diagnostic fail in idea_queue.csv with open status in candidate_ledger.csv.
  4. EXT-27: Fixed severe sign-inversion defect by eliminating buggy divisors, implemented point-in-time empirical home advantage estimation with h0=0.08 prior, and preserved mean scaling. Passed parallel Spec/Math and Standards reviews. Completed smoke retest on Dev 2025-26: all 6 variants failed Tier 2 Oracle Event Gate (best ext_27_e100_all delta -0.0163, boot P 0.389). Logged diagnostic fail in idea_queue.csv with open status in candidate_ledger.csv.
  5. EXT-21: Implemented empirical opponent xGC with K=4.0 EB shrinkage, isolated primary penalty takers (0.15 xG/90 unscaled), and moved saturating tanh factor inside _project_event_components. Passed parallel Spec/Math and Standards reviews. Completed smoke retest on Dev 2025-26: all 6 variants failed Tier 2 Oracle Event Gate (best ext_21_g10_k08 delta +0.3180, boot P 0.545 < 0.65). Logged diagnostic fail in idea_queue.csv with open status in candidate_ledger.csv.
  6. EXT-22: Wired K_venue Empirical Bayes shrinkage on completed appearances, preserved assist rates in _project_event_components, and preserved HoldChase minutes logic. Passed parallel Spec/Math and Standards reviews. Completed smoke retest on Dev 2025-26: all 6 variants failed Tier 2 Oracle Event Gate (best ext_22_b06_k4 delta -0.4921, boot P 0.169). Logged diagnostic fail in idea_queue.csv with open status in candidate_ledger.csv.
  7. EXT-25: Implemented empirical opponent concession modality from threat and creativity histories with K_modality EB shrinkage, corrected creator style alignment symmetry, and preserved assist rates in _project_event_components. Passed parallel Spec/Math and Standards reviews. Completed smoke retest on Dev 2025-26: all 6 variants failed Tier 2 Oracle Event Gate (delta +0.0000, boot P 0.000). Logged diagnostic fail in idea_queue.csv with open status in candidate_ledger.csv.
- **Blocked:** None
- **Next:** Advance to Phase 3: Implement prototype bug-fixes and run two-axis review for EXT-28 (Schedule-Neutralized Attack Baselines).

## Todo
- [x] Audit evaluation harness smoke.py and Tier 1/2/3 gating mechanics
- [x] Audit Batches 1–4 prototypes (EXT-05 through EXT-20)
- [x] Audit Batch 5 prototypes (EXT-21 through EXT-25)
- [x] Audit Batch 6 prototypes (EXT-26 through EXT-31)
- [x] Revive compromised ideas in idea_queue.csv
- [x] Formulate comprehensive fix plan and retest plan per revived idea
- [ ] Implement prototype patches for revived ideas upon user authorization
  - [x] EXT-23: Patched, two-axis reviewed (PASS), and retested on Dev 2025-26
  - [x] EXT-24: Patched, two-axis reviewed (PASS), and retested on Dev 2025-26
  - [x] EXT-27: Patched, two-axis reviewed (PASS), and retested on Dev 2025-26
  - [x] EXT-21: Patched, two-axis reviewed (PASS), and retested on Dev 2025-26
  - [x] EXT-22: Patched, two-axis reviewed (PASS), and retested on Dev 2025-26
  - [x] EXT-25: Patched, two-axis reviewed (PASS), and retested on Dev 2025-26
  - [ ] EXT-28: Fix assist history and fixture de-biasing
  - [ ] EXT-31: Attenuate additive matchup share addons across GW2-38
- [ ] Execute smoke retests for remaining revived ideas across Dev 2025-26
  - [ ] EXT-28: Fix assist history and fixture de-biasing
  - [ ] EXT-31: Attenuate additive matchup share addons across GW2-38
- [ ] Execute smoke retests for remaining revived ideas across Dev 2025-26
  - [ ] EXT-25: Aggregate concession modality and balance xG/xA adjustments
  - [ ] EXT-28: Fix assist history and fixture de-biasing
  - [ ] EXT-31: Attenuate additive matchup share addons across GW2-38
- [ ] Execute smoke retests for remaining revived ideas across Dev 2025-26
  - [ ] EXT-22: Wire K_venue Empirical Bayes shrinkage
  - [ ] EXT-25: Aggregate concession modality and balance xG/xA adjustments
  - [ ] EXT-28: Fix assist history and fixture de-biasing
  - [ ] EXT-31: Attenuate additive matchup share addons across GW2-38
- [ ] Execute smoke retests for remaining revived ideas across Dev 2025-26
  - [ ] EXT-21: Isolate penalty xG from open-play saturation
  - [ ] EXT-22: Wire K_venue Empirical Bayes shrinkage
  - [ ] EXT-25: Aggregate concession modality and balance xG/xA adjustments
  - [ ] EXT-28: Fix assist history and fixture de-biasing
  - [ ] EXT-31: Attenuate additive matchup share addons across GW2-38
- [ ] Execute smoke retests for remaining revived ideas across Dev 2025-26

## Blockers / Notes
- Do not execute retest runs until user authorizes bug-fix patches.
