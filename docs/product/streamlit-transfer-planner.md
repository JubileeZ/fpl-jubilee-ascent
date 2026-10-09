# Streamlit Transfer Planner

Status: Q1–Q12 agreed, implementation authorized through `/implement`, 2026-10-08. Streamlit app implemented; deployment deferred. Visual direction: [DESIGN.md](../../DESIGN.md). Architecture decision: [ADR 0059](../adr/0059-streamlit-transfer-planner.md). Launch/deployment: [guide](streamlit-planner-deployment.md).

Current usage: [dashboard guide](dashboard-usage.md). Subsequent [single-product integration](dashboard-planner-integration.md) replaces separate-interface approach; all four surfaces share same Streamlit app. [Responsive layout](dashboard-responsive-layout.md) replaces inline Player details with focused native dialog on all window sizes. Verification sections below retain original delivery evidence; latest checks in responsive spec.

## Scope

Single editable plan across Gameweeks; Gameweek selector replaces branching canvas. Transfer Planner, Explorer, Research, Model Methodology in one Streamlit dashboard. Prepare later private hosting; deployment deferred. Planning only: edits do not submit transfers to FPL.

Retain existing projection models, solver policies, chip rules, Selling Price accounting, and executable Transfer Plan Start at upcoming open deadline. Existing horizon length bounds retained. Existing exact-gap default + 20-minute backstop retained (ADR 0057).

## Recommendations and Jobs

- Open: restore saved draft; show valid cached solver recommendation with provenance. Without valid recommendation, offer Generate plan.
- Active scenario: Optimal / No Hit / Conservative. Scenario change replacing manual edits requires explicit confirmation.
- Distinguish cached solver result from manual draft or unsolved hold baseline. Never label baseline as solver recommendation.
- Generate plan: produce solver recommendation; show pending/running/finished/failed states until terminal result.
- Optimize remaining transfers: preserve explicit user choices; solve remaining horizon from appropriate preceding squad/bank state.
- Manual edits: recalculate legal XI immediately; avoid transfer MILP on every click.
- Solver results tied to input/version snapshot. Results computed against superseded edits retained separately; never silently overwrite newer draft.
- Failed solve preserves last usable recommendation/draft. Infeasibility explains constraints requiring change.
- Reset to solver restores applicable cached recommendation; stale result remains clearly marked.

## Player Interaction

Click Player: selected-Gameweek xP + xMins first, upcoming fixtures/projections, recent points/minutes, availability, Price/Selling Price where applicable, projection components when available. Missing history/components labelled unavailable.

- Sell from selected Gameweek: remove ownership from that week onward; add Position-labelled vacancy in bench area.
- Bench this week: retain ownership; exclude Player from selected-week Starting XI until override cleared.
- Replace: select eligible incoming Player; same Position as outgoing Player under ordinary transfer rules.
- Empty bench slot: open replacement search filtered by Position, available budget, squad uniqueness, and Club limit.
- Undo pending sale: restore Player and draft accounting.
- New purchase: available from selected Gameweek onward; recalculate XI + bench.

## Lineup and Draft Accounting

- Completed squad: 2 GKP / 5 DEF / 5 MID / 3 FWD; legal Starting Shape per existing glossary.
- Automatic XI: best feasible projected score from Players currently retained or added for selected week.
- Automatic bench order, captain, vice-captain; selected-week manual overrides available and respected.
- Contradictory overrides: explicit conflict; preserve choices for correction rather than silently dropping them.
- Partial draft: select legal XI from remaining Players when possible; otherwise show incomplete Starting XI. Vacancies displayed in bench area separately from actual bench allocation.
- Partial transfers: provisional bank, Free Transfers, Hits; disable transfer optimization until valid 15-player squad restored. Complete candidate batches evaluated against final squad validity.
- Vacant slot: no synthetic Player, Price, or Projection.

## Future Gameweeks and Persistence

