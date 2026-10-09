# Dashboard usability implementation

Source: [First-time manager dashboard usability](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/150); audit `anti-slop/audit-002-2026-10-09.md`. User `/implement` authorizes execution. Existing Apple utility direction; ENERGY 1 / RHYTHM 2 / MOTION 1.

## Decisions and acceptance

- 151: Decision summary before XI: absolute deadline UTC, projection export age, unavailable/stale warnings, active policy, C/VC, transfers, hit cost, bank, readiness. Export metadata required; legacy exports explicitly unknown.
- 152: Same-horizon read-only comparison of active draft, valid Optimal/No Hit/Conservative recommendations, unchanged User Squad roll baseline. Immediate and horizon lineup points after hits, Expected GW Score, transfers, hit cost, final bank/free transfers. Missing/partial recommendations explicitly unavailable. Weighted solver objective explained separately; no inferred solver error.
- 153: Label selector preview policy; active policy explicit. Preview metrics read-only; explicit adoption protects transfers, lineup overrides, chip bookings. Cancel preserves draft.
- 154: Shared availability labels and named chance of playing, explicit missing chance, injury news/minutes. Fixtures separate from adjusted difficulty; official 1–5 with home −0.25/away +0.25, lower easier; double-week average. Components under labelled expander.
- 155: Two-player comparison over Explorer horizon, retaining missing projection values. Prepare incoming Player in Transfer Planner, choose outgoing Player and Gameweek, validate through existing candidates, review then explicitly save. What-If stays independent; no solve or official transfer.
- 156: Duplicate chip Gameweeks and locked/banned overlap invalid before submit; errors name conflicts/alternatives; Run disabled. Worker repeats validation before expensive solve.
- 157: Help explains horizon endpoints, decay, FT/bank values, bench weights and policy differences using units/examples. No unsupported preset claims.
- 158: Explicit Save advanced settings, persisted separately from draft with optimistic concurrency, saved/unsaved/error feedback, reload latest saved settings, download current inputs. Horizon changes clear out-of-window bookings with notice. No silent save on field edits.

## Verification

Public boundaries: Planner, PlanStore, Streamlit AppTest (pending user agreement). Browser click-through of changed controls; existing solver/model behavior retained. Full suite once at delivery; targeted tests/types during implementation. Review against start commit, standards and spec separate.
