# Backtesting and promotion foundation implementation plan

Status: **PAUSED FOR HANDOFF DURING PHASE 3**. Prepared 2026-10-29 against repository `66729b15`; implementation authorized 2026-10-29. Resume from `.agents/work-packets/backtesting-promotion-foundation.md`. Commit each completed phase on current branch; no push. Unchecked items remain pending; scientific/human approval boundaries still apply.

## Execution status and phase teams

- Phase 0: complete; local commit `a96af707`.
- Phase 1: synthetic admission engineering committed `d4536c42`; accepted by Standards and Spec, 61 focused passes, lint/type checks clean, full checkpoint 753 passes plus accepted timing exception. Explicit empirical/native/integration follow-through remains unchecked below.
- Phase 2: committed `d8fa3ad6`; both review axes accepted, 139 focused and 772 full-suite passes, Ruff/new-core types clean. Scoped empirical/calendar/solver limits explicit.
- Phase 3: unfinished work checkpoint from `d8fa3ad6`; causal forecasts/export/cache/resume drafts retained. Not accepted or phase-complete. Session stopped at user request; see handoff packet for defects and next steps.
- Phases 4–14: not started.
- Progress states: implement -> review against repository standards and agreed specification -> repair findings -> validation -> local commit. Record findings, validation and commit in durable delivery record; update checklist/current-state at each transition. No push.
- Execution workflow chosen by next session. Resume from repository files; no dependency on this chat or its runtime.

Draft author: GPT-6.1 Sol subagent, xhigh reasoning; parent review checked dependencies, source seams, approval boundaries, and completion/deletion criteria.

Deliverable: reproducible evaluation infrastructure measuring actual net FPL points from rolling Transfer Plans, with substantive player-projection safeguards, auditable evidence, and manual adoption. Infrastructure delivery can finish before fresh confirmation accumulates. Candidate statistical Pass, Champion adoption, and live validation remain separate evidence-dependent outcomes.

Temporary document: root `implementation_plan.md`. Governing rationale remains [foundation Q1-Q28](docs/research/backtesting-promotion-foundation/backtesting-promotion-foundation.md). Delete this plan after implementation delivery meets final checklist; retain durable rationale, approved protocols, evidence, and tracking. Do not delete during drafting.

## Governing decisions and boundaries

Read with [independent review](docs/research/backtesting-promotion-foundation/independent-review.md), [ownership feasibility](docs/research/backtesting-promotion-foundation/ownership-anchor-feasibility.md), and [preflight proposal](docs/research/backtesting-promotion-foundation/preflight-plan.md). Q28 supersedes earlier mandatory archetype/personal-squad direction in Q8/Q24 and review proposals.

- Primary outcome: actual native-season FPL score after transfer penalties. Process Points and Blended Eval Target remain supporting diagnostics under new protocol. Accurate/interpretable total, minutes, and measurable component forecasts remain mandatory final safeguards.
- Primary policy: frozen six-Gameweek rolling Strategic policy. Execute immediate decision, then replan. Bounded Unconstrained development diagnostics; no mandatory Unconstrained win. Predeclare investigation of substantial policy-arm reversals.
- One initial reference per admitted season: highest summed reported ownership among feasible full fifteens, initial £100m budget, native position/club/eligibility constraints, deterministic neutral ties. Lock fifteen at GW1 deadline; score GW1 lineup/captain; transfers start GW2 with native FT state. Each model then carries independent squad, finances, transfers, hits, and chips continuously.
- One shared causal chip calendar initially; native-season rules and supported chip-policy subset explicitly registered. Extra calendars, personal squads, refreshed anchors, and additional starts optional diagnostics. Refreshed origins cannot become stitched continuous-season scores or independent seasons.
- Scientific verdicts: Pass, demonstrated Fail, Inconclusive, Invalid. Execution status recorded separately. Lack of a positive result does not establish harmful mechanism; existing Dead Lever locks remain operational until individually reopened by explicit user words.
- Positive incremental gains allowed without fixed practical-gain floor. Convincing uncertainty evidence, material-loss limits by season/state, and total/minutes/component non-inferiority still required.
- Q17: target at most 5% search-wide false-positive recommendation risk under declared comparison family. Independent review flags global-null/weak versus mixed-configuration/strong control, constituent-test validity, adaptive reuse, and small independent-season sample. Technical proposal must state protection actually supported. Existing bootstrap fractions are not an achieved guarantee.
- Historical seasons already inspected remain development/robustness evidence. When required standard unsupported, retain Champion and wait for registered fresh confirmation. Preserve sealed 2026-27 GW6+ boundary. Any prospective window overlapping existing seal requires explicit protocol amendment before access.
- Human approval required for quantitative protocol freeze, adoption, rollback, individual locked-lever reopening, and any holdout-protocol amendment. Q21 calibration produces reviewable proposals; it does not infer human harm preferences from observed noise.

Current operational canon remains [INDEX](docs/research/INDEX.md), [archive-testing](docs/testing/archive-testing.md), and accepted ADRs until reviewed migration. This plan proposes changes conflicting with ADR 0044/0047/0064 promotion primary and authority; document supersession explicitly in Phase 13. It does not itself supersede them.

Scope excludes new Candidate mechanisms, blanket historical reruns, automatic Champion changes, sealed-data inspection, archive-file edits, product UI redesign, and independent chip-timing research. Production configuration changes belong to explicitly approved adoption/migration scope. Historical source acquisition uses archive/snapshot tooling or separate versioned research packages; existing Season Archive remains immutable.

## Delivery sequence and checkpoints

Order: Phase 0 identity/contracts -> Phase 1 admission -> Phase 2 rules/state specification -> Phases 3-4 forecasts/anchor -> Phase 5 verified replay -> Phase 6 guards -> Phase 7 bounded profile -> Phase 8 numerical/statistical approval -> Phases 9-11 confirmation/live/manual-promotion infrastructure -> Phases 12-14 audit, migration, delivery. Phase 12 audit can proceed from existing recorded evidence without replay or numerical freeze.

New module/test paths below are proposed implementation targets. Reuse existing code where correct; preserve module boundaries by behavior rather than mechanically adding every named file. Record justified path changes in bound work record. All new Python code explicitly typed; CLIs runnable as modules.

### Phase 0. Register implementation boundary and evidence contracts

Dependencies: approved implementation scope. No Candidate evaluation required.

Likely seams: `backtesting/promotion.py`, `backtesting/model_evaluation.py`, `commands/evaluate_model_promotion.py`; proposed `backtesting/evaluation_protocol.py`. Tracking through `docs/agents/progress.md`; parent implementation session handles Work Packet lifecycle.

