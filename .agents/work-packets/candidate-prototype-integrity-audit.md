# Active Task: Candidate Prototype Integrity Audit & Idea Revival

- **Status:** In Progress
- **Objective:** Rigorous audit of candidate prototypes (Batches 1–6, EXT-01 to EXT-31) and evaluation harness mechanics; formulate exact fix plans and retest plans for flawed prototypes; revive compromised candidate ideas in idea_queue.csv without executing retests yet.
- **Acceptance:** Full audit report categorizing all 31 candidate ideas as LEGIT or NEEDS RETEST / FIX; exact root cause, fix plan, and retest plan for each flawed idea; idea_queue.csv updated with revived status; verify.sh passes.
- **Issue/Ticket:** Candidate Ideation Integrity Audit

## Work Packet (SFDBN)

- **Status:** In Progress — Phase 1 retests active: EXT-23 patched, two-axis reviewed, and retested (dev FAIL); EXT-24 next.
- **Files:** `docs/research/candidate-ideation/idea_queue.csv`, `docs/research/candidate-ideation/prototypes/ext_23/prototypes.py`, `docs/research/candidate-ideation/smoke_results.csv`, `docs/research/candidate-ledger/candidate_ledger.csv`, `.agents/work-packets/candidate-prototype-integrity-audit.md`
- **Decisions:** 
  1. Revived EXT-21, EXT-22, EXT-23, EXT-24, EXT-25, EXT-27, EXT-28, and EXT-31 in idea_queue.csv due to verified prototype implementation defects.
  2. EXT-23: Implemented Empirical Bayes club attacking rates with K_cs shrinkage, overrode _apply_hard_fixture_defence to eliminate double-penalty, passed parallel Spec/Math and Standards code-reviews, and completed smoke retest on Dev 2025-26. 5/6 passed Tier 2, best ext_23_a20_k4 delta +0.2338, failed Tier 3 on early_mid regression (-0.693 < -0.15). Logged diagnostic fail in idea_queue.csv with open status in candidate_ledger.csv.
- **Blocked:** None
- **Next:** Implement prototype bug-fixes and run two-axis review for EXT-24 (Price-Conditioned Fixture Sensitivity for Budget MID/FWD).

## Todo
- [x] Audit evaluation harness smoke.py and Tier 1/2/3 gating mechanics
- [x] Audit Batches 1–4 prototypes (EXT-05 through EXT-20)
- [x] Audit Batch 5 prototypes (EXT-21 through EXT-25)
- [x] Audit Batch 6 prototypes (EXT-26 through EXT-31)
- [x] Revive compromised ideas in idea_queue.csv
- [x] Formulate comprehensive fix plan and retest plan per revived idea
- [ ] Implement prototype patches for revived ideas upon user authorization
  - [x] EXT-23: Patched, two-axis reviewed (PASS), and retested on Dev 2025-26
  - [ ] EXT-24: Implement budget MID/FWD event components hook
  - [ ] EXT-27: Correct home advantage sign inversion and venue multiplier
  - [ ] EXT-21: Isolate penalty xG from open-play saturation
  - [ ] EXT-22: Wire K_venue Empirical Bayes shrinkage
  - [ ] EXT-25: Aggregate concession modality and balance xG/xA adjustments
  - [ ] EXT-28: Fix assist history and fixture de-biasing
  - [ ] EXT-31: Attenuate additive matchup share addons across GW2-38
- [ ] Execute smoke retests for remaining revived ideas across Dev 2025-26

## Blockers / Notes
- Do not execute retest runs until user authorizes bug-fix patches.
