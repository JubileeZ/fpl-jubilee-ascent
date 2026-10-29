# Independent review of foundation decisions Q1-Q26

**Updated**: 2026-10-29T13:08:20+07:00\
**Data stamp**: Source/code review of repository `66729b15` plus uncommitted foundation documents.\
**Season**: Multi-season methodology; no archive outcome analysis or sealed evidence accessed.\
**Status**: Review findings; proposed refinements, not amendments to agreed decisions.\
**Reviewer**: GPT-6.1 Sol, xhigh reasoning, explicitly requested by user.\
**Purpose**: Challenge all decisions, identify stronger alternatives, and minimize additional human questions.\
**Related**: [Foundation reference](backtesting-promotion-foundation.md), [preflight proposal](preflight-plan.md).

## Assessment

Preserve overall direction. Strong improvements over independent weekly XI gate: actual net transfer-policy outcome, substantive forecast quality, frozen paired comparisons, manual adoption, four evidence outcomes, causal restrictions, and measured compute.

Do not treat agreement on principles as complete operational specification. Strongest unresolved matters: target recommendation policy, meaning of synthetic squad panel, complete causal multi-horizon forecast contract, and justified statistical acceptance claim.

Review performed read-only. No tests, model/solver/backtest runs, archive analysis, gate changes, or holdout access. Parent saved report afterward; no review recommendation adopted implicitly.

## Sources and method

Read foundation/preflight/workload companion; cross-check code, ADRs, and glossary. Distinguish verified implementation, scientific assumptions, practical preferences, and unmeasured facts.

Primary methodological sources accessed by reviewer 2026-10-29:

