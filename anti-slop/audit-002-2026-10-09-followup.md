# Dashboard usability implementation follow-up

Scope: eight findings from audit 002; user `/implement`. Apple utility direction retained, ENERGY 1 / RHYTHM 2 / MOTION 1. No new visual assets; screenshot records actual local preview.

## Changes

- Readiness summary above XI; deadline UTC, export/input-file age, missing/stale states, active policy, C/VC, transfers/hit cost/bank.
- Read-only policy/roll comparison; unweighted horizon outcomes separate from weighted solver objective. Appearance-aware comparison optional and cached; computation can take minutes.
- Active/preview labels; adoption safeguards manual transfers, overrides and chip bookings.
- Readable availability/chance/news; flagged squad cards; fixture and adjusted difficulty separate; components optional.
- Two-target same-horizon comparison; stable Player identity; explicit planner preparation, outgoing choice, review/apply/cancel.
- Chip date and locked/banned preflight; Run disabled on conflicts; worker repeats validation.
- Advanced units/examples; explicit save/reload/download; concurrent settings-write guard; invalid settings recovery.
- Usage guide/button labels updated.

## Verification

- Existing full suite: 547 passed, one pre-existing constant-correlation warning. Affected tests rerun after review repairs: 23 passed.
- Final portable delivery gate: 115 passed after finished packet deletion. Invalid saved start value verified in browser: clear error, download/defaults recovery, usable unsaved controls.
- Ruff clean. Pyright changed dashboard modules: zero errors. Exporter: 29 diagnostics both original baseline and changed file; no new diagnostics in metadata additions.
- Actual isolated browser: policy preview leaves Optimal active; five-row same-horizon comparison including Expected GW Scores; chip conflict warning disables Run/Save; legal settings save and reload retain GW6–8 / WC8 / BB7; Mbeumo/Gibbs-White comparison; reviewed Palmer→Mbeumo apply persists £1.7m bank / zero hits. Original working draft untouched.
- Phone width 390px: sidebar open/closed, controls wrap, document width equals viewport. Desktop screenshot retained. Actual 200% zoom and complete screen-reader traversal remain unverified.
- No live Refresh, solver MILP, official FPL submission or deployment during verification. New TDD test seams unconfirmed; no new tests written.

## Standards

Initial findings: three, repaired. Duplicate names now disambiguated; null projections labelled unavailable; corrupt settings cannot leave partial initialization. Recheck: zero remaining findings.

## Spec

Initial findings: two, repaired. Same-Gameweek purchase replacement amends original transfer; locked/banned conflicts identify Players. Recheck: zero remaining findings.

## Delivery gate

Changed flows clicked in isolated preview; existing interaction tests exercise prior controls. Functional hierarchy retained; no decorative treatments or invented product claims. Existing contrast/focus/tap-target CSS retained. Phone overflow checked; native keyboard Enter used for horizon inputs. Full keyboard/screen-reader/200% zoom coverage not claimed.

Implementation artifact: `docs/product/dashboard-usability/implementation.md`. [First-time manager dashboard usability](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/150) completed on explicit user acceptance, 2026-10-09; all eight tickets and map verified closed. Accessibility gaps above remain deferred.
