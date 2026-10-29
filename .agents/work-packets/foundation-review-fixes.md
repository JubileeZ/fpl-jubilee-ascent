# Active Task: foundation-review-fixes

- **Status:** In Progress
- **Objective:** Fix Standards and Spec review findings across Backtesting & Promotion Foundation (Phases 1-14)
- **Acceptance:** Full test suite passes (874 tests), Ruff clean, Pyright clean, delivery gate passes, operator workflow doc aligned, end-to-end lifecycle verified
- **Issue/Ticket:** #166

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** backtesting/evidence_statistics.py, backtesting/live_capture.py, backtesting/confirmation_registry.py, backtesting/projection_guards.py, commands/evaluate_model_promotion.py, commands/audit_legacy_verdicts.py, docs/testing/operator-workflow.md, tests/test_foundation_end_to_end.py
- **Decisions:** Enforce human approval requirement for scientific pass verdict; restore sequential Holm step-down alpha formula; add CLI flags --confirmation_data_dir and --confirmation_seed_season; harden adopt_champion validation against missing or partial execution status; expose module-level evaluate_live_review wrapper; fix doc-code drift in operator-workflow.md; standardize research note headers in foundation research docs; implement offline foundation end-to-end integration test
- **Blocked:** None
- **Next:** Delivery gate verification and commit

## Todo
- [x] Fix Holm adjustment and human approval gate in evidence_statistics.py
- [x] Harden adopt_champion against missing execution status in evaluate_model_promotion.py
- [x] Expose evaluate_live_review top-level helper in live_capture.py
- [x] Clean up obvious comments in confirmation_registry.py and projection_guards.py
- [x] Align operator-workflow.md to actual class and method names
- [x] Standardize research note metadata headers in foundation research docs
- [x] Implement offline end-to-end foundation integration test (tests/test_foundation_end_to_end.py)
- [ ] Conclude review fixes Checkpoint