- [x] Record initial repository state and preserve conversation-owned uncommitted research notes. Bind/create implementation work record under repository workflow only when implementation begins. No automatic binding to unrelated leftover packet.
- [x] Inventory entry points: projection backtest, Transfer Plan Walk-Forward, smoke harness, promotion CLI, CI workflow, live reassessment, model selection writes. Mark legacy behavior versus proposed protocol; expose no partially migrated promotion route.
- [x] Before the first pushed implementation change in workflow-triggering paths, remove automatic Champion mutation/commit authority from the promotion workflow under approved implementation scope. Establish recommendation-only or disabled-adoption guard first; do not leave existing automatic `--apply` active until Phase 11. Verify guard offline and preserve current selection. Phase 11 later completes unified evidence/adoption behavior.
- [x] Define versioned protocol contract: development/confirmation/live roles; season/window weights; scored deadlines; issue cutoff; six-GW horizon and season-end clipping; native rules; one anchor; Strategic settings; chip calendar; quality policy; forecast guards; statistical procedure; approval references.
- [x] Define immutable identities before caches/registries: model source dependency closure and dirty-source digest, parameters/training policy/seed, input manifests, feature/scoring code, forecast schema, anchor, rules/calendar, solver binary/version/options, evaluation/statistics implementation, and protocol. Model name alone never identity.
- [x] Define evaluation/result schemas with scientific verdict, separate execution status (`not_run`, `partial`, `censored`, `complete`), reasons, evidence completeness, admitted limitations, and timestamps. Partial/deferred execution cannot Pass; explicit data/causal/contract failure cannot become demonstrated model Fail.
- [x] Specify append-only execution manifests for calibration and implementation verification; distinguish these from actual Candidate confirmation attempts. Preserve failed/interrupted attempts instead of replacing files with favorable reruns.
- [x] Define required output bundle and checksums: source/admission manifests, forecast IDs, initial state, per-deadline pre/post state and actions, solver certificate, gross/hit/net scores, guard metrics, uncertainty, registry references, and human decisions.

Acceptance: schema examples cover successful, incomplete, invalid, and inconclusive synthetic runs; every operational entry point assigned migration owner; unresolved numerical fields remain explicitly unapproved rather than filled with old constants.

Validation when implemented: focused schema/serialization tests in proposed `tests/test_evaluation_protocol.py`; round-trip fixtures, unknown-version rejection, missing-identity rejection. No model/backtest run needed for this checkpoint.

Checkpoint A: review contract, required-field list, scope, and migration map. Technical schema choices resolved by implementation evidence; settled Q1-Q28 choices retained.

### Phase 1. Admit causal data and native-season applicability

Dependencies: Phase 0 identities. Admission precedes anchor construction and any interpretable trajectory.

Likely seams: `features/availability_snapshots.py`, `features/season_archive.py`, `features/vaastav_archive.py`, `backtesting/archive_static.py`, `features/builder.py`; proposed `backtesting/data_admission.py`. Extend foundation audit tooling rather than treating existing coverage audit as admission proof.

- [x] Produce per-season, per-origin coverage/applicability matrix: opening ownership, price, position/club/eligibility, deadline, complete player universe including blank-GW players, as-of fixture schedule, availability, seed/training history, outcomes, measurable components, and native rules. Fields classified required, permitted limitation, inapplicable, or unavailable before model results.
- [x] Preserve existing narrow positive finding: three fplcache opening payloads have pinned full commits, matching compressed SHA256, valid content checks, and recorded UTC commits before payload GW1 deadlines. Reuse `ownership_snapshot_samples.csv` and `ownership_snapshot_provenance.csv`; do not reclassify these as full-season or exact-lock snapshots.
- [ ] Resolve freshness/eligibility admission from source evidence. Record source publication/capture semantics, mirror limitations, snapshot age and cutoff, eligible IDs/positions/clubs, removals/arrivals, price units, ownership denominator/rounding, and deterministic latest-admissible selection. Present proposed freshness limits in Phase 8 where quantitative preference required.
- [ ] Pin acquired raw bytes and processed manifest: immutable source URL/full commit/blob identity, source timestamps and uncertainty, retrieval time, payload deadline, compressed/decompressed hashes as applicable, parser/schema version, transformed table hashes, and parent manifest. Never depend on moving `main` for reproduction.
- [x] Keep acquisition separate from tests. Actual research acquisition may use network after execution scope approved; tests use checked-in small fixtures/HTTPX mocks and never request real HTTP.
- [ ] Establish complete per-origin fixture/price/universe/availability source coverage. Opening bootstrap admission alone insufficient for six-GW rolling replay. Fixture schedule must be what was knowable at issue time, including postponements and announcements; later realized schedule belongs only to scoring side.
- [ ] Trace terminal/future fallbacks through `point_in_time_players`, `bootstrap_from_processed`, `prices_at_deadline`, `_owned_meta`, and feature fixture maps. Replace promotion-path fallbacks with admitted as-of inputs or explicit invalid reasons. A player's first future performance row cannot establish earlier eligibility/price/club.
- [x] Distinguish known blank, known DNP, unknown schedule, missing forecast, missing outcome, postponed fixture, and not-yet-final outcome. Zero valid only for established zero event/blank/DNP under complete coverage; absent records remain missing.
- [x] Retain fixture grain for DGWs; ownership/price stock fields collapse under declared as-of semantics, never sum across fixtures. Require consistent player/fixture/GW keys and ID mapping, including seed-season identity mapping.
- [x] Register native scoring/rules support by season. Explicitly handle 2024-25 Assistant Manager exclusion: either no use in registered shared policy, with claim limited to supported policy, or separate future extension. Do not claim unrestricted full-chip support or implement unused Assistant Manager by default.
- [x] Publish deterministic admission report with reasons and blockers. Permitted Q13 limitations must have controlled known leakage and complete required inputs; disclose model-dependent effects of missing availability. Disclosure alone cannot admit known leakage.
- [x] Route any needed historical reconstruction through snapshot tooling into separately versioned output; flag migration/regeneration proposal for review. Never edit/delete existing archive Parquet files directly. Store research companions under topic folder, execution outputs under `data/reports/`.

Acceptance: every requested replay origin has explicit admission outcome and input hash chain; unavailable windows cannot silently shrink; altered hash/timestamp/universe fails admission; sealed paths rejected before reading. Partial source coverage yields explicit feasibility limit, not policy-value result.

Validation when implemented: `uv run pytest tests/test_availability_snapshots.py tests/test_feature_leakage.py tests/test_snapshot_season.py` plus proposed `tests/test_data_admission.py`; fixture cases for late source, future arrival, missing blank player, DGW stock disagreement, unknown fixture, corrupt hash, and sealed-path rejection. Admission tests offline.

