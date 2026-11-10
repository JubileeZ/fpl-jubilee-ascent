# Active Task: explore-candidate-candidate-ideation

- **Status:** In Progress
- **Objective:** explore-candidate candidate-ideation: frozen Candidate with verified ADR 0066 evidence and registered confirmation, adoption queued in Human Queue — or scope exhausted with every attempt recorded. Smoke diagnostics alone cannot satisfy gate. State: .agents/work-packets/explore-candidate-candidate-ideation.md
- **Acceptance:** All eligible candidate ideas (EXT-32, EXT-33, EXT-34) evaluated under ADR 0068 serialized 3-subagent review and execution engine against Champion def_xg_shrink_challenger on Dev 2025-26; results recorded in idea_queue.csv and candidate_ledger.csv; verify.sh passes.
- **Issue/Ticket:** ADR 0068 / ADR 0066

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** docs/research/candidate-ideation/idea_queue.csv, docs/research/candidate-ideation/smoke_results.csv, docs/research/candidate-ledger/candidate_ledger.csv, docs/research/candidate-ideation/prototypes/ext_32/prototypes.py
- **Decisions:** Queue mode on docs/research/candidate-ideation/idea_queue.csv. Batch 7: EXT-32, EXT-33, EXT-34. Lane ext_32 completed: 6/6 passed Tier 2, all 6 failed Tier 3 (best ext_32_t18_k800_m360 delta -0.0187, late regression -0.230). Open status in ledger preserved. Moving to EXT-33.
- **Blocked:** None
- **Next:** Implement and review EXT-33 (ext_33).

## Metadata
- **Mode:** Queue
- **Scope:** docs/research/candidate-ideation/idea_queue.csv (Batch 7: EXT-32, EXT-33, EXT-34)
- **Champion:** def_xg_shrink_challenger
- **Seasons:** dev=2025-26 (GW1-38, seed 2024-25), confirm=2024-25 (GW1-38, seed 2023-24), holdout=2026-27 (sealed)
- **Step:** 3 (Dispatch subagents for EXT-33)
- **Round:** 1

## Batch 7 Lanes
- [x] Lane 1: `ext_32` (EXT-32: Smooth Sigmoid Attacking-Role Stratification for Fullbacks)
  - Mechanism: Replaces DefXgShrinkChallengerModel.predict with smooth sigmoid threat transition and asymptotic minute reliability.
  - Grid: tau_threat=15.0,k_oop=800,m_zero=360,gamma_oop=0.20,s_threat=3.0; tau_threat=15.0,k_oop=600,m_zero=360,gamma_oop=0.25,s_threat=3.0; tau_threat=15.0,k_oop=1000,m_zero=450,gamma_oop=0.20,s_threat=3.0; tau_threat=18.0,k_oop=800,m_zero=360,gamma_oop=0.25,s_threat=3.0; tau_threat=18.0,k_oop=600,m_zero=450,gamma_oop=0.25,s_threat=3.5; tau_threat=14.0,k_oop=800,m_zero=360,gamma_oop=0.20,s_threat=2.5
  - Best row: ext_32_t18_k800_m360 (delta -0.0187, segs 1/3, boot P 0.514)
  - Status: fail
- [ ] Lane 2: `ext_33` (EXT-33: Truly Asymmetric Convex-Balanced Clean Sheet Hazard)
  - Mechanism: Strict convex weighting (1-w)z_fdr + wz_opp, K_cs=8 shrinkage, asymmetric hazard exp(alpha z) / exp(beta z) with beta = rho*alpha (rho 0.20-0.35).
  - Grid: alpha_cs=0.18,rho_cs=0.25,k_cs=8.0; alpha_cs=0.22,rho_cs=0.25,k_cs=8.0; alpha_cs=0.22,rho_cs=0.20,k_cs=10.0; alpha_cs=0.26,rho_cs=0.20,k_cs=10.0; alpha_cs=0.18,rho_cs=0.33,k_cs=6.0; alpha_cs=0.22,rho_cs=0.33,k_cs=6.0
  - Best row: pending
  - Status: in-progress-b7
- [ ] Lane 3: `ext_34` (EXT-34: Unified Fullback Attacking-Role and Matchup Clean-Sheet Hazard)
  - Mechanism: Co-optimization of sigmoid fullback role stratification (EXT-32) and asymmetric clean sheet hazard (EXT-33).
  - Grid: tau_threat=15.0,k_oop=800,alpha_cs=0.18; tau_threat=15.0,k_oop=800,alpha_cs=0.22; tau_threat=15.0,k_oop=600,alpha_cs=0.22; tau_threat=18.0,k_oop=800,alpha_cs=0.18; tau_threat=18.0,k_oop=800,alpha_cs=0.22; tau_threat=18.0,k_oop=600,alpha_cs=0.22
  - Best row: pending
  - Status: untested (queued)

## Todo
- [x] 0. Ground (seasons, packet, ledger screen)
- [x] 3a. EXT-32: Implementer subagent creates prototype
- [x] 3b. EXT-32: Reviewer A (Spec/Math) + Reviewer B (Standards/Arch) dual-axis review
- [x] 4. EXT-32: Purge stale rows, smoke test, record results, atomic checkpoint
- [ ] 3a. EXT-33: Implementer subagent creates prototype
- [ ] 3b. EXT-33: Reviewer A (Spec/Math) + Reviewer B (Standards/Arch) dual-axis review
- [ ] 4. EXT-33: Purge stale rows, smoke test, record results, atomic checkpoint
- [ ] 3a. EXT-34: Implementer subagent creates prototype
- [ ] 3b. EXT-34: Reviewer A (Spec/Math) + Reviewer B (Standards/Arch) dual-axis review
- [ ] 4. EXT-34: Purge stale rows, smoke test, record results, atomic checkpoint
- [ ] 8. Summary report & Exit

## Human Queue
- [ ] None currently pending.
