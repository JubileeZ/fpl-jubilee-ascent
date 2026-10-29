# Active Task: Backtesting and promotion foundation

- **Status:** In progress — Phase 3 complete, ready for Phase 4
- **Objective:** Implement temporary implementation_plan.md phase by phase; preserve Q1-Q28 and manual scientific approvals.
- **Acceptance:** Verified infrastructure and per-phase commits; no push; plan deleted only after delivery acceptance.
- **Issue/Ticket:** implementation_plan.md; docs/research/backtesting-promotion-foundation/backtesting-promotion-foundation.md

## Work Packet (SFDBN)

- **Status:** Phase 0 `a96af707`, Phase 1 `d4536c42`, Phase 2 `d8fa3ad6` committed locally. Phase 3 engineering completed, both reviews accepted, 41 focused tests pass, Ruff clean, new-core types clean.
- **Files:** implementation_plan.md; backtesting/data_admission.py; backtesting/forecast_inputs.py; backtesting/forecast_adapter.py; backtesting/forecast_export.py; backtesting/forecast_store.py; backtesting/forecast_solver_export.py; backtesting/replay_cache.py; models/base.py; tests/test_forecast_*.py; tests/test_replay_cache.py; docs/testing/causal-forecasts.md; durable tracking.
- **Decisions:** Current branch main; local phase commits, no push. Numerical freeze, adoption, rollback and sealed-data amendments retain explicit approval barriers. No Champion change. Temporary-document cleanup mandatory after full delivery.
- **Blocked:** Empirical admission and numerical protocol still unapproved. User accepted existing timing-only test exception for phase commits; no test weakening.
- **Next:** Phase 4: Construct and freeze neutral GW1 anchor.

## Todo
- [x] Complete Phase 0 contracts, tests and review; 14 focused passes, type/Ruff clean, 29 portable gate passes; full suite 705 passes plus accepted existing timing exception.
- [x] Complete reviewed Phase 1 synthetic engineering checkpoint; 61 focused passes, lint/type clean, 753 full-checkpoint passes plus accepted timing exception. Empirical/native/adapter follow-through retained explicitly in plan.
- [x] Complete scoped Phase 2 native state/scoring checkpoint; both reviews accepted, 139 focused and 772 full-suite passes, Ruff/new-core types clean. Causal calendar/source adapters and empirical applicability remain explicit.
- [x] Complete Phase 3 causal forecasts and reproducible store checkpoint; both reviews accepted, 41 focused passes, Ruff clean, new-core types clean, portable gate 29 passes.
- [ ] Implement Phase 4 neutral GW1 anchor construction and freeze.
- [ ] Implement subsequent phases in dependency order; preserve approval barriers.
- [ ] Final validation, cleanup, plan deletion and confirmation.

## Resume instructions — independent of previous chat

Repository: `C:\Users\phjenphithak\fpl-jubilee-ascent`. Python 3.14 / uv / pandas / pyarrow / HiGHS / pytest. Branch `main`. Preserve all existing commits and unfinished changes; no reset, discard or automatic push. Locate handoff checkpoint with `git log -5 --oneline`; last accepted phase baseline `d8fa3ad6`. A handoff checkpoint is a saved unfinished state, not a delivery claim.

Startup reading order:
1. `AGENTS.md`, `docs/agents/current-state.md`, active foundation section in `ROADMAP.md`, then `git status --short` and `git log -5 --oneline`.
2. This packet, explicitly bound by handoff ID `backtesting-promotion-foundation`.
3. Root `implementation_plan.md`: governing decisions, Phase 3 checklist, then subsequent phase dependencies.
4. `docs/testing/causal-forecasts.md`, `docs/testing/data-admission.md`, `docs/testing/native-replay-state.md`, `docs/testing/evaluation-protocol-v1.md`, and latest entries in `docs/testing/foundation-delivery.md`.
5. Before historical exploration/backtesting: `docs/testing/archive-testing.md`, `docs/research/INDEX.md`; before new Candidate lever: Candidate Ledger. Main settled rationale: `docs/research/backtesting-promotion-foundation/backtesting-promotion-foundation.md` (Q1–Q28).

Suggested opening request for next session:

> Continue work packet `backtesting-promotion-foundation` from unfinished Phase 3. Read repository instructions, handoff packet and implementation plan first. Reproduce recorded defects, finish Phase 3, review against standards and specification, run required checks, update progress and commit locally phase by phase on current branch. Do not push or change Champion. Preserve approval/sealed-data barriers. Delete temporary plan, finished packet and matching handoff pointer only after full implementation delivery; verify deletion and report it.

## What exists / what remains