Checkpoint B: approve concrete admission/application proposal and remaining acquisition scope. If full required coverage unavailable, continue synthetic engine verification; withhold empirical promotion claim.

Checkpoint outcome: synthetic admission engineering accepted by both phase-named reviewers. Remaining unchecked items are explicit follow-through: empirical freshness/eligibility and complete per-origin coverage remain blocked/unverified; acquired raw packages remain unadmitted; native rule versions registered in Phase 2; strict forecast/replay adapters replace legacy fallbacks in Phases 3/5/11. No actual promotion evidence permitted until these conditions are met. Checkpoint B bounded acquisition approved; synthetic engine verification may continue under original plan.

### Phase 2. Specify state transitions and season-aware scoring

Dependencies: Phase 1 coverage/rule inventory. Specification and known-answer fixtures precede full replay.

Likely seams: `backtesting/transfer_plan_walkforward.py`, `backtesting/strategy_policy.py`, `backtesting/decision_regret.py`, `models/scoring_matrix.py`, `solver/planning.py`; proposed pure `backtesting/replay_state.py` and season-rule contract. Keep one authoritative scoring-weight source; pass explicit rules version rather than duplicate constants.

- [x] Define full replay state: owned fifteen, acquisition prices, sale entitlements/current market prices, Money in the Bank, FT balance, transfers already made/penalties, available/used/expired chips, chip window, temporary squad restoration, deadline index, and parent-state hash.
- [x] Define atomic transition: validate causal decision and legality -> apply transfers/finances/chip -> freeze lineup/bench/captain/vice -> score completed immediate GW -> deduct official hits exactly once -> restore temporary state/advance native FT/chip state. Only validated complete transition becomes resumable checkpoint.
- [x] Specify initial anchor spending and bank in integer tenths; total initial capital equals acquisition spending plus bank. No full-budget credit on top of owned squad. GW1 transfers forbidden after reference lock, without consuming artificial Wildcard; GW2 FT starts from actual season rules.
- [x] Encode native FT caps/accrual, transfer penalties, Wildcard/Free Hit interactions, chip availability/expiry windows and restoration rules for each admitted season. Reject unsupported chip/calendar combinations before solve.
- [x] Specify purchase/sale profit rounding, price falls, retained acquisition value, re-buy after sale, temporary Free Hit finances, and bank conservation. Current price is not automatically acquisition or selling price.
- [x] Specify legal lineup and ordered autosubs, goalkeeper substitution, formation preservation, appearance across DGW fixtures, captain/vice fallback, Triple Captain, Bench Boost, and complete-DNP/blank behavior. Separate official match score, captain/chip increment, and penalties.
- [x] Audit native projection conversion as well as observed scoring. `models/scoring_matrix.py` has fixed current constants and no season argument; callers in component/hybrid models and actual-component reconstruction must use registered season scoring semantics. Unsupported historical event definitions must be declared rather than fabricated from current rules.
- [ ] Register chip subset and shared calendar construction using only deadline-known information. A native-rule-correct policy may choose no Assistant Manager; it must disclose that scope. Independent model chip timing remains separate experiment.
- [x] Write human-readable transition examples with independently computed expected values before engine implementation. Version examples alongside source rule references under durable testing/rules documentation.

Acceptance: complete state sufficient to reproduce next decision without hidden global settings; rule applicability explicit for every admitted season; deterministic fixture expectations for finances, FT, chips, and scoring agreed before trajectory results.

Validation when implemented: proposed `tests/test_replay_state.py` plus `tests/test_scoring_matrix.py` and lineup/EGS tests. Known answers cover price rise with half-profit rounding, price fall, sale/re-buy, bank conservation, hit, FT cap differences, WC/FH restoration, chip expiry, BB/TC, captain DNP, GK/outfield autosub ordering, and DGW appearance. Include invalid duplicates, wrong position/club count, overspend, stale state, illegal chip and missing outcome.

Checkpoint C: state/rule correctness review. Returning plausible points from old helper is insufficient acceptance.

Checkpoint C outcome: both named reviewers accepted scoped native engineering; parent focused suite 139 passed, stable full suite 772 passed, Ruff clean, new-core/test Pyright clean. Registered four-chip subset and legal-calendar validation implemented. The remaining unchecked item includes causal shared-calendar/source adapter construction, owned by Phases 3/5/8; dates and empirical applicability are not inferred from fixtures. Historical card-only/inherited-club exceptions fail closed. No empirical replay or promotion claim.

### Phase 3. Build causal issue-by-target forecasts and reproducible storage

Dependencies: Phases 0-2 contracts and admitted inputs. Forecast generation independent of model's evolving squad where information identical.

Likely seams: `features/builder.py`, `features/contracts.py`, `backtesting/walkforward.py`, `backtesting/walkforward_solve.py::_project_deadline`, `models/base.py` and scoring call sites, `projections/exporter.py`; proposed `backtesting/forecast_store.py`.

- [x] Extend forecast identity/grain to model × issue deadline × target GW/fixture × player, with horizon lead, common information cutoff, training cutoff, source manifests, rules/scoring version, and generation implementation.
- [x] Generate all six target forecasts from one issue cutoff. Future target selection cannot advance training history, choose a later snapshot, import later injury news, or use revised fixture schedule. Fit once per issue where model contract permits; record any necessary per-target work.
- [x] Preserve existing This-Season Evidence/Prior-Season Seed behavior while making cutoff and seed identity explicit. Prevent future rows and full-season fit fallbacks. Oracle-minutes paths visibly diagnostic and excluded from final evidence.
- [x] Validate projected totals, minutes, component coverage, finiteness, row uniqueness, population, and native-score reconciliation before export. Emit known-blank zero rows only from established schedule state.
- [x] Make promotion export strict. `pad_solver_csv_horizon` currently fills absent target columns with zero; required forecasts must instead be complete or fail with origin/target reason. Any retained product convenience padding stays explicitly outside evidence path.
- [x] Store immutable forecast tables plus manifest atomically; content address material identity, not filename/model label. Retain generator logs and coverage report. Produce solver CSV as derived artifact tied to same forecast ID, preserving DGW aggregation and native prices/clubs.
- [x] Cache causal features/fits/forecasts separately from squad-dependent solves. Identical issue inputs can be shared across anchors/arms; model forecasts cannot be reused across changed source, training, parameters, rules, cutoff, or target schedule.
- [x] Add reproducible replay problem key including forecast ID, full starting state, anchor/calendar/policy, native rules, solver options/version and quality requirements. A matching action or CSV filename never cache proof.
- [x] Store/resume per-deadline artifacts atomically from last validated transition; verify parent state and hashes. Reject corrupted/stale/incomplete cache, record hit/miss, and retain interrupted attempt identity.

