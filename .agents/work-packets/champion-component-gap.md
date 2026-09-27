# Active Task: Challenger beats Champion (goals then defence link)

- **Status:** #130 closed; frontier #131 task (unclaimed)
- **Objective:** Flip Champion via goals + Poisson defence-link + bonus-arm Candidate on 2025-26 Historical Promotion Gate
- **Acceptance:** Map Destination met; soft pre-gate PASS; Blended gate PASS + `--apply`
- **Issue/Ticket:** Map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110) · **Bind:** [#131 Champion dry-run/--apply](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/131)

## Work Packet (SFDBN)

- **Status:** #111–#130 closed. **#131** frontier (dry-run/`--apply`).
- **Files:** `soft_admit_130.py`; `soft_pre_gate_130.json`; `admission_race_130.json`; `config/model_selection.json` slate = `defence_link_challenger` + `bonus_arm_challenger`.
- **Decisions:** #130 soft 4/4 PASS (bonus via bias↓ vs Champion); admission beat-one → replace `participation_state_hybrid`.
- **Blocked:** none; `--apply` gated on #131 dry-run PASS
- **Next:** Claim #131 → `commands.evaluate_model_promotion` dry-run for `bonus_arm_challenger`

## Todo
- [x] #126–#130 stub / levers / soft-bar / calibrate / soft+admit
- [ ] #131 Dry-run / `--apply`

## Blockers / Notes
- Handoff: `challenger-beats-champion` → map #110 / #131
- Risk: `bonus_arm` lost Blended primary to parent `defence_link` (Δ −0.57, 1/3 segs) → Champion flip unlikely
