# Active Task: Candidate Prototype Integrity Audit & Idea Revival

- **Status:** In Progress
- **Objective:** Rigorous audit of candidate prototypes (Batches 1–6, EXT-01 to EXT-31) and evaluation harness mechanics; formulate exact fix plans and retest plans for flawed prototypes; revive compromised candidate ideas in idea_queue.csv without executing retests yet.
- **Acceptance:** Full audit report categorizing all 31 candidate ideas as LEGIT or NEEDS RETEST / FIX; exact root cause, fix plan, and retest plan for each flawed idea; idea_queue.csv updated with revived status; verify.sh passes.
- **Issue/Ticket:** Candidate Ideation Integrity Audit

## Work Packet (SFDBN)

- **Status:** Audit completed across all 31 proposals. 8 ideas revived in idea_queue.csv with fix and retest plans documented.
- **Files:** `docs/research/candidate-ideation/idea_queue.csv`, `.agents/work-packets/candidate-prototype-integrity-audit.md`
- **Decisions:** 
  1. Revived EXT-21, EXT-22, EXT-23, EXT-24, EXT-25, EXT-27, EXT-28, and EXT-31 in idea_queue.csv due to verified prototype implementation defects (omitted penalty isolation, unused EB parameters, silent assist overwrites in MultiFeatureAssistChallenger, home advantage sign inversions, and GW2-38 matchup share multiplier no-ops).
  2. Confirmed EXT-01..04, EXT-06, EXT-15..17, EXT-29, and EXT-30 as LEGIT dead-matches.
  3. Confirmed EXT-05, EXT-07..09, EXT-11..12, EXT-14, EXT-18..20, and EXT-26 as LEGIT evaluations (flawless prototype math or genuine statistical failures).
  4. Retests deferred pending user confirmation and prototype patch implementation.
- **Blocked:** None
- **Next:** Await user direction to implement prototype bug fixes and trigger retests.

## Todo
- [x] Audit evaluation harness smoke.py and Tier 1/2/3 gating mechanics
- [x] Audit Batches 1–4 prototypes (EXT-05 through EXT-20)
- [x] Audit Batch 5 prototypes (EXT-21 through EXT-25)
- [x] Audit Batch 6 prototypes (EXT-26 through EXT-31)
- [x] Revive compromised ideas in idea_queue.csv
- [x] Formulate comprehensive fix plan and retest plan per revived idea
- [ ] Implement prototype patches for revived ideas upon user authorization
- [ ] Execute smoke retests for revived ideas across Dev 2025-26

## Blockers / Notes
- Do not execute retest runs until user authorizes bug-fix patches.
