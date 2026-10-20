# Active Task: explore-candidate-apex-ml-composite

- **Status:** Exit (b) Complete (Dev PASS, Confirm FAIL; Champion stands)
- **Objective:** Explore and gate a new composite Challenger (`apex_predator_challenger`) stacking ML components (calibrated ramp) with past winning components (schedule congestion, mass-preserved start duration) to win the promotion gate on dev + confirm seasons.
- **Acceptance:** Prototype evaluated via smoke.py, passing full gate on dev (2025-26) and confirm (2024-25) seasons with all guardrails green, Candidate built and registered.
- **Issue/Ticket:** User /explore-candidate instruction.

## Work Packet (SFDBN)

- **Status:** Exit (b) Complete — Apex Predator Challenger evaluated on dev (PASS +0.840 pts/GW, boot P 0.992) and unseeded confirm (FAIL -0.153 pts/GW, boot P 0.376, early_mid regression -0.959 < -0.15); logged dead in Candidate Ledger; Champion `def_xg_shrink_challenger` stands
- **Files:**
  - `models/apex_predator_challenger.py`
  - `models/ml_component_challenger.py`
  - `models/ml_panel_features.py`
  - `tests/test_apex_predator_challenger.py`
  - `docs/research/apex-predator-challenger/apex-predator-challenger.md`
  - `docs/research/apex-predator-challenger/candidate_gate.csv`
  - `docs/research/apex-predator-challenger/smoke.csv`
  - `docs/research/apex-predator-challenger/prototypes.py`
  - `docs/research/candidate-ledger/candidate_ledger.csv`
  - `docs/research/candidate-ledger/candidate-ledger.md`
  - `docs/model_name.md`
  - `docs/agents/current-state.md`
  - `ROADMAP.md`
- **Decisions:**
  - Active Champion `def_xg_shrink_challenger` (ADR 0055) stands.
  - Stacked ML components with GW1-9 Champion stability + schedule congestion penalty.
  - Dev season (2025-26): PASS (+0.8400 pts/GW, boot P 0.9922, 2/3 segs).
  - Confirm season (2024-25): FAIL (-0.1528 pts/GW, boot P 0.3764, 1/3 segs due to lack of prior-season pretraining in GW10-19 and haul shrinkage).
  - Logged dead in Candidate Ledger (`revisit_after = 2027-10-21`).
- **Blocked:** None
- **Next:** Present report to user.

## Todo
- [x] Adopt ADR 0062 Non-Catastrophic Segment Loss Guardrail (pushed to main)
- [x] Write prototypes under docs/research/apex-predator-challenger/prototypes.py
- [x] Run smoke audit_only on prototypes
- [x] Run smoke dev backtest on dev season (2025-26)
- [x] Verify stack passes ADR 0062 Non-Catastrophic Segment Loss Guardrails
- [x] Run one-shot confirmation season on 2024-25
- [x] Build Candidate models/apex_predator_challenger.py
- [x] Record research note and update Candidate Ledger

## Human Queue
- [ ] Acknowledge Dead-lever verdict for apex_predator_challenger (revisit after 2027-10-21).
