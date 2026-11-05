# Active Task: explore-candidate-candidate-ideation

- **Status:** In Progress
- **Objective:** `explore-candidate candidate-ideation`: frozen Candidate with verified ADR 0066 evidence and registered confirmation, adoption queued in Human Queue — or scope exhausted with every attempt recorded. Smoke diagnostics alone cannot satisfy gate. State: `.agents/work-packets/explore-candidate-candidate-ideation.md`
- **Acceptance:** All Batch 3 queue rows (`EXT-14`..`EXT-19`) screened and evaluated against Champion `def_xg_shrink_challenger`; verified results recorded in `smoke_results.csv`, `idea_queue.csv`, `candidate_ledger.csv`, and topic note.
- **Issue/Ticket:** `docs/research/candidate-ideation/idea_queue.csv`

## Work Packet (SFDBN)

- **Status:** Step 8 — Exit (b): Queue exhausted (no win); human resolution confirmed (keep Dead locks intact, Champion unchanged)
- **Files:** `docs/research/candidate-ideation/idea_queue.csv`, `docs/research/candidate-ideation/smoke_results.csv`, `docs/research/candidate-ideation/candidate-ideation.md`, `docs/research/candidate-ledger/candidate_ledger.csv`, `docs/research/candidate-ledger/candidate-ledger.md`, `docs/research/backtesting-promotion-foundation/legacy_verdicts_audit.csv`, `docs/research/backtesting-promotion-foundation/legacy_verdicts_audit.md`, `commands/audit_legacy_verdicts.py`, `tests/test_audit_legacy_verdicts.py`
- **Decisions:**
  - Mode: Queue (`docs/research/candidate-ideation/idea_queue.csv`)
  - Champion: `def_xg_shrink_challenger` (`models/def_xg_shrink_challenger.py`)
  - Lineage (Shipped): `def_xg_shrink_challenger`, `club_def_prior_challenger`, `learned_start_challenger`, `multi_feature_assist_challenger`, `face_value_challenger`, `calibrated_matchup_hybrid`, `participation_state_hybrid`
  - Seasons: dev = `2025-26` (GW1-38, seed `2024-25`), confirm = `2024-25` (GW1-38, seed `2023-24`), holdout = `2026-27` (sealed live season)
  - Ledger screen (Step 1):
    - `EXT-15` (Territorial Possession-Tilt & Deep-Block Defcon Elasticity): Dead match vs Ledger Row 81 (`Defcon venue and opposition pressure scaling`, `revisit_after = 2027-09-30`) → user resolved: keep Dead lock intact, marked `dead-match`
    - `EXT-16` (Co-Starter Playmaker Gravity): Dead match (`revisit_after = 2027-09-29`) → user resolved: keep Dead lock intact
    - `EXT-17` (Micro-Cycle Fatigue & Ironman Stamina): Dead match (`revisit_after = 2027-09-28` / `2027-09-30`) → user resolved: keep Dead lock intact
  - Verified Smoke Results (Step 4 & Step 5):
    - Lane `ext_14` (`EXT-14`: Continuous Match-Tempo & Counter-Transition Attack Elasticity, 6 variants): `AUDIT PASS`, 0/6 passed Tier 2 Oracle Event Gate; best `ext_14_a15_b06` (`combined_delta = -0.6045`, `segs = 0/3`, `boot_p_gt0 = 0.000`). Logged Dead until `2027-11-05`.
    - Lane `ext_18` (`EXT-18`: Starter-Role Conditioning & Set-Piece Share Persistence for Budget Enablers, 6 variants): `AUDIT PASS`, 0/6 passed Tier 2 Oracle Event Gate; best `ext_18_k540_g015` (`combined_delta = -0.2407`, `segs = 0/3`, `boot_p_gt0 = 0.000`). Logged Dead until `2027-11-05`.
    - Lane `ext_19` (`EXT-19`: Opponent Speculative Shot-Volume & Goalkeeper Save-Floor Elasticity, 6 variants): `AUDIT PASS`, 0/6 passed Tier 2 Oracle Event Gate; best `ext_19_k900_xi035` (`combined_delta = -0.1279`, `segs = 0/3`, `boot_p_gt0 = 0.000`). Logged Dead until `2027-11-05`.