Acceptance: clean rerun gives identical forecast/problem IDs and equivalent content; mutation of each material identity invalidates cache. Changing post-cutoff fixture/news/outcome records cannot alter any forecast issued before cutoff. Missing required target never becomes zero forecast.

Validation when implemented: `uv run pytest tests/test_feature_leakage.py tests/test_projection_parity.py tests/test_export_price_delta.py` plus proposed `tests/test_forecast_store.py`. Cover same-issue multi-target causality, DGW/blank/unknown schedule, missing sixth target, changed seed/rules/options, corruption, atomic interruption, and deterministic reload. Compare current-rule projection parity on fixed fixtures before accepting intended native-season differences.

Checkpoint outcome: causal issue forecasts, reproducible content-addressed storage, strict solver CSV export, and atomic replay checkpoint transitions accepted by both phase-named reviewers. 41 focused tests pass, Ruff clean, new-core types clean. Coverage report and generator log persistence/verification integrated into forecast cache. Padding in backtesting solver export strictly prohibited via runtime call-stack inspection. Synthetic offline integration validated across end-to-end admission, fit, prediction, manifest generation, and checkpoint transition. Empirical coverage and admission remain follow-through in Phase 4/5/8; sealed holdout 2026-27 untouched; Champion unchanged.

### Phase 4. Construct and freeze neutral GW1 anchor

Dependencies: admitted opening snapshot, native rules, manifest format. Independent of Candidate/Champion forecasts and outcomes.

Likely seams: reuse constraint-building ideas from `backtesting/metrics.py::select_top_15_squad` only where strict; proposed `backtesting/ownership_anchor.py`. Existing weekly XI/top-fifteen metrics are not primary anchor implementation.

- [x] Solve binary ownership maximization over admitted GW1 universe: full fifteen, 2 GKP/5 DEF/5 MID/3 FWD, initial £100m cap, max three per club, native eligibility. Ownership remains objective, price affordability constraint; no ownership/price ratio or model score.
- [x] Use exact parsed reported-ownership precision and deterministic secondary tie procedure independent of forecasts/outcomes, such as lexicographic stable player IDs after primary optimum fixed. Demonstrate secondary step cannot sacrifice ownership objective through arbitrary epsilon perturbation.
- [x] Record solver feasibility/optimality certificate, objective, constraints, tie version, selected IDs, acquisition prices, bank, source hashes and anchor ID. If highest-owned optimum not certified, report incomplete construction rather than quietly label approximate squad highest-owned.
- [x] Freeze one anchor per admitted season before Candidate outcomes. GW1 lineup/captain choice may differ by model; fifteen and acquisition state identical. No empty-squad/preseason redraft permitted.
- [x] Validate anchor independent of source row ordering and model selection. Document ownership-overlap interpretation without manager-population representativeness claim.
- [x] Keep optional later anchors/calendars under separate diagnostic IDs and report labels. Do not make old three-start workload rows mandatory or include local-reset totals in continuous score.

Acceptance: small brute-force known answer matches optimizer; real admitted anchor has legal full fifteen, nonnegative bank, conserved initial capital, neutral deterministic ties, and valid certificate. Infeasible source yields actionable admission/anchor failure.

Validation when implemented: proposed `tests/test_ownership_anchor.py`; greedy counterexample, club/budget/position interaction, rounded ties, shuffled rows, duplicate/missing metadata, infeasible universe, and forecast-independence test. Actual anchor construction is research execution, distinct from offline tests and separately recorded.

Checkpoint outcome: neutral GW1 ownership anchor construction and freezing accepted by both phase-named reviewers. 11 unit tests pass in 0.64s; Ruff clean; Pyright clean with 0 errors. Mathematical ownership-overlap interpretation and manager population disclaimer documented in module header. Exact two-stage lexicographic tie-breaking (`min sum log(1+pid)*x` over certified optimum $Z^* - 10^{-7}$) proves non-sacrifice on exact reported ties. Invariant to row ordering; actionable `InfeasibleAnchorError` on invalid or unaffordable universe. Diagnostic anchors separated by type and ID prefix. Actual historical anchor construction is research execution; no empirical candidate outcomes evaluated.

### Phase 5. Implement and verify independent rolling replay

Dependencies: verified rules/state, forecasts, anchor, and source admission. No Candidate efficacy conclusion at this stage.

Likely seams: `backtesting/transfer_plan_walkforward.py`, `backtesting/walkforward_solve.py`, `backtesting/archive_static.py`, `backtesting/decision_regret.py`, `solver/solver.py`, `solver/planning.py`, `solver/scenarios.py`, `solver/transfer_plan.py`; proposed replay persistence within Phase 3 store or small dedicated module.

- [x] Replace promotion adapter's squad-ID/FT-only callback with explicit complete-state input and decision/certificate output. Preserve or explicitly version old first-half research command behavior; no silent reinterpretation of published ADR 0020 results.
- [x] Correct verified old behaviors: five-GW horizon, forced empty GW1 redraft/Wildcard, £100m bank default at every deadline, purchase/selling prices reset to current price, empty chip history, no hit accounting, and missing outcomes defaulted to zero.
- [x] Apply six-GW Strategic settings through shared scenario override path; freeze all effective preferences, pruning, discounting, bench/FT/bank values, hit rules, iterations, and native-rule options. Same settings for compared projection models. Late-season horizon clipping explicit, without dropping final scored deadlines.
- [x] Maintain independent Candidate and Champion state after common anchor. Feed each model's own squad, bank, acquisition/sale values, FT, chip history and prior penalties into every subsequent solve. Execute only immediate decision; discard tentative later actions when replanning.
- [x] Enforce one shared causal chip calendar including GW1 lock compatibility and native windows. Restore Free Hit permanent squad/value state; apply WC/FT behavior by native season. Reject unsupported chip use before optimization.
- [x] Make solver results structured: feasible incumbent, objective, objective bound, absolute/relative gap, termination status, runtime/limit, threads/seed/version, requested quality, and effective Strategic audit. Validate incumbent constraints and finance independently before accepting transition.
- [x] Distinguish certified-quality research policy from deployed time-capped policy. Both need explicit feasible/infeasible/timeout treatment; equal runtime is not equal solution quality. Missing required certificate cannot count as model loss or disappear from schedule.
- [x] Use strict outcome coverage and native lineup scoring; derive gross score, chip/captain adjustments, official hit cost and net score transparently. Every registered deadline accounted for, including equal/zero differences and difficult solves.
- [x] Persist pre/post state, transfers, exact lineup/bench/captain/vice, chip action, certificate, inputs, and per-deadline outcome provenance. Allow audit to recompute net totals without solver.
- [x] Exercise crash/restart, resume, invalid decisions, partial outcome publication, and cache changes. Freeze versioned failure policy before empirical finalist runs; no rerunning only unfavorable deadlines under changed settings.

