# Active Task: explore-candidate-ml-composite

- **Status:** In Progress
- **Objective:** Adopt ADR 0062 Non-Catastrophic Segment Loss Guardrail, then explore stacked challenger combining ML components with past winning components.
- **Acceptance:** Gate criteria refined and tested; candidate evaluated; promotion gate verified.
- **Issue/Ticket:** User /implement and /explore-candidate instruction.

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** backtesting/promotion.py, backtesting/model_evaluation.py, tests/test_promotion.py, docs/adr/0062-non-catastrophic-segment-loss-promotion-guardrail.md, docs/research/candidate-ledger/candidate_ledger.csv, docs/research/candidate-ledger/candidate-ledger.md, docs/research/ml-component-champion-blueprint/candidate_gate.csv, docs/research/ml-component-champion-blueprint/ml-component-champion-blueprint.md, docs/agents/current-state.md, ROADMAP.md, docs/research/INDEX.md
- **Decisions:** ADR 0062 implemented and tested (627 tests pass). Challenger re-checked on dev: combined delta +0.342, boot P 0.740, but failed early_mid segment guardrail (-0.998 < -0.15 pts/GW). Next: explore candidate stacking ML components with past winners.
- **Blocked:** None
- **Next:** Run explore-candidate stacking ML candidate with past winners that failed only under old segment criteria.

## Todo
- [x] Implement Non-Catastrophic Segment Loss Guardrail (ADR 0062) in backtesting/promotion.py
- [x] Update and expand tests in tests/test_promotion.py
- [x] Record ADR 0062
- [x] Re-check ml_component_challenger on dev
- [ ] Run explore-candidate for ML candidate + winning components

## Blockers / Notes
- None
