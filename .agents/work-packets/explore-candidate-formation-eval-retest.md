# Active Task: explore-candidate formation-eval-retest

- **Status:** Exit (a) — Candidate def_xg_shrink_challenger PASS dev + confirm, adoption queued
- **Objective:** Screen previously tested dev winners that failed confirmation or stalled before adoption under the new ADR 0054 legal formation XI promotion gate
- **Acceptance:** Full-season dev gate evaluation on 2025-26 vs Champion club_def_prior_challenger; confirm run for any dev winner; ledger updated; report delivered
- **Issue/Ticket:** User request to /explore-candidate past dev winners under updated promo eval

## Run state

- **Mode:** Scoped · scope: dev winners re-evaluated under ADR 0054 gate · slug: formation-eval-retest
- **Seasons:** dev 2025-26 GW1-38 seed 2024-25 · confirm 2024-25 GW1-38 no seed · holdout 2026-27 sealed
- **Champion:** club_def_prior_challenger (ADR 0051)
- **Gate:** ADR 0054 formation_xi_regret primary, Playable-Pool MAE/bias, Captaincy Regret tol 0.15, xMins tol 1.01, Spearman tol -0.005, boot P >= 0.60, segs >= 2/3
- **Step:** 8 done (Exit (a))
- **Scratch:** .tmp/agent/explore-candidate/ deleted

## Scorecard

| Candidate Model | Lever | Dev 2025-26 | Confirm 2024-25 | Gate Verdict |
|---|---|---|---|---|
| def_xg_shrink_challenger | ATK-04: DEF xG rate shrink K=2400 | PASS (+0.7929, 3/3, P 0.944) | PASS (+0.5941, 2/3, P 0.863) | **CONFIRM PASS** → Adoption queued |
| cs_exposure_challenger | DEF-02: CS exposure 60+ starts (m60=85, K=4) | PASS (+0.3829, 2/3, P 0.901) | FAIL (-0.2162, 1/3, P 0.189) | Confirm FAIL |
| asymmetric_finishing_challenger | Asymmetric finishing shrinkage (Kpos 1500, Kneg 3000) | PASS (+0.1028, 2/3, P 0.644) | FAIL (-0.1553, 1/3, P 0.296) | Confirm FAIL |
| schedule_congestion_challenger | MIN-07: Congestion logit shift -0.2 | FAIL (+0.1137, 1/3, P 0.623) | — | Dev FAIL |

## Work Packet (SFDBN)

- **Status:** Exit (a); def_xg_shrink_challenger ready for promotion
- **Files:** docs/research/formation-eval-retest/*, .agents/work-packets/explore-candidate-formation-eval-retest.md
- **Decisions:** Re-evaluated past dev winners under ADR 0054 formation_xi_regret. def_xg_shrink_challenger passes both seasons convincingly.
- **Blocked:** None
- **Next:** Await user decision on Human Queue promotion bundle for def_xg_shrink_challenger

## Human Queue

- [ ] Post-promotion holdout check (ADR 0047, once per Champion) when 2026-27 GW6+ finished: `uv run python -m commands.evaluate_model_promotion --data_dir data/archive/2026-27/processed --seed_season 2025-26 --gw_range 6-<last finished>` (Champion `def_xg_shrink_challenger` vs slate). FAIL -> revert to `club_def_prior_challenger` on user's words. Default: wait.