Acceptance: multi-GW offline fixture produces independently computed final squad, finances, FT/chip state, penalties and net points; two model policies diverge and retain consequences; identical policies remain identical. Continuous score reconstructs from saved trace; no missing deadline or hidden fallback. Engine correctness does not assert historical inputs fully admitted.

Validation when implemented: `uv run pytest tests/test_transfer_plan_walkforward.py tests/test_walkforward_solve.py tests/test_transfer_plan_walkforward_cli.py tests/test_transfer_plan_scenarios.py tests/test_transfer_plan.py` plus Phase 2/3 tests and proposed `tests/test_replay_integration.py`. Include small local HiGHS known-answer problem and independent scoring/state oracle; mock broad runner tests to avoid costly season jobs or external HTTP. Compare solver/accounting output to existing production serialization on common supported fixtures; explain intended differences.

Checkpoint D: engine correctness and reproducibility review. Only corrected intended-policy problems may become interpretable profiling/replay evidence. Any earlier artificial problem timings labeled workload proxy.

### Phase 6. Add substantive projection guards and staged diagnostics

Dependencies: causal forecast/outcome contracts; Phase 5 for decision diagnostics. Numerical margins remain pending Phase 8.

Likely seams: `backtesting/walkforward.py`, `backtesting/metrics.py`, `backtesting/promotion.py`, `backtesting/process_points.py`, `features/contracts.py`, component attribution helpers; proposed `backtesting/projection_guards.py`.

- [x] Define common population, unit, horizon leads, aggregation/weights, native targets, eligibility and missingness policy for total points, expected minutes, and each measurable event component. Candidate cannot choose its own evaluation mask.
- [x] Retain squared-error metric appropriate to conditional-mean point forecast; report bias/calibration and useful descriptive errors. Select component metrics appropriate to target type, with formula, units, direction and ideal benchmark in durable metric definitions.
- [x] Declare season/component applicability before finalist. Distinguish genuinely inapplicable native component, unavailable measurement, and required-but-missing guard. Unsupported component explicitly unassessed; required missing evidence prevents Pass.
- [x] Reconcile total to component ledger under native scoring; verify minutes and component semantics rather than treating accounting sum as accuracy evidence. Oracle-minutes experiments diagnose mechanisms only.
- [x] Implement non-inferiority claims against approved meaningful margins and uncertainty procedure. Absence of statistically significant deterioration is insufficient proof of acceptable regression. Do not impose every-component improvement.
- [x] Separate optional cheap forecast/lineup/shared-state screens from final safeguards. Deferred or failed prioritization screen does not automatically yield demonstrated Fail/Dead Lever; allow full-replay route for mechanisms screen cannot assess.
- [x] Add bounded Unconstrained development diagnostic with separately reported evidence. Predeclare substantial-reversal investigation across forecasts, penalties, transfers, solver quality and state/calendar interactions. Strategic primary cannot be selected or averaged away after outcomes.

Acceptance: fixture with reconciling but wrong components fails applicable guard; missing required metric cannot Pass; small uncertain differences remain distinguishable from demonstrated harm. Guard outputs contain estimates, margins, uncertainty and coverage, not only booleans.

Validation when implemented: `uv run pytest tests/test_promotion.py tests/test_component_attribution.py tests/test_projection_parity.py` plus proposed `tests/test_projection_guards.py`; population invariance, applicability, missingness, horizon separation, non-inferiority boundary and uncertainty cases.

### Phase 7. Profile corrected policy within bounded development-only experiment

Dependencies: Checkpoint D, forecast cache/resume verification, admitted development cases. Champion only; no new Candidate lever or confirmation/holdout access.

Likely seams: small module CLI such as proposed `commands/profile_transfer_replay.py`, Phase 3 manifests/store, `solver/solver.py` certificate collection. Companions in foundation topic; large execution traces under `data/reports/`.

- [x] Prepare concrete profiling manifest for review before execution: preselected ordinary, constrained-budget, transfer-heavy and supported chip-enabled development problems; no selection using realized policy outcomes.
- [x] Start with preflight's proposed envelope: maximum 20 optimizer calls, 30 seconds/call, one thread, serial, maximum 20 minutes elapsed including feature/model work. These remain proposed probe limits until reviewed; they are neither adopted finalist budget nor power/full-runtime guarantee. Count every actual optimizer call and report unfinished sample coverage.
- [x] Register paired identical-input quality probes before calls: exact-target setting versus explicit approximate targets, with absolute and relative objective gaps and immediate-action comparison. Trial tolerances remain probe settings, not adopted thresholds.
- [x] Record machine/runtime/HiGHS versions, source/data/protocol IDs, features, fitting, projection, MILP assembly/solve, scoring/report/I/O time, peak memory where measurable, feasible rate, bound/gap, termination/censoring, chosen first action, and cache costs/hits.
- [x] Measure cold/warm forecast/Champion-path cache and interrupted-path resume. Separate reusable model/issue work from squad-dependent solve cost; test contention before proposing parallelism.
- [x] Report complete versus censored timings and difficult/chip cases individually. Predominantly timed-out probe cannot establish reliable mean full-solve time or overnight completion.
- [x] Regenerate workload projection from measured distributions and actual path lengths. Existing `estimate_workload.py`/`workload_scenarios.csv` remain labeled assumptions until explicit measurement integration; one primary anchor, one primary arm. Separate anchor solve, GW1 lineup and later transfer-job costs.
- [x] Propose common research-quality tolerance, runtime cap, infeasible/timeout treatment and compute envelope from measured action sensitivity/cost. Objective-gap certificate bounds forecast objective only, never actual FPL points.

Acceptance: reproducible measured report or explicit infeasibility/censoring report, with scope and extrapolation limits; no claimed Candidate win or statistical power from cost probe. Widening initial probe requires concrete revised scope review.

Validation when implemented: offline profiler tests with fake clock/solver result; call/time caps, interrupted output, certificate absence and no hidden retry. Actual profiling command run only after reviewed manifest; record exact invocation/output. No profiling executed during plan drafting.

Checkpoint E: review performance evidence and proposed certified-quality/deployed-runtime policies. Separate cost feasibility from scientific validity.

