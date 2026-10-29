# Active Task: Implement Code Review Fixes Across Foundation Phases

- **Status:** In Progress
- **Objective:** Address all Standards and Spec review findings across phases 0-14 foundation.
- **Acceptance:** Cryptographic hash chaining in registry; missing evidence routes to invalid in statistics; rolling replay total_gross_points and encapsulation; adopt_champion legacy shim removal and bundle staging deduplication; profile_transfer_replay dry-run CLI feedback; foundation research notes required sections; full test suite passes; verify.sh passes.
- **Issue/Ticket:** Review findings across phases 0-14

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** backtesting/confirmation_registry.py, backtesting/evidence_statistics.py, backtesting/model_evaluation.py, backtesting/rolling_replay.py, commands/evaluate_model_promotion.py, commands/profile_transfer_replay.py, docs/research/backtesting-promotion-foundation/backtesting-promotion-foundation.md, docs/research/backtesting-promotion-foundation/ownership-anchor-feasibility.md, tests/test_confirmation_registry.py, tests/test_evidence_statistics.py, tests/test_foundation_end_to_end.py
- **Decisions:** Enforce cryptographic prev_record_hash chaining in confirmation registry; route missing guard evidence to 'invalid' to prevent false 1-year Dead Lever locks while keeping regressions as 'fail'; encapsulate ReplayDeadlineRecord serialization; require scientific_verdict 'pass' in adopt_champion; deduplicate recommendation staging; standardize research note sections.
- **Blocked:** None
- **Next:** Verify full test suite and verify.sh, then commit and push.

## Todo
- [x] Cryptographic hash chaining in ConfirmationRegistry
- [x] Route missing guard evidence to invalid in EvidenceStatistics
- [x] Expose total_gross_points and add to_dict/from_dict on ReplayDeadlineRecord
- [x] Hard-code scientific_verdict requirement in adopt_champion and deduplicate bundle staging
- [x] Add simulation notice in profile_transfer_replay CLI
- [x] Add Risks and unknowns & Decision in foundation research notes
- [x] Clean slop comments
- [ ] Run full pytest suite and verify.sh
- [ ] Commit and git push
