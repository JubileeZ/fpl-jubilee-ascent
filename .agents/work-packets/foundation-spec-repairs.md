# Active Task: Foundation specification repairs

- **Status:** In Progress
- **Objective:** Review Phases 1–14 against ADR 0066; repair confirmed defects.
- **Acceptance:** Independent Standards/Spec reviews; meaningful offline regression checks; truthful delivery scope; Champion unchanged.
- **Issue/Ticket:** User-requested local review and fixes, 2026-10-30.

## Work Packet (SFDBN)

- **Status:** Engineering validated; local checkpoint and task-only cleanup remaining. Baseline `a96af707...HEAD`, initial HEAD `64c53547`.
- **Files:** Foundation modules, tests, operator documentation, tracking as required.
- **Decisions:** User approved baseline and new packet; GPT-6.1 Sol xhigh subagents; no push; no empirical runs, archive edits or sealed-data access.
- **Blocked:** None.
- **Next:** Commit verified repairs with this in-progress packet; remove packet/task scratch and pending tracking references in cleanup checkpoint; no push.

## Todo
- [x] Complete initial Standards and Spec reviews (5 Standards, 9 Spec findings; overlap preserved by axis).
- [x] Repair confirmed defects with regression coverage.
- [x] Validate integration, Ruff, pytest and delivery gate.
- [ ] Update durable state; delete finished packet and task-only scratch.

## Blockers / Notes
- Existing implementation completion claims require verification; no new numerical protocol approval inferred.
- Confirmed: legacy recommendation authority; unverified/wrong-candidate adoption; synthetic replay default and false certificate; missing guards/confirmation admission; chronological pseudo-Holm; weak checkpoint identity; non-native live scoring/finances; mutable terminal/duplicate-ID registry; Unix-only/simulated profiler.
- Repair groups own separate files; shared evaluator/statistical API coordinated directly. No production Champion mutation.
- Follow-up review repairs include malformed failed guards, approval before scientific Fail, uncertain non-inferiority vs demonstrated harm, canonical seasonal/chip floors, fixed metric semantics/parameters, admitted opening prices, persisted certificates, future target outcome alignment and actual solver binary identity.
- Focused checkpoints: projection/statistics/registry 105 passes; native replay/live/profiler 64 passes; final profiler simulation repair 15 passes; CLI/smoke authority 16 passes. Counts overlap; not a full-suite total. Parent Ruff clean and structural delivery gate 29 passes before final source edits.
- Final shared checks: quick regression suite 53 passes; retained-source/end-to-end suite 14 passes. Parent changed core/test Pyright 0 errors; legacy diagnostic smoke retains exact same 14 typing diagnostics proven at `64c53547`. No suppression/baseline rewrite.
- Final hardening: gap math consistency shared by executor/retained evaluator; bounded Windows cache publication retry with persistent failure retention. Full-suite attempts interrupted explicitly for source corrections, not recorded as passes.
- Final full pytest: 1007 passed, 2 existing warnings, 0 failures in 335.64s. Final Standards/Spec 0 remaining confirmed findings each. No timing exception needed. Cleanup remains open; packet not finished until removed.
