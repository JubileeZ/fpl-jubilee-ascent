# Active Task: explore-candidate-multi-component-ladder

- **Status:** Exit (b) Complete (Scope exhausted across Rungs 1-3, Champion stands)
- **Objective:** Progressively improve non-minute event components (Rung 1 Attacking Core -> Rung 2 Defensive Tuning -> Rung 3 Bonus Calibration) against Champion `def_xg_shrink_challenger`. Screen with Oracle Minutes, gate on dev 2025/26 and confirm 2024/25, and promote winning Candidate.
- **Acceptance:** Frozen Candidate passing Historical Promotion Gate (ADR 0054 formation_xi_regret, dev + confirm boot P >= 0.60, all guardrails) promoted to Champion on user authorization, or scope exhausted with every attempt logged in Candidate Ledger.
- **Issue/Ticket:** User request 2026-10-13 (Component projection improvement on all except mins; De Cuyper set-piece attack & unseeded adaptation)

## Work Packet (SFDBN)

- **Status:** Exit (b) Complete — 6 prototypes evaluated on dev season under ADR 0054 formation regret; all delta negative; Rungs 2-3 confirmed dead in ledger; Champion `def_xg_shrink_challenger` stands
- **Files:**
  - `.agents/work-packets/explore-candidate-multi-component-ladder.md`
  - `docs/research/multi-component-ladder/multi-component-ladder.md`
  - `docs/research/multi-component-ladder/smoke_results.csv`
  - `docs/research/candidate-ledger/candidate_ledger.csv`
  - `docs/research/candidate-ledger/candidate-ledger.md`
  - `docs/research/INDEX.md`
  - `docs/agents/current-state.md`
  - `CONTEXT.md`
- **Decisions:**
  - Active Champion: `def_xg_shrink_challenger` (ADR 0055) stands.
  - Stage 1 Oracle Minutes screen on 2026/27 GW1-6 proved component baselines are structurally sound (bias collapsed from -1.11 to -0.08 pts).
  - Rung 1 Attacking Core evaluated on dev 2025/26 GW1-38: dynamic K relaxation and creativity assist boosting failed promotion gate (delta -0.3875 to -0.8386 pts/GW, 0/3 segments).
  - Rungs 2 & 3: Defensive and bonus core levers are pre-existing Dead levers in candidate_ledger.csv (locked until 2027-09-30 / 2027-10-01).
  - All new attempts logged as Dead in Candidate Ledger (`revisit_after = 2027-10-13`).
- **Blocked:** None
- **Next:** Clean scratch directory, verify test suite, and present final report

## Todo
- [x] Step 0: Ground (arm goal, resolve seasons, inspect Champion)
- [x] Step 1: Screen against Candidate Ledger (exclude Dead levers)
- [x] Step 2: Formulate Lane Plan & declare fixed grids
- [x] Step 3: Implement prototypes and run Stage 1 Oracle Minutes screen
- [x] Step 4: Run smoke evaluations against Champion on dev season
- [x] Step 5: Stack best Lane 1 + best Lane 2 into Candidate (N/A - all Lane 1 and Lane 2 prototypes delta negative)
- [x] Step 6: Evaluate Candidate on confirmation season (N/A - failed dev gate)
- [x] Step 7: Promotion execution (N/A - failed dev gate, Champion stands)
- [x] Step 8: Update Candidate Ledger, research notes, and docs

## Human Queue
- [x] 1. Promotion authorization active: User authorized automated testing and promotion if Candidate passes both seasons. Evaluated; all candidates failed dev season gate; Champion stands per ADR 0054.
- [ ] Acknowledge Dead-lever verdict for multi-component ladder (revisit after 2027-10-13).