Accepted checkpoints:
- Phase 0: versioned protocol/evidence contracts and recommendation-only CI boundary, `a96af707`.
- Phase 1: synthetic causal admission/fixture checks plus historical acquisition inventory, `d4536c42`. Actual freshness, complete per-origin sources and empirical admission remain unverified; unchecked plan items intentional.
- Phase 2: native season rules, full replay state, finance/FT/chip/lineup transitions and explicit native scoring context, `d8fa3ad6`. Causal calendar/source integration and some historical exceptions remain explicit limits.

Phase 3 draft seams:
- `forecast_inputs.py`: retained synthetic v2 authority/training bundle; source cutoff, clubs, prior seed mapping, current history before issue. Prior-season GW38 allowed at current-season GW1. Proved seed absence for newcomers supported.
- `forecast_adapter.py`: staged snapshot-backed builder; explicit native rule/issue context; fresh concrete `DefXgShrinkChallengerModel`, current-history fit once, six-target prediction once. `BaseModel` itself exposes predict only; do not invent generic fit/cache support.
- `forecast_export.py`: strict fixture/blank coverage and DGW aggregation; no missing-target zero padding. Component validator draft also present; audit actual call sites.
- `forecast_store.py`: retained source/dirty-code material, content-addressed forecast table/manifest, original admission revalidation on verified load, attempt start/complete/failure records. Atomicity, concurrency, integrity and semantic validation incomplete.
- `forecast_solver_export.py`: ForecastID-linked solver CSV draft with admitted names/clubs/native price conversion; latest edits had not been tested before stop.
- `replay_cache.py`: full-state/problem identity and replay checkpoint draft, native transition recomputation and parent hashes. Current test uses mocked forecast admission; not end-to-end proof.
- `models/base.py`: explicit issue-context cutoff handling; legacy callers without context retain behavior. `data_admission.py`: synthetic v2/native bridge support.
- Four new test files: `test_forecast_inputs.py`, `test_forecast_adapter.py`, `test_forecast_export.py`, `test_replay_cache.py`. `causal-forecasts.md` updated at handoff to distinguish drafts from verified behavior; reconcile again after remaining implementation.

All new paths synthetic diagnostic only. No real historical forecasts, actual replay/MILP, empirical gate evidence or adoption produced.

Highest-priority next work:
1. Reproduce current tests/types; fix failures without weakening assertions. Three Pyright errors at handoff: `tests/test_replay_cache.py` lines 34/36/39, invariant `dict` value inference vs `AdmissionContext`. Lines may shift.
2. Wire declared component coverage/native-total reconciliation into generation AND verified cache load/export; immutable checksums alone insufficient semantic proof. Missing required metrics cannot become zero/N/A/pass.
3. Harden full staging/source schemas, retained authorized raw closure and no terminal/archive fallback. Mutations to post-cutoff/current-future rows must reject or leave forecast unchanged; prior seed history remains separate.
4. Verify ForecastID stability and mutation sensitivity: source/code/parameters/training/rules/cutoff/target schedule changes invalidate; independent later outcome packages do not alter input/forecast identity. No reliance on caller-supplied digest alone.
5. Exercise solver CSV against actual parser contract, native prices/clubs/positions, complete clipped six-GW horizon, DGWs/known blanks/missing target rejection, and same ForecastID.
6. Multi-deadline parent/state lineage, resume from last validated transition, corrupt/stale/incomplete cache rejection, interrupted attempts, concurrent publication and race tests. Verify outcomes never contaminate forecasting side.
7. Add real offline synthetic integration across adapter/store/export/problem/checkpoint; current mocked checkpoint test insufficient. Explicit feature/fit caching scope: no fitted-state serialization support currently claimed.
8. Update documentation/checklists to actual implementation; obtain code review, run full required checks, then commit completed Phase 3. Proceed Phases 4–14 in plan order; do not mark deferred empirical/approval requirements complete.

## Validation / environment

Latest accepted Phase 2: 139 focused tests, 772 full-suite tests; Ruff/new-core Pyright clean; portable gate 29 passes. Phase 3 earlier implementation reports: 31 broader focused passes, later five focused passes, with Ruff/Pyright clean at those earlier snapshots. Subsequent edits invalidate those as final validation. Current handoff checks appended below after completion.

Current stopped-code handoff validation: Ruff passes; all five Phase 3 tests pass (5.90s); full suite 776 passed, one existing speed benchmark failed (1.9487s vs 1s), two existing constant-input warnings, 414.36s total. User-accepted timing exception applies; test untouched. New Phase 3/test Pyright: three errors, all `tests/test_replay_cache.py` context-dict typing, not waived or fixed. Portable gate 29 passes. No completed Phase 3 review; checkpoint intentionally WIP, not deliverable acceptance. Required review and type repairs remain next-session work.