- Elmachtoub and Grigas, [Smart Predict, then Optimize](https://arxiv.org/abs/1710.08005): downstream decision quality depends on optimization objective/constraints.
- Romano and Wolf, [Stepwise Multiple Testing as Formalized Data Snooping](https://www.econ.uzh.ch/dam/jcr:ffffffff-935a-b0d6-ffff-ffffd823d949/jasa.pdf): weak/global-null versus strong family-wise error control.
- Cawley and Talbot, [Model-selection overfitting](https://jmlr.org/papers/v11/cawley10a.html): finite evaluation criteria can themselves be overfit.
- Politis and Romano, [The Stationary Bootstrap](https://doi.org/10.1080/01621459.1994.10476870): dependence assumptions behind stationary-bootstrap inference.
- Howard et al., [Time-uniform confidence sequences](https://arxiv.org/abs/1810.08240): repeated-review guarantees require explicit assumptions; no automatic power.
- Gneiting, [Making and Evaluating Point Forecasts](https://arxiv.org/abs/0912.0902): matching forecast loss to mean/other functional.
- HiGHS, [options](https://github.com/ERGO-Code/HiGHS/blob/master/docs/src/options/definitions.md): absolute/relative gaps and runtime controls.

Sources do not validate project-specific thresholds, runtime, or future model performance. Findings below remain conditional on reviewed code and stated assumptions.

## Findings and alternatives

### High: tested policy versus product claim — Q9-Q11/Q25

Fixed six-week Strategic policy/shared calendar is valid controlled comparison. It establishes projection improvement under that policy, not under every arm or full delivered recommendation procedure.

Evidence: [scenario ranking](../../../solver/scenarios.py) `rank_scenarios` sorts by `horizon_egs`; [CONTEXT](../../../CONTEXT.md) Transfer Plan Scenarios describes multiple displayed arms and manual choice. No basis to assume user always follows first-ranked arm.

**Preferred architecture:** Two evaluation tracks. Controlled projection benchmark freezes policy. Product-policy evaluation fixes and tests entire deployed procedure, including arm selection, runtime/fallback rules, and chips. Use expensive product check for finalists, not every prototype.

**Trade-off:** Single-policy comparison cheaper and easier to interpret. Retain it, but limit claims unless broader check performed. Exact adoption target requires human choice.

### High: Strategic is inherited operating policy, not proven optimal

[Archived rationale](../../archive/milp-variance-constraints/milp-variance-constraints.md) contains performance percentages and substitute guarantees without supporting experiments in reviewed note. Do not repeat as measured efficacy.

Verified [solver behavior](../../../solver/solver.py): below-minutes starter penalty flat, not proportional to deficit; bench-cover count includes goalkeepers, so count alone does not guarantee viable outfield substitute. [Scenarios](../../../solver/scenarios.py) horizon-scales several preferences. [ADR 0065](../../adr/0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md) Proposed despite code present.

Freeze actual implemented discounting, bench/FT values, penalties, pruning and tie-breaking. Extra risk/concentration preferences change optimization utility; whether they improve actual outcomes under forecast error is empirical. No evidence here establishes Strategic helps or harms.

### Blocking for full replay evidence: forecast origin/target and provenance

Explicit contract needed: every target forecast for `g..g+5` issued at deadline `g` uses history and schedule information available at `g`. Store both issue deadline and target GW/fixture. No missing future forecast padded as genuine zero.

Verified: [primary walk-forward](../../../backtesting/walkforward.py) uses horizon one. [Archive adapter](../../../backtesting/walkforward_solve.py) correctly passes single `as_of_gw=deadline_gw` for multiweek features. Review found no separate-future-history leakage in that loop.

Remaining provenance risks: terminal processed fixtures used without snapshots, first-record/terminal player fallbacks, same-GW price timing, and [exporter](../../../projections/exporter.py) future-zero padding. [Live run_model](../../../commands/run_model.py) all-season history mode cannot simply be reused for historical evaluation.

Equal future information does not guarantee bias cancels between models/policies. Distinguish real blanks, unknown schedules, missing forecasts, and absent outcomes. Restricted trustworthy windows or synthetic workload probes answer narrower questions than complete causal replay.

### Blocking for existing adapter as full replay: money/state accounting

[walkforward_solve.py](../../../backtesting/walkforward_solve.py) defaults bank to £100m at later calls without evolved bank; assigns current price as both purchase and selling price. [DeadlineWeekPlan](../../../backtesting/transfer_plan_walkforward.py) lacks persistent bank/acquisition/chip/hit state. Missing outcomes become zero in adapter.

These are verified behavior, not measured distortion of published results. Complete-management evidence requires corrected state/accounting and verification. Existing adapter timings only workload proxy unless corrected intended policy represented.

Native rules must govern projection-point conversion as well as outcome scoring/financial mechanics. [scoring_matrix.py](../../../models/scoring_matrix.py) fixed constants/no season argument require season-version audit. Scoring observed outcomes natively alone insufficient.

### High: precise statistical acceptance claim — Q17

Current wording limits false recommendations when *none* of tested Candidates improves: global-null/weak control. It leaves unspecified false adoption of unhelpful Candidate when another Candidate helps.

Recommended refinement: define protection under mixed helpful/unhelpful configurations, exact positive-effect/harm/non-inferiority claims, and error-budget scope over attempts/reviews. One finalist per round and attempt registry do not themselves control repeated testing. Multiplicity correction cannot fix invalid individual tests or restore adaptively reused data.

Technical method and assumptions are agent research tasks. Human decides practical risk/benefit preferences; avoid another quiz on statistical algorithms. No achieved error guarantee claimed by current design.

### High: saved-score bootstrap remains conditional sensitivity

Observed fixed-path total descriptive. Inference to another season requires assumptions. Ownership consequences may exceed planning horizon; expanding models, chips, native rules, and population changes undermine generic stationarity assumptions.

Preserve existing cautions: shared calendar resampling across correlated starts; keep zero-difference weeks; no extra independent seasons from multiple starts; no coherent new season produced by shuffling saved scores. Synthetic/null checks diagnostic, not proof of real-football error control.

Explore prospective registered procedure when needed. Repeated live looks need valid sequential treatment or fixed review protocol. Tiny incremental gains may remain undetectable for useful periods; no promised timetable for evidence.

### Medium/high: neutral state panel versus deployment population — Q8/Q24

Model-independent equal-weight archetypes form fair controlled benchmark, not automatically representative distribution of user's future team. Identical starts omit preseason drafting benefits; resets alter long-term objective.

Retain neutral panel for stress/robustness. Add deployment-relevant prospective shadow comparison if adoption claim is personal transfer benefit. Synthetic benchmark alone supports conditional benchmark claim.

Feasibility facts for agents: causal construction, reconstructible finances, roster diversity, and overlap after Wildcards. Human preference: benchmark performance versus personal deployment performance as primary target.

### Medium: solver quality versus deployed runtime policy — Q22

Common relative gap not identical point-scale objective tolerance. Profile absolute gap, relative gap, and first-deadline action stability.

Distinguish certified-quality research policy from actual time-limited product policy. Missing required certificate leaves first incomplete. Feasible timeout can be actual valid output of second under registered runtime/fallback rules. No discarded hard deadlines or retroactive invalidation because score inconvenient.

Objective bounds do not bound realized-point losses. Numerical tolerance choice follows profiling; no new fixed gap recommended here.

### Medium: scientific outcome versus execution status — Q5/Q19/Q23

Keep four scientific outcomes, but separately record not-run, partial, censored, complete. Deferred work not same evidence as completed inconclusive test.

Required projection guardrails need non-inferiority against meaningful margins; absence of significant deterioration is not proof deterioration acceptably small. Component applicability declared in advance.

Valid negative test does not prove mechanism permanently bad. One-year moratorium is resource-governance choice. Existing locks remain unless specific human-approved reopening; preserve distinction during legacy audit.

### Q13 and Q26 coherent when applied as written

Provisional Pass means requirements met with permitted external-validity limitations. Inconclusive means required evidence unmet. Explicit human exception cannot be relabeled statistical Pass. Shared missing availability may affect models differently; disclosure alone does not make every gap admissible.

No need to re-ask Q26 unless user requests a release exception. Current agreement accepts waiting for sufficient fresh evidence.

## Preflight refinements recommended

1. Specify issue-deadline × future-target forecast contract and native projection scoring.
2. Audit causal inputs and persistent state before interpreting full trajectories.
3. Label initial solver probe as corrected-policy sample or artificial workload proxy. Small capped probe cannot establish full season validity/power or reliable overnight completion.
4. Register paired tolerance probes before calls; record censoring, achieved certificates, decision changes, feature/model-fitting costs, and shared-cache boundaries.
5. Separate feasibility audit, engine implementation/verification, runtime profiling, statistical protocol, and legacy audit into deliverables. Twenty-minute cap applies probe, not whole foundation rebuild.

Workload CSV/runner arithmetic internally consistent. Fixed 38 deadlines/one arm/one iteration assumptions remain illustrative; alternative product selector may add solves. Forecast fitting may dominate and may be shared across starts when causal information identical.

## Minimum additional human decisions

1. What should adoption claim: improvement under fixed Strategic policy, or improvement in full recommendation procedure user follows? Retain controlled benchmark; broader claim needs deployed-policy check.
2. What should neutral squad panel represent: primary deployment target, or robustness benchmark supplemented by actual-context shadow evidence?

Fresh-evidence waiting already settled by Q26. Do not re-ask. Statistical procedures, cache architecture, missing-field detection, forecast contracts, and profiling implementation are agent tasks; present justified proposals instead of asking user to choose libraries or formulas.

## Status and next action

Review recommends targeted clarification, not restarting all 26 questions. Preserve settled objectives and safeguards. Read-only feasibility audit possible before every numerical detail resolved; operational protocol adoption and valid replay evidence blocked by identified gaps.

No policy amendment or preflight execution follows automatically from saving review. Resolve adoption-target/context questions, then revise concrete plan accordingly.

## Follow-up: Strategic usage and GW1 ownership-informed panel

User confirmed primarily using Strategic, while asking whether Unconstrained better for testing. User also prefers representative predefined squads over personal-only requirement and suggested GW1 ownership values. These are steering facts/questions, not approval of following proposals.

### Policy roles proposed for Q27

- Use forecast metrics and bounded Unconstrained replays during development to expose projection effects with fewer Strategic preferences.
- Keep Strategic as primary adoption comparison because it is user's main deployed arm.
- Do not require Unconstrained win as admission condition for a Strategic winner. Report each arm separately; never select whichever arm produces favorable result or average away Strategic harm.
- Predeclare investigation of substantial reversals: forecasts, penalties, transfers, solver quality, state/calendar interactions.

Unconstrained remains a policy: discounting, bench weights, FT/bank terms, weekly hit limit and player pruning persist in [solver objective](../../../solver/solver.py) and [scenario overrides](../../../solver/scenarios.py). Fewer preferences do not make its results standalone forecast-accuracy evidence. Mandatory wins under both arms would be stronger cross-policy requirement, with additional cost and possible rejection of useful Strategic-specific improvement.

### Representative panel proposed for Q28

Ownership-informed legal archetypes bridge arbitrary synthetic teams and unavailable real-manager sample. Use verified opening ownership and prices to create diverse predefined spending structures, such as premium-concentrated and balanced allocations. Select players/tie-breaks independently of either evaluated model. Enforce full fifteen-player composition, club limits, initial budget, and consistent opening bank/acquisition values. Freeze before outcomes.

Retain equal archetype weights from Q24. Interpret result as average over registered benchmark situations, not estimated average over all managers. Personal squad optional for personalization, not mandatory general gate. Exact construction, count, coverage and cost remain audit/profiling tasks.

[Official ownership definition](https://www.premierleague.com/en/news/4680259/whats-new-in-202627-fantasy-more-ways-to-view-your-squad/) is marginal fraction of Fantasy teams owning player, not joint squad composition. Popular expensive players may belong to different manager camps. Independent ownership sampling conditioned on legal budget/positions changes marginals; it does not reconstruct actual population.

Actual manager sample preserves real player combinations when reliably available. Select managers using predeclared sampling frame, not same-season eventual winners. Records observed after deadline can document team that existed at lock; observation time alone does not prove hindsight selection. Stronger population representativeness requires such sampling/coverage evidence, not just larger synthetic panel.

### Data boundary

[Importer](../../../features/vaastav_archive.py) reads players_raw ownership/current price directly and maps GW performance selected/value without capture timestamps. [Local dictionary](../../data_dictionary.md) describes performance price at fixture time. [Upstream dictionary](https://github.com/vaastav/Fantasy-Premier-League/blob/master/DATA_DICTIONARY.md) defines GW selected/value but does not establish exact pre-deadline timestamp. Upstream scrape timing caveat for xP is reason to investigate fields separately, not proof ownership/price invalid.

Verify historical field semantics/capture, opening universe, price, position, club and unavailable players before calling panel causal. GW1 file label insufficient; unknown timing remains unresolved. Do not silently substitute terminal ownership or same-season realized points-per-price. Opening prices constrain affordability; arbitrary ownership/price ratio not established representativeness measure.

### Pending confirmation

1. Unconstrained development diagnostic plus Strategic primary adoption, with registered reversal review.
2. Equal-weight ownership-informed legal archetypes as initial broad benchmark, actual manager sample preferred when feasible, personal check optional.

No new test, solver run, archive analysis, holdout use, or policy amendment in follow-up research.