- Ownership edits propagate forward; week-only lineup overrides remain scoped to their Gameweek.
- Earlier edits mark dependent future recommendations Needs recalculation; explicit future user choices preserved.
- Impossible future choice: show conflict for resolution.
- Autosave draft, selected scenario, week overrides, recommendation provenance + input snapshot, and completed solver results.
- Reload: restore persisted plan; Session State alone insufficient. Save failure visible; never claim saved without successful write.
- Jobs: recover running/completed status after page rerun/reload while worker survives. Interrupted worker/host restart reported explicitly; retry available. Process restart is not claimed to resume an in-memory solve.
- Durable storage location configurable for future hosting; private squad/auth data excluded from git.

## Deployment Preparation

Streamlit entrypoint + dependency locking; documented local launch; configurable data/storage paths; secrets supplied through environment or host secret configuration. Validate Python 3.14 + uv dependency install on Linux before declaring hosting readiness. Keep solver work separate from Streamlit UI calls; recover status through supported polling/rerun mechanisms.

Private hosting target and durable storage provider selected when deployment requested. Validate actual MILP memory/runtime on chosen host; no hosting capacity claim from local tests alone.

Official references: [Python support](https://docs.streamlit.io/knowledge-base/using-streamlit/sanity-checks), [uv dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [components](https://docs.streamlit.io/develop/concepts/custom-components/overview), [Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state), [threading](https://docs.streamlit.io/develop/concepts/design/multithreading), [private sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).

## Acceptance

- Fresh install without solver cache: Generate plan visible; no fake recommendation.
- Existing saved draft: restored independently from solver cache; stale input status visible.
- Solve lasting beyond 36 seconds: status remains observable; finished recommendation displayed.
- Player click opens details; Sell and Bench have distinct ownership effects.
- Pending sale creates real vacancy; Undo restores ownership/accounting.
- Add Player recomputes legal XI/bench; highest feasible projected score selected subject to overrides.
- Invalid budget, duplicate Player, Club limit, or Starting Shape: explicit validation.
- Two pending sells + one buy: incomplete draft; provisional totals; optimization blocked.
- Earlier edit invalidates dependent future recommendations and preserves explicit choices.
- Scenario switch confirms replacement of manual edits; Reset restores applicable solver result.
- Refresh/reload, solve failure, stale completion, and save failure preserve recoverable state.
- Local Streamlit launch + clean dependency install verified; deployment guide supplied; no publishing performed.
- UI keyboard/mobile/zoom/contrast checks; meaningful state/solver tests; repository delivery gates before commit proposal.

## Documentation Verification, 2026-10-08

- PASS: local document links resolve; `git diff --check` clean.
- PASS: intended text pairings ≥5.11:1; filled-button label 5.57:1; focus ≥4.31:1; control boundary ≥3.33:1. Verified with installed antislop-human WCAG checker.
- PASS: design direction + typography/spacing/motion purposes stated; no fabricated Player data or new visual assets.
- PASS: 17 targeted tests; real HiGHS with injected fixtures preserves manual transfer, bench, captain, vice; Streamlit AppTest exercises click/details/sell/add/reload, scenario confirmation/cancel, horizon/chip changes, completed-job recovery, solver-chip synchronization. Multiweek regression preserves optimized additions + explicit future choices after lineup edits. No external HTTP in tests.
- PASS: planner Pyright checks; local Streamlit server launched on port 8501.
- PASS: repository suite 536 tests; Ruff; Pyright; delivery gate 115 checks after finished packet deletion. Existing research-path test required temporary directory outside `.tmp`. Latest multiweek refinements rechecked through all 17 planner tests.
- PASS: desktop browser renders cached User Squad; Player click shows stats, projections, selling price, ownership/lineup actions. Player labels wrap to avoid clipping.
- PASS: rendered 390px layout has no horizontal overflow; caption opacity corrected; neutral button borders use tested token; header Refresh fully visible. Enter opens Player details; Escape dismisses details and retains Player-button focus. No browser console errors observed.
- REVIEW: Standards found missing Escape/focus behavior; native Escape shortcut added, focus limitation documented. Spec found hidden optimized moves, widget chip overwrite, retained chip overrides on Reset; repaired with regression coverage. Follow-up multiweek invalidation regression repaired.
- Unverified: actual 200% browser zoom; in-app browser zoom shortcut had no effect. Narrow viewport reflow verified; no claim of browser zoom equivalence.
- Unverified: Linux image build + hosting capacity; Docker/WSL unavailable. Deployment preparation files supplied; no publishing performed.
