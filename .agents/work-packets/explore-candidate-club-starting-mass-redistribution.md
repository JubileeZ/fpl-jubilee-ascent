# Active Task: explore-candidate-club-starting-mass-redistribution

- **Status:** Completed (Exit b: scope exhausted, verdict no win)
- **Objective:** Evaluate Model Candidate featuring Club Starting Mass Conservation & Vacancy Redistribution against Champion `club_def_prior_challenger` on dev (2025-26) and confirm (2024-25) seasons via smoke.py.
- **Acceptance:** Frozen Candidate passing Historical Promotion Gate (ADR 0047, ADR 0049, ADR 0054 formation_xi_regret) on dev + confirm seasons, adoption queued in Human Queue — or scope exhausted with attempts recorded in Candidate Ledger.
- **Issue/Ticket:** explore-candidate Scoped mode

## Work Packet (SFDBN)

- **Status:** Completed (Exit b: all 6 variants across 2 lanes failed dev gate; lever recorded as Dead in Candidate Ledger; research note and smoke companion recorded)
- **Files:**
  - `docs/research/club-starting-mass-redistribution/club-starting-mass-redistribution.md`
  - `docs/research/club-starting-mass-redistribution/smoke_results.csv`
  - `docs/research/candidate-ledger/candidate_ledger.csv`
  - `docs/research/candidate-ledger/candidate-ledger.md`
  - `docs/research/INDEX.md`
  - `CONTEXT.md`
  - `.agents/work-packets/explore-candidate-club-starting-mass-redistribution.md`
- **Decisions:**
  - Lane 1 (`pos_cap`): all 3 variants failed dev (best `pos_cap_k90` combined_delta -3.136, 0/3 segs, boot P 0.017; Playable Pool Bias 0.700 vs 0.418; Captaincy Regret 5.264 vs 4.685).
  - Lane 2 (`form_slot`): all 3 variants failed dev (best `form_slot_dnp2` combined_delta -3.615, 0/3 segs, boot P 0.018; `form_slot_pure11` -3.621; `form_slot_base` -4.134; Captaincy Regret 5.38-5.58 vs 4.69; Playable Pool Bias 0.65-0.67 vs 0.43).
  - Diagnostic: Two structural failure modes: (1) 1-DNP false absence causes engine to abandon rested elite assets who start next match, severely hurting captaincy regret; (2) per-club hard 11.0 constraint deflates elite rotating squads (Man City, Chelsea, Arsenal ~12.5 starting mass) while inflating unplayable budget players.
  - Lever moved to Dead in Candidate Ledger with 1-year freeze (`revisit_after = 2027-10-01`).
- **Blocked:** None
- **Next:** Follow-up post-promotion check on Champion `def_xg_shrink_challenger` at 2026-27 GW6+.

## Human Queue
- [x] Acknowledge Dead-lever verdict for Club Starting Mass Redistribution (revisit after 2027-10-01).
- [ ] Post-promotion monitoring for Champion def_xg_shrink_challenger at 2026-27 GW6+.

## Lane Inventory & Results
| Lane | Mechanism | Best Variant | dev combined_delta | segs | boot P | Verdict |
|---|---|---|---|---|---|---|
| `pos_cap` | Position capacity-capped redistribution | `pos_cap_k90` | -3.136 | 0/3 | 0.017 | FAIL |
| `form_slot` | Formation-constrained slot allocation | `form_slot_dnp2` | -3.615 | 0/3 | 0.018 | FAIL |

## Todo
- [x] 0. Ground (arm goal, packet, seasons, champion)
- [x] 1. Ledger screen
- [x] 2. Lane plan
- [x] 3. Dispatch lanes (prototypes.py, audit, smoke.py)
- [x] 4. Audit + verify results
- [x] 5. Iterate to paper win (no pass; all variants failed)
- [x] 6. Build Candidate (skipped, scope exhausted)
- [x] 7. Adopt gate (skipped, no dev winner)
- [x] 8. Record + Exit (research note, smoke_results.csv, candidate ledger, INDEX updated)
