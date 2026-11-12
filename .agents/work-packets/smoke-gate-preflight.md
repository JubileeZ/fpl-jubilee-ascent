# Active Task: Smoke correctness and promotion-readiness preflight

- **Status:** In Progress
- **Objective:** Repair Development Screen measurement/provenance; establish bounded promotion readiness.
- **Acceptance:** Common playable-pool guard enforced; versioned stage evidence and identity-safe resume; historical evidence retained; admission/applicability inventory, synthetic cost/calibration diagnostics and readiness report; required checks pass.
- **Issue/Ticket:** User-approved grill-with-docs decisions, 2026-11-11.

## Work Packet (SFDBN)

- **Status:** Repairs/preflight implemented. Full suite 1042 passed; Ruff clean; portable gate 29 passed; new helper/runner/consumer types clean. Promotion types unchanged (26 diagnostics); smoke baseline improved 14 to 13, no new diagnostics. Two-axis review pending.
- **Files:** `.agents/skills/explore-candidate/{smoke.py,SKILL.md}`, `backtesting/{promotion,smoke_diagnostics}.py`, diagnostic consumer/tests; `docs/research/backtesting-promotion-foundation/smoke_gate_*` and tracking docs.
- **Decisions:** Option B: repair then bounded preflight. New packet approved; at most eight synthetic optimizer calls, 30 seconds/call, one thread, serial, 20-minute total budget. Preserve historical CSVs/locks. Retain existing promotion policy; numerical proposals remain unapproved. No Candidate/confirmation/holdout runs, adoption or archive mutation. User invoked implement 2026-11-12: commit current branch, no push. Agreed test seams: real frame-to-oracle guard, retained stage evidence/resume integrity, diagnostic consumer. Review baseline `c6fb09bf`.
- **Blocked:** Empirical replay inputs unadmitted; synthetic profiling cannot establish empirical readiness.
- **Next:** Commit verified implementation checkpoint; run Standards/Spec reviews against `c6fb09bf`, resolve findings, then delete packet in final checkpoint.

## Todo
- [x] Repair smoke pool guard and add integration regressions.
- [x] Retain stage-specific traces/identities and validate resume; update consumers/instructions.
- [x] Produce admission/applicability inventory and bounded diagnostic measurements.
- [x] Record readiness, limitations and numerical proposal; run required checks.
- [ ] Complete independent Standards/Spec review and final checkpoint.
- [ ] Update durable progress and delete finished packet.

## Blockers / Notes
- Final gate already permits individual-season ties under pooled superiority and material-loss floors.
- Historical reversals lack controlled attribution; no promised promotion winner.