Commands from repo root:
```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.tmp\uv-cache'
uv run --offline ruff check .
uv run --offline pytest tests/test_forecast_inputs.py tests/test_forecast_adapter.py tests/test_forecast_export.py tests/test_replay_cache.py tests/test_data_admission.py tests/test_feature_leakage.py -q -p no:cacheprovider
.venv\Scripts\pyright.exe --pythonpath .venv\Scripts\python.exe backtesting/forecast_inputs.py backtesting/forecast_adapter.py backtesting/forecast_export.py backtesting/forecast_store.py backtesting/forecast_solver_export.py backtesting/replay_cache.py tests/test_forecast_inputs.py tests/test_forecast_adapter.py tests/test_forecast_export.py tests/test_replay_cache.py
uv run --offline pytest -q -p no:cacheprovider
& 'C:\Program Files\Git\bin\bash.exe' tests/verify.sh
```
Other OS: use installed Bash/Python paths; preserve Python/uv versions and offline/mocked tests. Default uv cache/pytest temp/Git Bash signal pipe denied in prior restricted environment; accessible filesystem permissions required. These are environment restrictions, not permission to skip validation. Existing unrelated causal-panel speed benchmark has user-accepted timing-only exception; applies to that benchmark only, never new functional/type failures. Broad legacy typing debt exists; no project-wide Pyright-clean claim.

No known active subprocess at implementation stop. Task-owned failed pytest scratch `.tmp/agent/phase3-tests` removed at handoff; `Test-Path` returned False. Unrelated `.tmp/agent/explore-candidate/` preserved, existence confirmed. No root `walkthrough.md` exists.

## Authorization and data boundaries

- Primary: actual native-season net FPL points after hits through independent rolling six-GW Strategic plans. One neutral highest-owned feasible full £100m GW1 fifteen/season; lock squad GW1, transfers GW2. Total/minutes/components substantive safeguards. Q1–Q28 remain settled.
- Scientific Pass / demonstrated Fail / Inconclusive / Invalid separate from execution status. Human approval for numerical protocol freeze, adoption/rollback, sealed amendment and individual locked-lever reopening. Bootstrap saved scores, never solver per bootstrap draw. Missing evidence means wait/keep Champion.
- Champion `def_xg_shrink_challenger` unchanged. No production selection writes, new Candidate mechanisms, blanket historical reruns, or locked mechanism retries authorized.
- Historical acquisition approval limited to immutable public 2023-24/2024-25/2025-26 input snapshots and separately retained finalized outcomes/components, outside frozen archives. Acquisition is not empirical admission. Three opening packages plus GW2 pilot acquired, all unadmitted. Raw gitignored packages under `data/reports/replay-admission/v1/` do not travel with Git; inventory/research companions do. Verify existence/hashes before use on another machine; missing raw bytes never fabricate admission.
- Entire 2026-27 excluded from acquisition; sealed 2026-27 GW6+ boundary unchanged. No sealed-data inspection. Never edit `data/archive/`; no real external HTTP in tests; never expose credentials. No push authorized.

## Temporary files — delete after full delivery

Keep during unfinished work; do not delete to make handoff look complete:
- Root `implementation_plan.md` (temporary full checklist).
- This `.agents/work-packets/backtesting-promotion-foundation.md` (temporary handoff/work record).
- `.agents/handoff-pointer` only while it contains this packet ID; preserve if later repointed to another task.
- Task-created `walkthrough.md` if later created; none exists at this handoff.
- Task-owned scratch under `.tmp/agent/`; preserve unrelated exploration resume state and retained source/evidence packages.

At full delivery: preserve durable rationale/protocols/source inventories/tests and delivery evidence; replace temporary plan/packet pointers in ROADMAP/current-state with durable references; delete temporary files above, not empty/archive as canon. Verify `Test-Path` false for plan and finished packet, and absence of matching handoff pointer. Record validation, unresolved empirical/human barriers, final commit and deletion confirmation in durable tracking/final response. Do not delete source/evidence or unrelated user work.

## Blockers / Notes
- Preserve existing conversation-owned research artifacts. No real HTTP in tests; no sealed/archive mutations.
- Checkpoint B acquisition scope explicitly approved by user 2026-10-29: immutable public input snapshots and separately held finalized outcome/component packages for 2023-24, 2024-25, 2025-26. Excludes entire 2026-27, archive edits, model comparisons, solver runs. Approval not empirical admission or numerical freeze.
