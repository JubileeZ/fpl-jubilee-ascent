# Active Task: Challenger beats Champion (goals then defence link)

- **Status:** Flip Candidate on Comparison Slate; frontier = soft-pre-gate grill #120
- **Objective:** Flip Champion via goals + Poisson defence-link Candidate on 2025-26 Historical Promotion Gate
- **Acceptance:** Map Destination met; soft pre-gate companion improve before `--apply`
- **Issue/Ticket:** Map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110) · **Bind next:** [#120 Settle conceded soft-pre-gate bar](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/120)

## Work Packet (SFDBN)

- **Status:** #111–#119 closed. Frontier **#120** (grilling · unclaimed).
- **Files:** Slate `config/model_selection.json` = Champion `hold_chase_challenger` + Candidates `participation_state_hybrid`, `defence_link_challenger`; race `admission_race_119.json`; soft `soft_pre_gate_119.json`
- **Decisions:** Admission #119 — beat both; replace `calibrated_matchup_hybrid`. Soft pre-gate: goals+CS PASS; conceded FAIL (`|mse_share|` ↑) → no Champion `--apply`
- **Blocked:** Champion `--apply` until #120 settles conceded soft bar
- **Next:** Claim #120 (HITL grill) → then Champion dry-run/`--apply` Task

## Todo
- [x] Component-gap diagnosis + Eval canon
- [x] Decision tickets #111–#115, #117
- [x] #116 `goals_path_challenger`
- [x] #118 `defence_link_challenger`
- [x] #119 admission race (seat swap; no Champion apply)
- [ ] **#120** settle conceded soft-pre-gate bar
- [ ] Champion dry-run / `--apply` (after #120)

## Blockers / Notes
- Handoff: `challenger-beats-champion` → map #110 / task #120
- Both seats tied on decision_regret primary; MAE tie-break → displace calibrated