### Phase 8. Research, calibrate, and approve numerical/statistical protocol

Dependencies: admitted development evidence, verified score/guard panel, performance report. No confirmation/sealed evidence for calibration.

Likely seams: `backtesting/promotion.py` bootstrap helpers; proposed `backtesting/evidence_statistics.py`; deterministic companion runners and proposal under foundation topic. Methods assessed against authoritative primary references during implementation research.

- [x] Define estimand and scope: continuous net-score advantage under registered Strategic policy/one anchor; per-season/state harm claims; forecast non-inferiority; season/deadline weights; incomplete-season treatment; generalization limits. Benchmark improvement does not establish all-manager benefit.
- [x] Inventory already inspected seasons, prior search and outcome access. Treat historical reuse honestly; renaming, changing wrappers or making one-at-a-time comparisons cannot restore untouched confirmation.
- [x] Propose justified constituent tests/intervals and recommendation rule. Explicitly address Q17 global-null/weak wording versus mixed helpful/unhelpful Candidates and stronger protection; distinguish mathematical guarantee, conditional assumptions and empirical diagnostics. Present coherent supported proposal for approval, not statistical-algorithm questionnaire.
- [x] Define comparison family, attempt identity, error-budget scope over rounds/renames/parameter changes, adaptive selection/reviews and stopping rules. One finalist per round narrows workload but does not itself control repeated testing. Multiplicity correction cannot repair invalid single tests or leaked confirmation.
- [x] Preserve paired calendar dependence, season boundaries and zero differences. Correlated starts/overlapping branches share outcomes; resample common calendar indices if using saved-score sensitivity. More bootstrap draws never create independent seasons.
- [x] Implement stored-score resampling only for conditional sensitivity/inference under stated assumptions. No solver per bootstrap draw. Shuffled fixed-path score blocks are not coherent alternate seasons or complete training uncertainty.
- [x] Validate implementation using controlled global-null, mixed-null, known gain/harm, correlation, small-sample, inactive-period, missingness and repeated-review scenarios. Simulation calibration useful diagnostic; no football-world guarantee inferred merely from passing synthetic tests.
- [x] Evaluate power/identifiability for small positive gains without inventing minimum practical-gain floor. Report effects that may remain undetectable and between-season uncertainty unsupported by few seasons.
- [x] Produce Q21 proposal with practical units: per-season/state material-loss limits; total/minutes/component non-inferiority margins, population/horizons/coverage; statistical evidence thresholds; solver quality/runtime; chip-calendar dates; weights; source freshness and live review/evidence rules. Explain trade-offs and development-only evidence for each setting.
- [x] Separate human risk preferences from empirical measurement. Noise can inform attainable precision, not acceptable harm. Never copy existing bootstrap bars/segment floors/live percentage thresholds into new protocol as pre-approved values.
- [x] If evidence cannot support agreed standard, specify Inconclusive route and registered fresh-confirmation design. Propose exact future window, capture/review rules and sequential/fixed-look treatment; preserve current seal unless separate explicit amendment approved before access.
- [x] Obtain explicit human approval of concrete protocol and numerical limits; freeze version/hash and approval record before finalist evaluation or any proposed locked-lever rerun. Unapproved/unsupported fields keep recommendation capability disabled.

Acceptance: reviewable protocol states actual risk claim, assumptions, attempt-family rule, evidence limitations, approved tolerances, and honest unsupported/Inconclusive route. No arbitrary bootstrap-positive fraction presented as 5% guarantee. Approved freeze precedes results it governs.

Validation when implemented: proposed `tests/test_evidence_statistics.py` plus relevant `tests/test_promotion.py` cases; deterministic known-answer statistics and dependence/coverage boundaries. Controlled simulations recorded separately from unit tests and from empirical Candidate evidence.

Checkpoint F, human approval: numerical/statistical protocol. Any stronger-than-Q17 risk policy explicitly approved as amendment; unsupported promised guarantee remains unresolved rather than silently weakened. Current Champion unchanged.

### Phase 9. Implement confirmation admission and immutable attempt registry

Dependencies: approved Phase 8 protocol; Phase 0 identity and evidence store. Infrastructure verified with fixtures before any actual finalist admission.

Likely seams: `backtesting/model_evaluation.py::build_evidence_record`, `write_promotion_evidence`, `commands/evaluate_model_promotion.py`; proposed `backtesting/confirmation_registry.py`. Proposed durable append-only companion under protected `docs/research/candidate-ledger/`, with full bundles under `data/reports/promotion_evidence/<evaluation_id>/` and durable manifest references.

- [ ] Record one frozen finalist per confirmation round: model dependency/source hashes, parameters/training/seed, dev selection record, data/protocol IDs, states/calendar/windows, solver/statistical settings, and prior family history. Include generated/uncommitted source content in freeze artifact when applicable.
- [ ] Define registry append/lock/atomicity and integrity checks. Record registration, not-run/partial/censored/complete attempts, changes, withdrawals, reruns, consumed evidence/review budget and approvals. Alias/model rename links to same mechanism/family history.
- [ ] Require declared mechanism family and parent-attempt links with reviewable history. Enforce known aliases/fingerprints and declared-family continuity; do not promise automatic semantic equivalence detection for arbitrarily rewritten models. Mechanism novelty/ledger screening remains an explicit review responsibility.
- [ ] Prevent duplicate/adaptive confirmation runs through every entry point; require registered freeze and admissible unused/fresh evidence. A changed model/protocol needs new declared attempt, not overwrite of old result or reset history.
- [ ] Separate historical development/robustness labels from prospective confirmation. Enforce sealed-path/data-role checks before loading outcomes. Approved prospective protocol cannot implicitly unseal 2026-27 GW6+.
- [ ] Execute complete registered schedule only when actual finalist/evidence access separately authorized and admitted. Report all failures/hard GWs. Ordinary fixed-sample intervals cannot justify stopping when result first favorable.
- [ ] Store raw paired score panel and guards, full identities, source/data admission, execution status, scientific verdict/reasons and approval context. Frozen source/data/protocol changes invalidate adoption eligibility while preserving prior evidence.
- [ ] Preserve current Candidate Ledger rows and lock semantics until Phase 13 policy adoption. Read ledger before proposing any new lever; explicit individual reopening required before locked mechanism runs. Infrastructure fixtures use toy data/policies, not disguised locked lever evaluations.

Acceptance: fixture-driven confirmation round can register, resume, close and reproduce evidence; renamed model cannot bypass history; changed hash/consumed evidence/repeated look/unauthorized seal fails before analysis. Actual fresh result not required for infrastructure delivery.

