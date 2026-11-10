# Active Task: explore-candidate-candidate-ideation

- **Status:** In Progress
- **Objective:** explore-candidate candidate-ideation: frozen Candidate with verified ADR 0066 evidence and registered confirmation, adoption queued in Human Queue — or scope exhausted with every attempt recorded. Smoke diagnostics alone cannot satisfy gate. State: .agents/work-packets/explore-candidate-candidate-ideation.md
- **Acceptance:** All eligible candidate ideas (EXT-32, EXT-33, EXT-34) evaluated under ADR 0068 serialized 3-subagent review and execution engine against Champion def_xg_shrink_challenger on Dev 2025-26; results recorded in idea_queue.csv and candidate_ledger.csv; verify.sh passes.
- **Issue/Ticket:** ADR 0068 / ADR 0066

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** docs/research/candidate-ideation/idea_queue.csv, docs/research/candidate-ideation/smoke_results.csv, docs/research/candidate-ledger/candidate_ledger.csv, docs/research/candidate-ideation/prototypes/ext_32/prototypes.py, docs/research/candidate-ideation/prototypes/ext_33/prototypes.py, docs/research/candidate-ideation/prototypes/ext_34/prototypes.py, docs/research/candidate-ideation/candidate-ideation.md, docs/agents/current-state.md
- **Decisions:** Queue mode on docs/research/candidate-ideation/idea_queue.csv. Batch 7: EXT-32, EXT-33, EXT-34. All 3 candidates completed under ADR 0068 serialized 3-subagent review protocol. All 3 demonstrated positive Tier 2 Oracle signals but failed Tier 3 walkforward Development Screen. All 3 logged in candidate_ledger.csv with open status preserved. Entire queue exhausted (Exit b: no win). Model Champion def_xg_shrink_challenger unchanged.
- **Blocked:** None
- **Next:** Await operator instructions for next ideation vector or evaluation focus.

## Metadata
- **Mode:** Queue
- **Scope:** docs/research/candidate-ideation/idea_queue.csv (Batch 7: EXT-32, EXT-33, EXT-34)
- **Champion:** def_xg_shrink_challenger
- **Seasons:** dev=2025-26 (GW1-38, seed 2024-25), confirm=2024-25 (GW1-38, seed 2023-24), holdout=2026-27 (sealed)
- **Step:** 8 (Record + Exit b)
- **Round:** 1

## Batch 7 Lanes
- [x] Lane 1: `ext_32` (EXT-32: Smooth Sigmoid Attacking-Role Stratification for Fullbacks)
  - Mechanism: Replaces DefXgShrinkChallengerModel.predict with smooth sigmoid threat transition and asymptotic minute reliability.
  - Grid: tau_threat=15.0,k_oop=800,m_zero=360,gamma_oop=0.20,s_threat=3.0; tau_threat=15.0,k_oop=600,m_zero=360,gamma_oop=0.25,s_threat=3.0; tau_threat=15.0,k_oop=1000,m_zero=450,gamma_oop=0.20,s_threat=3.0; tau_threat=18.0,k_oop=800,m_zero=360,gamma_oop=0.25,s_threat=3.0; tau_threat=18.0,k_oop=600,m_zero=450,gamma_oop=0.25,s_threat=3.5; tau_threat=14.0,k_oop=800,m_zero=360,gamma_oop=0.20,s_threat=2.5
  - Best row: ext_32_t18_k800_m360 (delta -0.0187, segs 1/3, boot P 0.514)
  - Status: fail
- [x] Lane 2: `ext_33` (EXT-33: Truly Asymmetric Convex-Balanced Clean Sheet Hazard)
  - Mechanism: Strict convex weighting (1-w)z_fdr + wz_opp, K_cs=8 shrinkage, asymmetric hazard exp(alpha z) / exp(beta z) with beta = rho*alpha (rho 0.20-0.35).
  - Grid: alpha_cs=0.18,rho_cs=0.25,k_cs=8.0; alpha_cs=0.22,rho_cs=0.25,k_cs=8.0; alpha_cs=0.22,rho_cs=0.20,k_cs=10.0; alpha_cs=0.26,rho_cs=0.20,k_cs=10.0; alpha_cs=0.18,rho_cs=0.33,k_cs=6.0; alpha_cs=0.22,rho_cs=0.33,k_cs=6.0
  - Best row: ext_33_a18_r33_k6 (delta -0.0371, segs 1/3, boot P 0.229)
  - Status: fail
- [x] Lane 3: `ext_34` (EXT-34: Unified Fullback Attacking-Role and Matchup Clean-Sheet Hazard)
  - Mechanism: Co-optimization of sigmoid fullback role stratification (EXT-32) and asymmetric clean sheet hazard (EXT-33).
  - Grid: tau_threat=15.0,k_oop=800,alpha_cs=0.18; tau_threat=15.0,k_oop=800,alpha_cs=0.22; tau_threat=15.0,k_oop=600,alpha_cs=0.22; tau_threat=18.0,k_oop=800,alpha_cs=0.18; tau_threat=18.0,k_oop=800,alpha_cs=0.22; tau_threat=18.0,k_oop=600,alpha_cs=0.22
  - Best row: ext_34_t18_k600_a22 / ext_34_t18_k800_a22 (delta -0.0988, segs 1/3, boot P 0.427)
  - Status: fail

## Todo
- [x] 0. Ground (seasons, packet, ledger screen)
- [x] 3a. EXT-32: Implementer subagent creates prototype
- [x] 3b. EXT-32: Reviewer A (Spec/Math) + Reviewer B (Standards/Arch) dual-axis review
- [x] 4. EXT-32: Purge stale rows, smoke test, record results, atomic checkpoint
- [x] 3a. EXT-33: Implementer subagent creates prototype
- [x] 3b. EXT-33: Reviewer A (Spec/Math) + Reviewer B (Standards/Arch) dual-axis review
- [x] 4. EXT-33: Purge stale rows, smoke test, record results, atomic checkpoint
- [x] 3a. EXT-34: Implementer subagent creates prototype
- [x] 3b. EXT-34: Reviewer A (Spec/Math) + Reviewer B (Standards/Arch) dual-axis review
- [x] 4. EXT-34: Purge stale rows, smoke test, record results, atomic checkpoint
- [x] 8. Summary report & Exit

## Human Queue
- [ ] Await operator review on next ideation direction (queue exhausted across EXT-01 through EXT-34; Champion def_xg_shrink_challenger retained).
