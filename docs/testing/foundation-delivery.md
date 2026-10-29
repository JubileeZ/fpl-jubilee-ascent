# Backtesting foundation delivery record

Implementation baseline: `66729b15`, branch `main`. Scope: [Q1-Q28](../research/backtesting-promotion-foundation/backtesting-promotion-foundation.md). Per-phase commits; no push. Champion unchanged; sealed data and frozen archives untouched.

## Phase 0 — contracts and CI authority

Implemented: versioned protocol/result/bundle contracts; named-material SHA256; separate execution/scientific outcomes; exclusive-create verification/calibration manifests; entry-point migration map. CI read-only token, no `--apply`, no commit/push step.

Review: GPT-6.1 Sol xhigh, independent Standards/Spec axes. Resolved minimum JSON artifact structures, malformed-value handling, mixed material keys, large integer finiteness, pre-serialization, shared status constants, documentation wording. No remaining substantive Phase 0 blocker.

Validation: focused 14 passed; Ruff clean; focused Pyright 0 errors; portable delivery gate 29 passed. Full suite 705 passed, 1 existing timing failure: `test_build_causal_panel_fast_execution_and_determinism`, 1.886s vs 1s; isolated 1.434s. User explicitly accepted documented timing exception for phase commits on 2026-10-29. Test and implementation untouched. Sandbox initially denied pytest temp creation and Git Bash signal pipes; validation rerun with required filesystem access. No real HTTP requested by tests.

Limits: descriptive protocol references not numerical approval; bundle structure/checksum verification not semantic eligibility. Caller supplies source dependency closure; collection/retention integration pending. Interrupted exclusive-create manifest may remain truncated; preserve attempt, new identity for retry. Explicit legacy CLI adoption remains until Phase 11; CI automatic authority removed immediately.