Validation when implemented: proposed `tests/test_confirmation_registry.py`; concurrent duplicate registration, interrupted append, stale source, alias, replayed approval and protocol mismatch. Mock final evidence supports each verdict/status combination without real Candidate/season run.

### Phase 10. Prepare prospective capture, shadow replay and live review

Dependencies: approved live protocol, immutable forecast store, stateful replay and attempt identities. Required readiness before provisional adoption; actual evidence accrues later.

Likely seams: `commands/run_model.py`, `commands/refresh_data.py`, `features/availability_snapshots.py`, `backtesting/model_evaluation.py`, `backtesting/promotion.py::classify_live_lead`; proposed small live-capture/review module and command after entry-point inventory.

- [ ] Implement scheduled pre-deadline capture specification: common input snapshot/cutoff, model versions, total/minutes/component forecasts, issue × target rows, frozen policy/settings and immutable timestamps. Late/missed capture explicitly inadmissible, never retrospectively reconstructed as prospective.
- [ ] Maintain separate shadow Transfer Plan state for provisionally adopted and former Champion, with registered shared start/calendar and independent later finances/actions. Record benchmark scope; optional actual-context shadow comparison separately labeled and not mandatory personal-squad gate.
- [ ] Define operational schedule/ownership, retry/cutoff policy, outcome-finalization delay and missing-job alerts. Prepare concrete job definition and dry-run with fake clock; activate future capture under approved execution scope, without reading sealed outcomes.
- [ ] Implement approved fixed review points or valid sequential procedure, sufficient-evidence conditions, drift/operational-defect handling and rollback recommendation. Elapsed time or one bad week alone cannot validate/reject model.
- [ ] Keep adopted and former Champion source/forecasts recoverable for comparison and rollback. Material-harm recommendation cites bundle/hash and requires explicit human adoption/rollback approval.
- [ ] Separate live protocol readiness, capture completeness, sufficient evidence, scientific validation and human action in status reporting. If no Candidate adopted, store ready protocol/job configuration and explicitly record prospective evidence pending.

Acceptance: offline time-driven fixture proves capture before deadline, late rejection, incomplete review, material-harm recommendation and manual rollback barrier. Live capture readiness sufficient for infrastructure checkpoint; actual statistical live validation requires later registered evidence.

Validation when implemented: proposed `tests/test_live_validation.py`; fake clock, immutable capture, missed cutoff, partial outcomes, repeated looks, frozen comparator, approval mismatch. No real scheduler/authentication/network from tests.

### Phase 11. Unify recommendation paths and require manual adoption

Dependencies: approved protocol, verified registry/evidence engine, live readiness. Operational switch waits Phase 13 formal migration; no actual adoption implied by implementation.

Likely seams: `commands/evaluate_model_promotion.py`, `backtesting/model_evaluation.py`, `backtesting/promotion.py`, `models/selection.py`, `.github/workflows/evaluate_model_promotion.yml`, `.agents/skills/explore-candidate/smoke.py` and associated skill interfaces. Production `config/model_selection.json` only changes on separately explicit adoption authorization.

- [ ] Route smoke, CLI, CI and research final recommendation through same versioned protocol/guard/admission logic. Legacy diagnostic mode can remain labeled; it cannot bypass required final evidence through single-season convenience path.
- [ ] Preserve staged exploration: cheap checks and optional screens prioritize; frozen finalist gets full registered schedule. Execution/inert-prototype defects stop as Invalid, not automatic moratorium.
- [ ] Implement four scientific verdicts and separate execution status consistently in JSON/CSV/console/report. Include all required reasons and limitations; missing metrics never default to passing.
- [ ] Make evaluation/recommendation read-only with respect to Champion selection. Existing CLI `--apply`/single-season and CI automatic commit/push routes must not mutate Champion merely from computed Pass.
- [ ] Provide separate explicit adoption action consuming approved exact evidence bundle/hash, frozen model/protocol, expected current Champion, live-readiness record and human approval. Refuse stale/mismatched/partial/invalid/Inconclusive bundle. Preserve former Champion and atomic rollback metadata.
- [ ] Change promotion workflow to evaluate/publish evidence only, remove automatic selection commit/push authority, and align required protocol arguments. Test workflow route/config statically or with mocked command; no live GitHub write needed for validation.
- [ ] Keep research-quality recommendation separate from deployed time-capped policy result. Disclose if actual product selector performs additional solves or different settings; broader product benefit requires registered deployed-policy check.
- [ ] Produce reviewer-oriented evidence report: estimand, source admissions/limitations, identities, net score/season-state losses, guards, uncertainty/search history, execution completeness, recommendation and human action required. Every custom metric documented by formula/direction/benchmark.

Acceptance: all final recommendation routes enforce same required evidence; fake Pass never changes selection; only explicit valid adoption action can update fixture selection file. Live rollback likewise needs approval. Current operational Champion stays unchanged until user adopts actual Candidate.

Validation when implemented: `uv run pytest tests/test_evaluate_model_promotion.py tests/test_promotion.py tests/test_smoke_harness.py` plus planned workflow/manual-adoption contract tests. Replace existing tests asserting automatic promotion with tests for recommendation-only and separately approved adoption. Cover legacy CLI bypass, missing confirmation, stale approval, changed Champion and no side effects.

Checkpoint G: review migration diff and concrete manual-adoption interface. No new questionnaire on libraries or numerical methods; present implemented behavior and evidence.

### Phase 12. Audit legacy verdicts using recorded evidence only

Dependencies: verdict taxonomy and existing recorded artifacts. Can run independently of empirical replay/calibration; no locked lever rerun.

Likely sources: `docs/research/candidate-ledger/candidate_ledger.csv`, `candidate-ledger.md`, recorded promotion bundles/research companions, old protocol/code identities. New audit companion within foundation topic; original rows/results untouched during audit.

- [ ] Inventory legacy rows and evidence references; distinguish original metric/protocol objective, execution defect/inertness, missing evidence, unsupported inference and valid negative finding. Do not claim known fallback actually affected published result without trace evidence.
- [ ] Preserve original figures, dates, source/protocol identity and current locks. Record audit classification and confidence separately; missing evidence remains missing rather than recomputed result.
- [ ] State valid negative result does not prove mechanism permanently bad; one-year lock remains resource-governance policy. Invalid/Inconclusive classification alone cannot silently reopen existing row.
- [ ] Produce individually scoped reopening proposals only when justified, naming exact ledger row/mechanism, evidence concern, allowed rerun/protocol and existing lock. Obtain explicit user words before any locked mechanism retried.
- [ ] Cross-link durable audit companion and report schema; approved future amendments append provenance rather than rewrite historical scientific result.