- **Blocked:** None
- **Next:** Ingest fresh candidate ideas via `/ideate-candidate`.

## Todo
- [x] 0. Ground (arm goal, packet)
- [x] 1. Ledger screen
- [x] 2. Lane plan
- [x] 3. Dispatch subagents
- [x] 4. Audit + verify results
- [x] 5. Iterate to paper win
- [x] 6. Build Candidate (skipped: no dev winner)
- [x] 7. Adopt gate (skipped: no dev winner)
- [x] 8. Record + Exit

## Report

**Verdict:** no win (Queue exhausted across all 19 ideas; Champion `def_xg_shrink_challenger` stands unchanged)
**Lanes:**
- `ext_14` · Continuous Match-Tempo & Counter-Transition Attack Elasticity (`xp_goals`/`xp_assists`) · best `ext_14_a15_b06` · `combined_delta = -0.6045` · `0/3` segs · `boot P = 0.000` (`tier2_oracle_fail`)
- `ext_18` · Starter-Role Conditioning & Set-Piece Share Persistence for Budget Enablers (`xp_goals`) · best `ext_18_k540_g015` · `combined_delta = -0.2407` · `0/3` segs · `boot P = 0.000` (`tier2_oracle_fail`)
- `ext_19` · Opponent Speculative Shot-Volume & Goalkeeper Save-Floor Elasticity (`xp_saves`) · best `ext_19_k900_xi035` · `combined_delta = -0.1279` · `0/3` segs · `boot P = 0.000` (`tier2_oracle_fail`)
**Audit:** all 18 prototypes across `ext_14`, `ext_18`, `ext_19` `AUDIT PASS`, no `LEAKAGE FAIL`
**Ledger:** 3 rows added (`ext_14_*`, `ext_18_*`, `ext_19_*`, locked until `2027-11-05`); `EXT-15` marked `dead-match` against Row 81 (`2027-09-30`)

## Human Queue
- [x] 1. Override Dead row `Defcon venue and opposition pressure scaling` (`revisit_after = 2027-09-30`) to evaluate `EXT-15` (Territorial Possession-Tilt & Deep-Block Defcon Elasticity)? User resolution: No (keep Dead lock intact). Evidence: `docs/research/candidate-ledger/candidate_ledger.csv` Row 81, `docs/research/candidate-ideation/ideas/EXT-15-territorial-possession-tilt-deep-block-defcon-elasticity.md`.
- [x] 2. Override Dead row `Start vs sub attack intensity` (`revisit_after = 2027-09-29`) to evaluate `EXT-16` (Co-Starter Playmaker Gravity & Non-Zero-Sum Space-Creation Synergy)? User resolution: No (keep Dead lock intact). Evidence: `docs/research/candidate-ideation/ideas/EXT-16-co-starter-playmaker-gravity-non-zero-sum-space-creation-synergy.md`.
- [x] 3. Override Dead row `Learned participation variants` / `Schedule-congestion start shift` (`revisit_after = 2027-09-28` / `2027-09-30`) to evaluate `EXT-17` (Position-Conditioned Exponential Micro-Cycle Fatigue & Ironman Stamina Resistance)? User resolution: No (keep Dead lock intact). Evidence: `docs/research/candidate-ideation/ideas/EXT-17-position-conditioned-exponential-micro-cycle-fatigue-ironman-stamina-resistance.md`.

## Next Batch Queue
- [ ] Ingest fresh ideation batch via `/ideate-candidate` (queue exhausted across all 19 candidates in `candidate-ideation/idea_queue.csv`).
