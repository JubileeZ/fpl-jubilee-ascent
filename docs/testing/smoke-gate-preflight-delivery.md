# Smoke gate repair and readiness preflight

**Date:** 2026-11-12 (Europe/Copenhagen)
**Scope:** User-approved Option B, followed by eight synthetic diagnostic solver calls. User-invoked implement skill authorizes local commits on current branch; no push.
**Review baseline:** `c6fb09bf`; implementation checkpoint `5ed060b5`, followed by reviewed repairs and task cleanup.

## Delivered behavior

- Oracle bias from one common playable pool; missing/non-finite metrics rejected. Null metrics retained as invalid stage evidence rather than aborting remaining work.
- Separate versioned stage summaries and content-addressed manifests; paired frames, weekly regret traces and pool metrics retained. Complete matching identities required for resume; changed source/data/seed/protocol or damaged evidence prevents reuse.
- Oracle success retained before integrated execution; oracle segment wins unassessed. Diagnostic completion separate from promotion execution and scientific authority.
- Evidence consumer separates Champion, season, variant, range, stage and run identity. Historical records and locks preserved.
- [Readiness report](../research/backtesting-promotion-foundation/smoke_gate_preflight.md) with reproducible companions, admission/applicability inventory, bounded solver diagnostic and controlled statistical examples.
- Report caches derive settings and result counts from companions; inconsistent calibration dimensions rejected before report replacement. Worker/start markers prevent accidental probe repetition.

## Validation

- `UV_CACHE_DIR=/tmp/fpl-uv-cache uv run --offline --no-sync ruff check .`: pass.
- `UV_CACHE_DIR=/tmp/fpl-uv-cache uv run --offline --no-sync pytest -q`: 1046 passed; three constant-input warnings from synthetic fixtures.
- `bash tests/verify.sh`: pass; final checkpoint removes completed Work Packet.
- Pyright on new diagnostic helper, readiness runner, evidence consumer and report regressions: zero errors.
- Explicit baseline comparison: promotion file retains 26 pre-existing diagnostics; smoke file improves 14 to 13, with no new diagnostics. Legacy pandas/monkeypatch typing debt remains separate.
- No Candidate/confirmation/holdout runs, archive mutation, Champion change or promotion-policy relaxation.

## Standards review

Initial finding: P2 report settings/results hardcoded instead of companion-derived. Fixed; regressions cover nondefault dimensions, nonzero defect counts and mismatching probe actions. Re-review: zero hard violations, zero actionable smell findings.

## Spec review

Initial findings: P2 null oracle metric aborted before invalid-stage retention; P2 configurable calibration dimensions misreported. Fixed; real synthetic harness and report regressions added. Re-review: zero findings or scope creep; focused synthetic/no-solver checks 11 passed.

## Remaining prerequisites

Empirical admission closed in code; historical issue-time inputs and freshness unadmitted. Recorded acquisition paths absent locally. Synthetic significance diagnostics do not establish nominal error control; numerical defaults remain unapproved. Eight tiny synthetic solves establish neither empirical season runtime nor acceptable approximation policy. Further empirical activation, source acquisition/admission and calibrated numerical proposal require separately scoped work.
