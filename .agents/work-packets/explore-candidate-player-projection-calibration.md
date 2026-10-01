# Active Task: explore-candidate-player-projection-calibration

- **Status:** In Progress
- **Objective:** Evaluate calibration and de-biasing mechanisms (bonus pool saturation with fixture conservation, minutes clamping / sharp slope removal, natural rates) against Champion `def_xg_shrink_challenger` on dev (2025-26) and confirm (2024-25) seasons via `smoke.py`.
- **Acceptance:** Frozen Candidate passing Historical Promotion Gate on both seasons with adoption queued in Human Queue, or scope exhausted with every attempt logged in Candidate Ledger.
- **Issue/Ticket:** User request 2026-10-01 (Haaland over-projection calibration)

## Work Packet (SFDBN)

- **Status:** Scope exhausted, every attempt logged in Candidate Ledger (Exit b)
- **Files:**
  - `models/calibrated_rate_challenger.py`
  - `tests/test_calibrated_rate_challenger.py`
  - `docs/model_name.md`
  - `docs/research/player-projection-calibration/player-projection-calibration.md`
  - `docs/research/player-projection-calibration/smoke_results.csv`
  - `docs/research/player-projection-calibration/candidate_gate.csv`
  - `docs/research/candidate-ledger/candidate_ledger.csv`
  - `docs/research/candidate-ledger/candidate-ledger.md`
  - `docs/research/INDEX.md`
  - `docs/agents/current-state.md`
- **Decisions:**
  - Champion `def_xg_shrink_challenger` stands as Model Champion.
  - Lane 1 (`lane_bon`): 5 variants negative on dev (−0.16 to −0.38 delta).
  - Lane 2 (`lane_att`): `calibrated_rate_challenger` (natural rates + 90 min clamp) PASSED dev 2025-26 (+0.355 2/3 segs, boot P 0.901) but FAILED confirm 2024-25 (−0.449 1/3 segs, boot P 0.237).
  - Levers marked Dead in Candidate Ledger (`revisit_after = 2027-10-01`).
- **Blocked:** None
- **Next:** User review of calibration trade-off in Human Queue

## Results Summary
- `lane_bon` (bonus saturation): all 5 variants negative (−0.16 to −0.38).
- `lane_att` (attack de-biasing):
  - `att2_nosharp_notilt`: delta +0.6764, Captaincy Regret fail (4.997 vs 4.831 + 0.15).
  - `att2_nosharp_notrim_notilt` (`calibrated_rate_challenger`):
    - Dev (2025-26): PASS (+0.3549, 2/3 segs, boot P 0.901, all guardrails passed).
    - Confirm (2024-25): FAIL (−0.4488, 1/3 segs, boot P 0.237).

## Todo
- [x] Step 0: Ground (arm goal, resolve seasons, inspect Champion)
- [x] Step 1: Screen against Candidate Ledger (exclude Dead levers)
- [x] Step 2: Formulate Lane Plan & declare fixed grids
- [x] Step 3: Dispatch prototypes and run smoke tests
- [x] Step 4: Audit prototypes and verify dev results
- [x] Step 5: Stack protocol / paper win selection (`att2_nosharp_notrim_notilt`)
- [x] Step 6: Build Candidate module and tests (`models/calibrated_rate_challenger.py`)
- [x] Step 7: Confirmation season gate (Confirm FAIL: -0.449)
- [x] Step 8: Candidate Ledger update and final report

## Human Queue
- [ ] 1. Note calibration trade-off: Champion's top-end slope (+25%) inflates Haaland to ~9.5 pts, but removing it hurts haul capture in 2024-25 (−0.449 pts/GW). Keep Champion or revisit?
