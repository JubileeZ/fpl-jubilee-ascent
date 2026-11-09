# Active Task: explore-candidate-candidate-ideation

- **Status:** In Progress
- **Objective:** `explore-candidate candidate-ideation`: frozen Candidate with verified ADR 0066 evidence and registered confirmation, adoption queued in Human Queue — or scope exhausted with every attempt recorded. Smoke diagnostics alone cannot satisfy gate. State: `.agents/work-packets/explore-candidate-candidate-ideation.md`
- **Acceptance:** All Batch 3 & 4 queue rows (`EXT-14`..`EXT-20`) screened and evaluated against Champion `def_xg_shrink_challenger`; verified results recorded in `smoke_results.csv`, `idea_queue.csv`, `candidate_ledger.csv`, and topic note.
- **Issue/Ticket:** `docs/research/candidate-ideation/idea_queue.csv`

## Work Packet (SFDBN)

- **Status:** In Progress — Batch 5 fixture impact candidates (EXT-21 to EXT-26) ingested into idea_queue.csv as untested (2026-11-09)
- **Files:** `solver/scenarios.py`, `solver/solver.py`, `.agents/skills/ideate-candidate/generate_prompt.py`, `.agents/skills/ideate-candidate/SKILL.md`, `tests/test_ideate_candidate.py`, `docs/research/candidate-ideation/fixtures-ideation-response.md`, `docs/research/candidate-ideation/idea_queue.csv`, `docs/research/candidate-ideation/candidate-ideation.md`, `docs/research/candidate-ideation/candidate_model_ideation_prompt.md`, `docs/research/INDEX.md`
- **Decisions:**
  - Mode: Queue (`docs/research/candidate-ideation/idea_queue.csv`)
  - Champion: `def_xg_shrink_challenger` (`models/def_xg_shrink_challenger.py`)
  - Lineage (Shipped): `def_xg_shrink_challenger`, `club_def_prior_challenger`, `learned_start_challenger`, `multi_feature_assist_challenger`, `face_value_challenger`, `calibrated_matchup_hybrid`, `participation_state_hybrid`
  - Seasons: dev = `2025-26` (GW1-38, seed `2024-25`), confirm = `2024-25` (GW1-38, seed `2023-24`), holdout = `2026-27` (sealed live season)
  - Fixture Impact Ideation (2026-11-09): Added `--focus fixtures` to `generate_prompt.py`; generated Batch 5 (EXT-21 to EXT-26) targeting soft-saturating open-play elasticity, venue dynamics, log-linear CS decay, budget fixture sensitivity, adversary style contrast, and playing duration trim; all 6 passed data catalog validation and dead-lever screen, queued as `untested`.
  - Candidate Status: `EXT-20`, `EXT-08`, and Batch 5 (`EXT-21`..`EXT-26`) remain `untested` in `idea_queue.csv`.
- **Blocked:** None
- **Next:** Run `/explore-candidate` on queued candidates.

## Todo
- [x] 0. Ground (arm goal, packet)
- [x] 1. Ledger screen
- [x] 2. Lane plan
- [ ] 3. Dispatch subagents
- [ ] 4. Audit + verify results
- [ ] 5. Iterate to paper win
- [ ] 6. Build Candidate
- [ ] 7. Adopt gate
- [ ] 8. Record + Exit

## Report

**Verdict:** no win (Queue exhausted across all 20 ideas; Champion `def_xg_shrink_challenger` stands unchanged)
**Lanes:**
- `ext_14` · Continuous Match-Tempo & Counter-Transition Attack Elasticity (`xp_goals`/`xp_assists`) · best `ext_14_a15_b06` · `combined_delta = -0.6045` · `0/3` segs · `boot P = 0.000` (`tier2_oracle_fail`)
- `ext_18` · Starter-Role Conditioning & Set-Piece Share Persistence for Budget Enablers (`xp_goals`) · best `ext_18_k540_g015` · `combined_delta = -0.2407` · `0/3` segs · `boot P = 0.000` (`tier2_oracle_fail`)
- `ext_19` · Opponent Speculative Shot-Volume & Goalkeeper Save-Floor Elasticity (`xp_saves`) · best `ext_19_k900_xi035` · `combined_delta = -0.1279` · `0/3` segs · `boot P = 0.000` (`tier2_oracle_fail`)
- `ext_20` · Endogenous Attacking-Role Stratification & Threat-Adaptive Shrinkage for Out-of-Position Defenders (`xp_goals`) · best `ext_20_t18_k800` · Tier 2 PASS (`oracle_delta = +0.2529`, `boot P = 0.918`) · Tier 3 FAIL (`combined_delta = -0.2153`, `0/3` segs, `boot P = 0.000`)
**Audit:** all 24 prototypes across `ext_14`, `ext_18`, `ext_19`, `ext_20` `AUDIT PASS`, no `LEAKAGE FAIL`
**Ledger:** 4 rows added (`ext_14_*`, `ext_18_*`, `ext_19_*`, `ext_20_*`); `EXT-15` marked `dead-match` against Row 81 (`2027-09-30`)

## Human Queue
- [x] 1. Override Dead row `Defcon venue and opposition pressure scaling` (`revisit_after = 2027-09-30`) to evaluate `EXT-15` (Territorial Possession-Tilt & Deep-Block Defcon Elasticity)? User resolution: No (keep Dead lock intact). Evidence: `docs/research/candidate-ledger/candidate_ledger.csv` Row 81, `docs/research/candidate-ideation/ideas/EXT-15-territorial-possession-tilt-deep-block-defcon-elasticity.md`.
- [x] 2. Override Dead row `Start vs sub attack intensity` (`revisit_after = 2027-09-29`) to evaluate `EXT-16` (Co-Starter Playmaker Gravity & Non-Zero-Sum Space-Creation Synergy)? User resolution: No (keep Dead lock intact). Evidence: `docs/research/candidate-ideation/ideas/EXT-16-co-starter-playmaker-gravity-non-zero-sum-space-creation-synergy.md`.
- [x] 3. Override Dead row `Learned participation variants` / `Schedule-congestion start shift` (`revisit_after = 2027-09-28` / `2027-09-30`) to evaluate `EXT-17` (Position-Conditioned Exponential Micro-Cycle Fatigue & Ironman Stamina Resistance)? User resolution: No (keep Dead lock intact). Evidence: `docs/research/candidate-ideation/ideas/EXT-17-position-conditioned-exponential-micro-cycle-fatigue-ironman-stamina-resistance.md`.

## Next Batch Queue
- [ ] Ingest fresh ideation batch via `/ideate-candidate` (queue exhausted across all 19 candidates in `candidate-ideation/idea_queue.csv`).
