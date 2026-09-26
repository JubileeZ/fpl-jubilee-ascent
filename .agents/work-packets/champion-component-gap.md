# Active Task: Challenger beats Champion (goals then defence link)

- **Status:** #129 closed; frontier #130 task (unclaimed)
- **Objective:** Flip Champion via goals + Poisson defence-link + bonus-arm Candidate on 2025-26 Historical Promotion Gate
- **Acceptance:** Map Destination met; soft pre-gate PASS; Blended gate PASS + `--apply`
- **Issue/Ticket:** Map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110) · **Bind:** [#130 Soft pre-gate + admission race](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/130)

## Work Packet (SFDBN)

- **Status:** #111–#129 closed. **#130** frontier (soft+admit). #131←#130.
- **Files:** `bonus_arm_challenger` wired; `_XBPS_WEIGHTS`=(0.1,96,48,48,24,8) `_BONUS_SOFTMAX_T`=8.0; note `calibrate-bonus-arm-129.md`.
- **Decisions:** #128 = bonus soft bias/τ and/or `|mse_share|`↓ on `mins_60`/`ALL`; #129 = event k=4 + T=8 (τ not cleared on bias).
- **Blocked:** apply until #130/#131
- **Next:** Claim #130 → soft checklist + admission race

## Todo
- [x] #126–#129 stub / levers / soft-bar / wire+calibrate
- [ ] **#130** Soft + admission
- [ ] #131 Dry-run / `--apply`

## Blockers / Notes
- Handoff: `challenger-beats-champion` → map #110 / #130
- Soft risk: mins_60 bonus bias ≈ −0.067 (outside τ); need `|mse_share|`↓ half of and/or