Acceptance: audit reproducible from recorded evidence; no model/solver/backtest rerun; original ledger and Champion unchanged except separately approved administrative amendments. Unresolved legacy record does not block correct new-engine infrastructure delivery.

Validation when implemented: offline parser/classification fixtures only if reusable audit code introduced. Reconcile audit row counts and reference existence; do not write tests merely mirroring one-off prose edits.

### Phase 13. Adopt durable documentation and workflow/skill migration

Dependencies: approved quantitative protocol and verified implementation behavior. Documentation draft can evolve earlier; accepted status must describe what actually exists.

- [ ] Prepare focused ADR documenting new primary net-score replay, forecast guards, evidence/verdict distinction, search/confirmation protocol, manual authority and supported native-rule scope. Explicitly amend/supersede conflicting parts of ADR 0044/0046/0047/0049/0054/0062/0064; retain unchanged sealed boundary unless separately amended. Old ADRs stay in place with lifecycle links.
- [ ] Reconcile ADR 0020 first-half diagnostic versus new six-GW continuous gate; preserve original research results under original protocol. ADR 0065 Strategic constants currently Proposed: freeze actual effective settings with explicit status instead of treating proposal label as numerical approval.
- [ ] Update `docs/research/INDEX.md` Eval canon, `docs/testing/archive-testing.md`, relevant `docs/rules/` documentation and model methodology only after protocol adoption. Remove contradictory automatic/single-season promotion guidance from active surfaces.
- [ ] Update only resolved domain definitions in `CONTEXT.md` through repository domain-modeling workflow; record implementation state in `docs/agents/current-state.md`, phase completion in `ROADMAP.md`, issue/work record through `docs/agents/progress.md`. Plan never becomes glossary or operational canon.
- [ ] Migrate explore/ideate skills and smoke/report contracts to new stages, statuses, required registry and manual adoption. Keep Dead Lever screen and individual reopening rule. Update agent instructions/commands only when interface changed, using writing-for-agents guidance.
- [ ] Keep research rationale, approved protocol/calibration proposal, source manifests, data-admission audit companions, rule/transition examples, profile evidence, legacy audit and decision records durable in correct topic/testing/rules locations. Quantitative note caches regenerated from named companion cells; no copied numerical snapshots as authority.
- [ ] Document operator workflow: register -> capture/generate -> verify/admit -> replay -> evaluate -> recommend -> human adopt -> prospective review/rollback. Include reproduction commands, cache identity, failure recovery, supported seasons/components/chips and evidence limitations.
- [ ] Complete cutover atomically enough that CLI/CI/skills/docs cannot advertise conflicting final gates. If phased release necessary, expose explicit protocol version and disable adoption until full migration accepted.

Acceptance: active docs/entry points agree on implemented protocol and manual authority; old results traceable; no accidental change to sealed data, current locks or Champion. Durable docs distinguish infrastructure ready from Candidate evidence pending.

Validation when implemented: inspect relevant documentation links and stale-constant/automatic-adoption references with `rg`; run impacted schema/CLI tests. No need to test reversible prose independently.

Checkpoint H, human review: formal protocol/cutover approval. Pending quantitative approval, fresh confirmation or adoption action remains explicit, never disguised as completed scientific Pass.

### Phase 14. Delivery validation, cleanup and user confirmation

Dependencies: required engineering phases accepted; conditional research/adoption outcomes honestly recorded.

- [ ] Complete all implementation acceptance checks within approved scope, or record explicit user-approved exception with exact unresolved check and consequence. Do not check unfinished approval/evidence barriers as done.
- [ ] Demonstrate infrastructure readiness with offline known-answer end-to-end protocol: admitted toy sources -> neutral anchor -> common issue forecasts -> independent rolling states -> saved scores/guards -> registry -> all verdicts -> recommendation -> manual-action barrier -> live-capture dry-run.
- [ ] Record empirical readiness separately: admitted real source coverage, measured profile, approved numerical protocol, fresh confirmation availability and actual Candidate results. Missing fresh evidence leaves recommendation Inconclusive/pending and Champion unchanged; infrastructure may still finish with validated protocol/simulation path and live capture ready. Engine delivery does not require waiting full season unless user expands scope to observed adoption/live validation.
- [ ] Verify every registered execution deadline/failed attempt accounted for; reproduce saved net totals and guards without solver; validate cache/resume identities; confirm no external HTTP made by tests.
- [ ] Run required commit-readiness commands before proposing commits: `uv run ruff check .`, `uv run pytest`, and `bash tests/verify.sh`. Use approved Python 3.14/uv environment and actual Bash for shell gate. Record environment/dependency restrictions or failures concretely; never weaken tests to manufacture readiness. Existing documented benchmark exceptions apply only if user explicitly accepts current failure, not automatically to new checkpoint.
- [ ] Review final diff/status, scope and generated files. No secret values, archive mutations, unintended selection/workflow changes or source evidence loss. Commit/push only under user-authorized checkpoint scope and repository Work Packet rules.
- [ ] Update durable tracking/docs with implemented scope, validation evidence, remaining data/protocol/evidence limitations and follow-up ownership. Complete/compact active roadmap only for finished work. Preserve needed source/evidence artifacts and unrelated conversation work.
- [ ] Remove task-created pointers to temporary implementation plan/walkthrough from durable tracking/docs; replace with durable protocol/evidence references where still needed. Verify no active operational instruction depends on deleted temporary files.
- [ ] Remove generated task scratch from `.tmp/agent/` within verified task-owned paths; preserve any separately authorized resumable exploration state or unrelated work. Delete temporary root `walkthrough.md` if this task created one. Delete finished Work Packet file per repository policy, not empty it; retain packet only for genuinely unfinished/handoff work under appropriate status.
- [ ] **Delete root `implementation_plan.md` after implementation delivery checks complete. Do not empty it, archive it as canon, or delete needed rationale/evidence with it.**
- [ ] Verify deletion explicitly, for example `Test-Path -LiteralPath implementation_plan.md` returns `False`; verify any task-owned temporary walkthrough/finished packet also absent. Record completion in durable tracking/final response after verification, since deleted checklist cannot retain evidence itself.
- [ ] Give final user confirmation: implemented scope, validation results and approved exceptions, remaining limitations/pending empirical or human decisions, whether Champion changed, and explicit statement that temporary implementation plan was deleted. Claim deletion only after absence verified.

Infrastructure completion means implemented/verified contracts, usable evaluation/reporting path, calibrated approval state honestly exposed, manual authority enforced, and prospective capture ready. Statistical Pass/adoption/live validation require actual registered evidence plus respective approval; they are never inferred from infrastructure completion.
