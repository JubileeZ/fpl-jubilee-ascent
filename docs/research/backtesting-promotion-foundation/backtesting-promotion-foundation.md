# Backtesting and promotion foundation: decisions, projections, and evidence

**Updated**: 2026-10-29T13:42:04+07:00\
**Data stamp**: Repository `66729b15`; source review/user decisions plus data-only ownership-price feasibility audit, 2026-10-29. No solver timing, outcome analysis, or backtest evidence.\
**Season**: Multi-season methodology; sealed 2026-27 holdout untouched.\
**Status**: Policy direction agreed Q1-Q28; quantitative protocol, data admission, and implementation pending.\
**Purpose**: Preserve why evaluation should measure rolling transfer value while protecting interpretable player projections and controlling compute cost.\
**Scope**: Scoring-model evaluation, optimization policy, statistical evidence, promotion authority, and workload arithmetic.\
**Related**: [Eval canon](../INDEX.md), [archive limitations](../../testing/archive-testing.md), [ADR 0044](../../adr/0044-blended-eval-target-promotion-primary.md), [ADR 0047](../../adr/0047-two-season-promotion-gate.md), [ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md), [ADR 0064](../../adr/0064-promotion-gate-and-evaluation-rigor-overhaul.md), [previous reform](../backtest-gate-reform/backtest-gate-reform.md).\
**Artifact**: [workload_scenarios.csv](workload_scenarios.csv); arithmetic runner [estimate_workload.py](estimate_workload.py).

**Next-stage proposal**: [Preflight and calibration plan](preflight-plan.md), prepared for review; not executed.

**Independent challenge review**: [GPT-6.1 Sol xhigh review](independent-review.md). Targeted clarifications and technical refinements proposed; Q1-Q26 not silently amended. Main human questions: tested recommendation procedure and relationship of neutral starting panel to deployment context.

**Review follow-up:** Q27 agreed: Unconstrained development diagnostic, Strategic primary adoption, with predeclared investigation of substantial arm reversals. Q28 agreed: one highest-owned feasible GW1 anchor per season, locked at first deadline, transfers from GW2, independently evolving continuous paths. Fresh per-origin resets optional diagnostics. Earlier mandatory archetype/personal-squad proposals replaced by simpler reference. Causal source admission and numerical protocol pending.

**Q28 feasibility report:** [Highest-owned anchor audit](ownership-anchor-feasibility.md), [local coverage](ownership_local_coverage.csv), [pinned snapshot sample checks](ownership_snapshot_samples.csv), and [provenance registry](ownership_snapshot_provenance.csv). Opening-anchor continuous benchmark adopted. Contents and recorded pre-deadline Git chronology corroborated for three samples; freshness/eligibility/full replay admission pending. No anchor optimization or model evaluation run.

## Decision boundary

User approved saving reference after initially keeping discussion in chat. No operational gate, Champion selection, workflow, Candidate Ledger, or glossary changed by this note. Existing ADRs and executable behavior remain current until explicit implementation and protocol adoption.

Agreed direction:

- **Q1 — Purpose:** Maximize actual FPL score through suggested rolling transfer plans. Accurate player/component projections also required to understand score drivers and make informed decisions.
- **Q2 — Risk:** Prioritize avoiding harmful promotions. Insufficient evidence distinct from demonstrated failure.
- **Q3 — Outcome:** Actual FPL points after transfer penalties primary. Process Points and blend supporting diagnostics.
- **Q4 — Compute:** Staged exploration; inexpensive diagnostics; optional decision screens; full independent transfer replays for frozen finalists; reusable Champion baseline; statistical resampling from saved outcomes.
- **Q5 — Verdicts:** Pass, demonstrated Fail, Inconclusive, Invalid. Invalid/Inconclusive evidence does not itself justify one-year Dead Lever ban.
- **Q6 — Authority:** Automatic evaluation/recommendation; explicit human approval before Champion adoption.
- **Q7 — Overnight evaluation:** Overnight finalist runs permitted. Exact runtime budget and panel size set after representative profiling; no assumed timing adopted as measurement.
- **Q8 — Starting conditions:** Candidate and Champion receive identical historically legal initial squad, bank, free transfers, and chips, then evolve independently. Initial multi-squad direction narrowed by Q28 to one highest-owned feasible GW1 reference per season.
- **Q9 — Planning horizon:** Six Gameweeks per planning decision; execute immediate decision and replan at each historical deadline. Different horizons remain separate experiments.
- **Q10 — Planning mode:** Strategic arm primary, with identical frozen settings for compared projection models. Other modes are optional robustness checks subject to compute budget.
- **Q11 — Chips:** Shared chip dates for compared models, predefined without future outcomes. Exact schedule and causal construction remain open. Independent chip timing is a separate policy experiment.
- **Q12 — Historical rules:** Use each season's actual scoring and applicable game rules for primary historical replay. Common-current-rule reconstruction remains separate supporting analysis where required data exists; disclose season differences.
- **Q13 — Historical evidence:** Valid comparisons with controlled known leakage and explicitly disclosed historical information gaps may support provisional promotion, subject to human approval and subsequent live validation. Known leakage or broken required inputs remain Invalid. Complete historical snapshots not universal prerequisite for provisional recommendation.
- **Q14 — Projection requirement:** Final promotion requires transfer-policy improvement and no unacceptable regression in predefined player-projection quality checks. Define metrics, population, horizons, tolerances, and uncertainty handling before finalist evaluation; no automatic rejection from small/noisy differences.
- **Q15 — Incremental gain:** No fixed minimum positive points gain for promotion. Convincing evidence of improvement and all safeguards still required; report gain and uncertainty. Insufficient evidence remains Inconclusive.
- **Q16 — Consistency:** Require overall improvement plus predefined material-loss limits for individual seasons and starting-state cases. Do not require every case to win; exact margins and uncertainty handling unresolved.
- **Q17 — Statistical risk:** Target at most 5% family-wise false-positive recommendation risk across declared confirmation comparisons when none of the tested Candidates improves on Champion. Method, dependence assumptions, search accounting, and evidence must justify target. Not posterior probability of superiority, not achieved by existing bootstrap thresholds alone. Unsupported statistical claim remains Inconclusive.
- **Q18 — Confirmation admission:** One frozen finalist per confirmation round initially, selected using development evidence. Freeze code/parameters/data/evaluation identity and record every attempt. Renaming or modifying model does not reset trial history or make inspected data fresh.
- **Q19 — Protected forecasts:** Protect total points, expected minutes, and measurable event components using predefined tolerances. No requirement every component improves. Mark unsupported historical component evidence unassessed; decide applicability/promotion eligibility before finalist results, never silently skip required check.
- **Q20 — Live review:** Provisionally adopted model compared with former Champion using forecasts captured before deadlines and shadow transfer plans. Predefine review points and sufficient-evidence criteria; elapsed time alone does not validate model. Material harm yields rollback recommendation requiring human approval. Single poor week does not automatically switch Champion. Exact review calendar/thresholds pending.
- **Q21 — Numerical calibration:** Prepare documented proposal using development evidence and controlled statistical examples; measure runtime/uncertainty, explain practical trade-offs, then obtain human approval and freeze limits before finalist evaluation. Confirmation/sealed evidence excluded from calibration. Material-harm tolerance remains human preference, not quantity inferred from noise.
- **Q22 — Solver quality:** Accept predefined certified objective-quality tolerance, common to compared models, with maximum runtime; exact optimality not universally required. Choose tolerance after profiling and decision-sensitivity assessment. Missing required quality leaves evaluation incomplete/invalid, not demonstrated model loss. Objective gap does not bound realized-point loss.
- **Q23 — Legacy verdicts:** Audit recorded historical Dead Lever evidence; flag invalid execution, missing evidence, and differing evaluation objectives. Preserve original results/current locks. Specific reopening proposals require explicit human approval before any locked idea rerun. Agreement authorizes audit direction, not blanket reopening.
- **Q24 — Neutral construction:** Freeze initial squads/finances/windows independently of evaluated models and future outcomes. Initial equal-weight multi-archetype panel replaced by Q28 highest-owned feasible reference. Additional anchor sensitivity remains optional; no manager-population representativeness claim.
- **Q25 — Chip-calendar workload:** One shared predefined chip calendar for primary gate initially; additional calendars optional robustness checks. Calendar respects native rules and deadline-known information; actual dates specified before examining Candidate outcomes.
- **Q26 — Fresh confirmation when needed:** Keep Champion and collect predefined fresh evidence for frozen Candidate when reused historical results cannot support agreed statistical standard. Promising historical result alone does not override Inconclusive verdict. Existing archive remains useful for development/robustness; Q13 permits snapshot gaps only when other evidence requirements satisfied. New confirmation protocol/window requires explicit agreement before outcomes examined; sealed data remains protected.
- **Q27 — Policy roles:** Forecast accuracy measured directly; bounded Unconstrained replays useful in development; Strategic remains primary adoption evidence because user primarily uses it. No mandatory Unconstrained win; substantial reversals investigated under predefined rule. Do not choose favorable arm after outcomes or average away Strategic harm.

- **Q28 — Ownership anchor:** One highest-owned full feasible GW1 squad per admitted season, based on verified opening ownership/prices/eligibility. Maximize summed reported ownership under legal fifteen/budget/club/position constraints, with predefined model-independent tie-breaks. Lock fifteen at GW1 deadline; evaluate lineup/captain, start transfers GW2 with native FT state, then preserve each model's independent finances/ownership/chips throughout continuous replay. No mandatory archetypes or personal squad. Refreshed anchors optional local-decision diagnostics, never silently stitched into continuous season score. Narrows Q8/Q24 initial panel direction.

**Measurement-dependent details:** Exact compute budget, starting-state count/composition/windows, Strategic settings and numerical solver tolerance, causal shared chip dates, chronological evidence/search-accounting details, statistical method supporting Q17, material-loss margins, projection metrics/applicability/tolerances, and live review calendar/thresholds. Policy direction agreed Q1-Q26; concrete proposals and numerical freeze follow Q21 preflight/calibration process.

## Why revisit evaluation

Trigger: pulled change restored `def_xg_shrink_challenger` over `adaptive_causal_challenger` in commit `9b6ca8f`, citing re-evaluation under ADR 0064. Discussion questioned fixed £83.5m starting-XI cap versus actual £100m initial squad.

Read-only audit findings:

- [metrics.py](../../../backtesting/metrics.py), `select_legal_formation_xi` and `_formation_xi_stats`: primary task independently selects XI each week under fixed £83.5m cap. Primary points exclude persistent ownership, captain doubling, bench substitution, transfer costs, and chip state.
- Cap implicitly reserves £16.5m for bench. This is arithmetic interpretation, **not documented derivation**. Legal bench cost depends on remaining positions, eligible players, prices, and club quotas. XI under cap need not extend to legal complete squad.
- Separate £100m 15-player selection feeds churn metric, rather than primary XI score.
- Missing metadata and unsuccessful optimizations have fallbacks capable of dropping constraints. Existence verified; use in published historical results not established.
- [transfer_plan_walkforward.py](../../../backtesting/transfer_plan_walkforward.py) carries squad IDs/free transfers and scores lineups. Helper alone does not establish complete bank, acquisition/selling-price, chip, and hit accounting.
- [Promotion workflow](../../../.github/workflows/evaluate_model_promotion.yml) configures single-season `--apply` without `--two_season`; [promotion command](../../../commands/evaluate_model_promotion.py) has separate optional two-season path. Workflow execution history not audited.
- Current confirmation protections and evidence records do not consistently identify frozen source/data/protocol across entry points. Repeatedly examined historical season cannot be assumed untouched confirmation.

**Interpretation:** Earlier results remain evidence under recorded protocols. They do not establish superiority for complete transfer management. No Champion reversal or wholesale rejection of historical research follows automatically.

## Sources

Primary sources accessed 2026-10-29:

- Elmachtoub and Grigas, [Smart Predict, then Optimize](https://arxiv.org/abs/1710.08005), submitted 2017-10-22, revised 2020-11-19: prediction loss versus downstream decision loss.
- Cawley and Talbot, [On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation](https://jmlr.org/papers/v11/cawley10a.html), 2010: selection-induced optimism from finite evaluation samples.
- Gneiting, [Making and Evaluating Point Forecasts](https://arxiv.org/abs/0912.0902), submitted 2009-12-04, revised 2010-03-07: matching scoring function to forecast target.
- Politis and Romano, [The Stationary Bootstrap](https://users.ssc.wisc.edu/~behansen/718/Politis%20Romano.pdf), 1994: dependent-data resampling under assumptions.
- SciPy, [bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html), version 1.18.0 page at review: paired resampling of supplied arrays. Generic API, not justification for IID gameweek resampling.
- HiGHS, [option definitions](https://github.com/ERGO-Code/HiGHS/blob/master/docs/src/options/definitions.md), rolling documentation: solver seeds, time limits, absolute/relative MIP gaps. Installed-version behavior requires profiling.

**Source boundary:** Sources support methodological distinctions, not project thresholds, runtime, starting-state count, or future FPL performance. Workload figures are formula outputs under assumed durations. No empirical timing claim. Project interpretation separated below.

## Method

**Method type:** Source synthesis, repository audit, user interview, deterministic workload arithmetic. Specialist research performed by GPT-6 Astra with High reasoning, followed by source/code review.

Procedure: compare current task with operational objective; separate validity/forecast/decision/statistical evidence; identify reusable versus model-specific computation; preserve agreed direction and open decisions; generate companion CSV then regenerate note cache.

No model fitting, solver calls, archive writes, sealed-holdout inspection, or Candidate lever attempts performed.

### Metrics: formula, direction, benchmark

- **Net realized FPL points:** Official lineup/chip score minus official transfer penalties. Higher ↑. Ideal = best attainable prospective policy under same causal information/constraints, unknown. Positive paired advantage necessary but not alone sufficient for proposed promotion.
- **Paired policy advantage:** Candidate net points minus Champion net points for common season/start/deadline; aggregate with predefined weights. Higher ↑. Neutral benchmark 0; practical worthwhile gain unresolved.
- **Player-points MSE:** Mean `(projected_points - actual_points)^2` on common eligible population, separately by horizon. Lower ↓. Ideal 0, generally unattainable under outcome noise. Squared error matches conditional-mean target; MAE useful descriptively, not sole universal gate.
- **Signed bias:** Mean projected minus observed points. Absolute magnitude lower ↓. Ideal 0; unbiased aggregate alone does not prove calibration.
- **Component reconciliation error:** Absolute total projection minus sum of defined component contributions. Lower ↓. Ideal 0; accounting invariant, not component-accuracy proof.
- **Optimizer calls:** Models × seasons × starting states × deadlines × strategy arms × iterations. Lower ↓ for fixed evidence coverage/quality. Benchmark = smallest workload meeting approved protocol; no universal number.
- **Conditional solver time:** Calls × assumed or measured mean seconds/call. Lower ↓ for fixed coverage/quality. Benchmark = approved budget, unresolved. Excludes feature/fitting/scoring/I/O overhead and parallel scheduling effects.
- **MIP gap:** Feasible-objective versus bound difference, absolute/relative as reported. Lower ↓. Ideal 0 within solver tolerances; does not bound realized FPL loss.
- **Bootstrap interval / positive-draw fraction:** Effect interval under declared resampling assumptions / fraction of resampled effects above 0. No intrinsic ideal or adopted threshold. Fraction is not probability Candidate truly superior or guaranteed search-wide error control.

**Validation boundary:** No measured runtime, new calibrated gate, or new Candidate evidence. Causal-data limitations and replay accounting require implementation review.

## Source synthesis

- Prediction error and optimization value can disagree because constraints and marginal trade-offs determine decisions [Elmachtoub and Grigas]. Supports measuring both, not discarding accuracy.
- Repeated selection among noisy evaluations can overfit evaluation criterion [Cawley and Talbot]. Best finalist report does not erase adaptive search history.
- Scoring function must match intended forecast functional [Gneiting]. Expected points seek conditional mean; absolute-error-only selection can favor another target.
- Paired resampling preserves matched comparisons [SciPy]. Temporal dependence requires additional assumptions/methods [Politis and Romano].
- Common time allowances do not imply equal optimization quality [HiGHS]. Optimization certificate concerns forecast objective, not realized outcomes.

## Project interpretation: idea-to-adoption process and rationale

### 1. Register mechanism and expected benefit

Describe hypothesis, affected players/horizons, proposed variants, and expected decision benefit. Distinguish projection idea from strategy idea. Respect current ledger locks; methodology discussion authorizes no Dead Lever retry.

**Why:** Prevent unrecorded variant search. Identify diagnostics suited to mechanism. A long-term budget-enabler benefit may not appear in immediate lineup comparison.

### 2. Establish usable evidence

Require causal inputs, common player universe, required prices/club metadata, valid forecasts, legal decisions, complete outcomes, and correct scoring. Detect inert implementations. No silent unconstrained fallback, missing-results-as-zero substitution, or alternative primary metric.

**Why:** Defective evidence measures data/code failure, not idea quality. Genuine DNP/blank must be distinguishable from missing outcome record. Stop as Invalid with actionable reason.

### 3. Diagnose player and component projections

Evaluate common eligible population; total-point error, minutes, event probabilities/components, calibration/bias, and horizons. Define strata before inspecting results. Oracle-minutes experiments remain mechanism diagnostics. Keep projection requirements substantive and explicit.

Q14 makes final projection-quality safeguards mandatory alongside transfer-policy evidence. Optional early diagnostic screens remain prioritization tools; their scores alone do not decide promotion or impose a Dead Lever ban.

Q19 protects total points, expected minutes, and measurable event components. Declare per-season applicability/coverage before evaluation: unsupported component remains explicitly unassessed, while missing evidence for a required check prevents passing. Native-season component not awarded by rules may be explicitly inapplicable rather than missing.

**Why:** Product supports informed human judgment as well as solver decisions. Aggregate accuracy can hide wrong minutes or components. Reconciled component sums do not establish accurate explanation.

### 4. Prioritize using optional decision screens

Fixed-15 lineup/captain/bench selection useful for immediate decisions. Sparse shared-state transfer branches useful for interpretation. Preserve full-replay route for mechanisms outside screen scope.

**Why:** Cheap screens conserve compute but can miss long-term winners. Candidate repeatedly reset to Champion state loses continuing consequences of its transfers. Shared-state MILPs at every deadline may cost almost as much as Candidate replay.

Screen may yield lower priority/deferred/Inconclusive. Not automatically demonstrated Fail or Dead Lever.

### 5. Run bounded development transfer replay

Predefine common initial states; use agreed six-Gameweek horizon, Strategic mode, and shared chip dates selected without future outcomes. Freeze Strategic settings, rules, candidate universe, and solver quality. Each model then evolves independently. Replan each deadline, execute immediate decisions, score outcomes, carry complete state. Cache Champion paths; resume completed Candidate deadlines.

Carry owned players, bank, acquisition/selling prices, free transfers, penalties, available/used/expired chips, temporary squad restoration, lineup/bench, captain/vice. Initial £100m belongs to initial squad construction; later deadlines follow evolving finances rather than fresh budget reset.

Use actual historical season scoring/game rules (Q12) in both policy accounting and outcome scoring. Document differences from current product rules; any common-rule reconstruction must be separate and supported by adequate historical inputs.

**Why:** Measures adopting transfer recommendations. Common starts isolate policy effect; independent subsequent states preserve long-term consequences. Fixed solver strategy isolates forecast changes; strategy comparisons require separate track.

Starting state: one model-independent highest-owned feasible GW1 anchor per admitted season (Q28), not mandatory multi-archetype panel. Use verified pre-deadline ownership, opening prices, club/position and eligibility; freeze before examining Candidate outcomes. Total capital minus acquisition spending equals bank. Lock fifteen at first deadline so free preseason redraft cannot erase reference; lineup/captain evaluated GW1, transfers start GW2. Preserve each model's own state afterward. One shared primary chip calendar (Q25); alternatives and later reset origins optional sensitivity, not independent seasons.

### 6. Freeze finalist and experiment identity

Freeze model source/parameters/training, causal datasets, seeds/forecasts, state panel/weights, windows/targets, strategy/horizon, solver version/options, scoring/statistics, and acceptance rules. Persist exact actions, state transitions, per-deadline scores, and termination evidence.

Admit one frozen finalist per confirmation round initially (Q18). Keep versioned attempt registry across renames, patches, and rounds; one-at-a-time admission does not itself solve repeated-testing risk.

**Why:** Model name insufficient identity. Reuse only identical complete problem; same action does not prove same problem. Model/protocol changes invalidate previous recommendation for adoption.

### 7. Complete confirmation and quantify uncertainty

Complete predeclared schedule. Report per-season/start results and weighted paired totals. Process Points/blend and player diagnostics support actual net-points outcome. Resample saved paired score panel; no new solves merely for bootstrap.

Q15 permits any convincingly positive incremental effect without fixed gain floor. Q16 adds predefined material-loss limits by season/start; aggregate win cannot conceal unacceptable harm. Q17 sets 5% family-wise false-positive recommendation target for declared confirmation comparisons. No chosen block-bootstrap fraction or nominal confidence level establishes this target without justified dependence/search/evidence treatment.

**Why:** Saved-effect arithmetic cheap; new trajectories expensive. Preserve contiguous calendar, zero differences, and season boundaries. Use same resampling indices across starts/models sharing matches. Show sensitivity to block length and starting states.

Resampled score blocks need not connect into legal squad trajectory. Interpretation: conditional stability/inference under assumptions, not coherent alternative football season. Training uncertainty or changed histories generally need refitting/replay. Two seasons cannot establish broad between-season uncertainty; more resamples do not create independent evidence.

Repeatedly examined confirmation cannot recover untouched status by renaming. Fresh-evidence protocol and search-aware error control unresolved. Sealed holdout remains protected.

Q26 requires waiting for predefined fresh confirmation when historical reuse prevents supporting agreed standard. Continue development/robustness research while Candidate frozen for confirmation. Insufficient evidence does not authorize provisional switching; any exception requires separately explicit policy decision. No future period allocated or existing sealed outcomes accessed by this note.

Q13 permits provisional recommendation from valid historical comparisons with disclosed information gaps; known leakage must be controlled and required inputs complete. Subsequent live validation required; exact schedule/acceptance rules pending. This permission does not make reused historical validation untouched evidence.

### 8. Classify evidence and recommend

- **Pass:** Valid evidence meets agreed practical improvement, uncertainty, and substantive guardrails.
- **Demonstrated Fail:** Valid evidence establishes predefined unacceptable harm or requirement breach.
- **Inconclusive:** Insufficient valid evidence for either conclusion; includes work deferred by compute budget.
- **Invalid:** Missing required inputs, causal/constraint/scoring defects, solver-quality failure, or protocol violation prevents judgment.

**Why:** Failure to prove improvement is not proof of inferiority. Protect adoption without prematurely banning promising mechanisms. Existing moratorium remains operational until changed implementation/policy adopted; historical ledger rows not silently reopened.

### 9. Human adoption, live validation, rollback

Prepare frozen evidence bundle and explicit recommendation. User approval required before Champion change. Q20 requires saved pre-deadline forecasts/shadow transfer plans for adopted and former Champion, predefined live review points, evidence-based validation, and manual approval of material-harm rollback recommendation. Review calendar, sufficient-evidence thresholds, and operational defect handling still require specification.

**Why:** Small historical sample, adaptive search, and archive limitations require judgment. Intermediate screens or single-season convenience paths cannot establish final adoption readiness.

## Conditional workload and time estimate

Calls = `(F + 1) × S × K × T × A × J`: F Candidates plus Champion, S seasons, K starts, T deadlines, A strategy arms, J internal iterations. Sum actual path lengths if unequal. Randomness repetitions add factor if required.

Planning horizon enlarges each optimization problem; does not automatically multiply outer call count by horizon length. Paths sequential internally; independent paths may parallelize, but speed-up and contention unmeasured. CSV assumes serial calls and no within-path cache savings.

Generate: `uv run python docs/research/backtesting-promotion-foundation/estimate_workload.py`.

**Hypothetical inputs, not measured timings.** Companion columns `optimizer_calls`, `assumed_seconds_per_call`, `solver_seconds`, `solver_minutes`. Generated cache:

<!-- workload-estimates:start -->
- `development_candidate_only`: **38 calls**; 10s/call: 0h 06m 20s; 30s/call: 0h 19m 00s; 60s/call: 0h 38m 00s; 120s/call: 1h 16m 00s.
- `minimal_two_season_candidate_only`: **76 calls**; 10s/call: 0h 12m 40s; 30s/call: 0h 38m 00s; 60s/call: 1h 16m 00s; 120s/call: 2h 32m 00s.
- `single_anchor_champion_and_candidate`: **152 calls**; 10s/call: 0h 25m 20s; 30s/call: 1h 16m 00s; 60s/call: 2h 32m 00s; 120s/call: 5h 04m 00s.
- `three_start_candidate_only`: **228 calls**; 10s/call: 0h 38m 00s; 30s/call: 1h 54m 00s; 60s/call: 3h 48m 00s; 120s/call: 7h 36m 00s.
- `three_start_champion_and_candidate`: **456 calls**; 10s/call: 1h 16m 00s; 30s/call: 3h 48m 00s; 60s/call: 7h 36m 00s; 120s/call: 15h 12m 00s.
- `three_start_champion_and_two_candidates`: **684 calls**; 10s/call: 1h 54m 00s; 30s/call: 5h 42m 00s; 60s/call: 11h 24m 00s; 120s/call: 22h 48m 00s.
<!-- workload-estimates:end -->

Interpretation:

- `development_candidate_only`: one development season/start; Champion cached/excluded. Not complete final gate.
- `minimal_two_season_candidate_only`: one start/two seasons. Smaller workload, narrower roster coverage.
- `single_anchor_champion_and_candidate`: initial two-model/two-season comparison under Q28 reference structure, including uncached Champion baseline.
- `three_start_candidate_only`: incremental finalist/two seasons/three starts with matching Champion cache.
- `three_start_champion_and_candidate`: initial comparison including Champion baseline.
- `three_start_champion_and_two_candidates`: one baseline shared by two finalists.

One opening anchor per season agreed Q28. Three-start rows retained only as optional sensitivity workload examples. Counts assume one planning job per deadline; GW1 locked-squad lineup job may be cheaper than later transfer MILPs. Workload does not make previously inspected confirmation fresh. Champion cache invalid after changes in model, states, data, forecasts, rules, or protocol.

Total elapsed time adds feature generation, fitting, forecasts, MILP assembly, scoring, reports, I/O, and bootstrap. Early screens avoid transfer MILPs but model fitting can dominate. No measured duration available for those stages. Idea authoring/debugging excluded.

**Planning assumption for discussion only:** 30-60 seconds/call illustrates hours per finalist; no claim current machine achieves range. Slower difficult, chip-enabled, or longer-horizon jobs can exceed examples. Overnight execution permitted (Q7); exact budget remains pending profiling.

### Profiling before runtime promises

1. Select small development-only sample before outcomes inspected: ordinary, constrained-budget, transfer-heavy, chip-enabled jobs.
2. Measure feature, fit/projection, MILP, scoring/report time; median/tail time, memory, feasible rate, achieved gap/bound.
3. Freeze solver-quality target and treatment of incomplete jobs. Equal time limit can produce unequal solution quality. Time-limited feasible policy valid only when declared deployed policy; missing required certificate blocks promotion.
4. Estimate Q28 single-anchor continuous workload from actual budget; measure cache/resume behavior. Optional extra anchors require separately stated sensitivity purpose.
5. Use any development racing for prioritization only. Complete frozen final schedule; ordinary fixed-sample intervals do not justify favorable-result early stopping.

Q21 requires documented development-only calibration proposal and human approval before freezing numerical limits. Q22 permits certified approximate optimization under common tolerance/runtime requirements. Profile tighter tolerances for decision sensitivity; no automatic demand for zero gap, and no deadline dropped because solve unfinished.

## Alternatives and why not chosen as sole gate

- **£100m XI cap:** Still omits bench and ownership. Prefer complete legal fifteen and evolving state.
- **Weekly fresh squad:** Useful diagnostic, omits transfer persistence and finances.
- **Full replay every prototype:** Relevant but expensive; restricts breadth or encourages shortcuts. Prefer limited frozen finalists.
- **Mandatory forecast/lineup win:** Cheap proxy can miss decision-useful ideas. Prefer diagnostics plus explicit projection requirements.
- **Change forecasts and strategy together:** Possible product win, but contribution unclear. Separate forecast and policy tracks.
- **Solver rerun per bootstrap draw:** Unnecessary for saved-effect resampling. Different histories/training require different experiment.
- **Independent-squad statistical samples:** Shared match outcomes create dependence; apparent sample size misleading.
- **Promote every positive average:** Luck/search can dominate. Practical and statistical criteria needed; values unresolved.

## Remaining choices and prerequisites

- Exact compute budget after profiling; concurrency. Overnight permission agreed Q7; one finalist per confirmation round agreed Q18.
- Exact Strategic settings, certified solver tolerance/runtime after profiling (Q22), causal shared chip schedule, and separate policy-comparison track. Six-Gameweek horizon, Strategic primary, and shared chip dates agreed Q9-Q11.
- Opening snapshot admission, deterministic highest-owned feasible construction/ties, initial state and GW1 lock for Q28 reference. Season/window weights and actual dates for one shared chip calendar pending; mandatory multi-archetype panel removed.
- Historical rule implementation and supported auxiliary current-rule reconstruction. Native historical rules agreed Q12.
- Evidence coverage requirements and leakage controls for provisional comparison (Q13), historical confirmation reuse, authorized future validation.
- Material-loss margins, interval method, dependence assumptions, and search accounting needed for agreed 5% family-wise risk target (Q17). No fixed minimum gain (Q15); overall win plus loss limits (Q16).
- Projection population/horizons/component metrics, applicability/coverage, tolerances, and uncertainty handling within mandatory safeguards (Q14/Q19).
- Fail-closed inputs, constraints, solver results, metric coverage, and complete scored windows.
- One mandatory promotion protocol across smoke, CLI, CI; full evidence identity and trial history; live review calendar/evidence thresholds and defect handling within agreed manual adoption/rollback (Q20).
- Legacy evidence audit agreed Q23; preserve original figures/protocol/locks and seek explicit individual reopening approval. No blanket ledger exceptions.

## Decision

**Verdict:** Q1-Q26 policy direction agreed as design intent. Preflight/calibration proposal prepared for shared-understanding review; numerical protocol and implementation not adopted. Note is rationale reference, not implemented gate or superseding ADR.

**Next:** Complete source-time admission and replay-accounting feasibility for agreed Q28 reference; then bounded development-only timings and statistical-method assessment before numerical proposal. [Preflight plan](preflight-plan.md) updated to single-anchor design. Formalize ADR/glossary and implementation plan when complete protocol ready for approval.

**Revision trigger:** Measured timings, validated replay accounting, new causal evidence, or changed human decisions. Replace assumptions only with labeled empirical measurements; keep dataset/machine/settings identity.

## Risks and unknowns

- **Computational Scaling**: Full-season 6-GW rolling transfer plan replays across multiple seasons and candidates require bounded runtime controls and certified solver gap management.
- **Serial Dependence**: Overlapping multi-deadline transfer paths introduce strong temporal autocorrelation; IID bootstrap assumptions fail and require non-wrapping Moving Block Bootstrap (MBB).
- **Confirmation Data Integrity**: Reusing historical seasons risks subtle exploratory leakage; strict immutable registration and prospective capture protocols are mandatory.

## Agent Prompt

```text
Refresh docs/research/backtesting-promotion-foundation/backtesting-promotion-foundation.md.
Read archive-testing.md, research INDEX, relevant ADRs, and current evaluator code.
Preserve Q1-Q28 agreements, including ownership-anchor continuous replay replacing mandatory multi-archetype panel. No optimizer preflight executed; data admission, exact budgets and numerical protocol require measurements/review.
Distinguish implemented gate from proposed design; preserve sealed holdout.
Check primary sources; separate their claims from project interpretation.
Run estimate_workload.py for arithmetic only. workload_scenarios.csv columns
optimizer_calls, assumed_seconds_per_call, solver_seconds, solver_minutes are hypothetical.
Add timings only after authorized profiling; record sample, machine/settings/data identity.
Regenerate note cost cache from companion runner. Keep companions in topic folder.
No Champion, gate, workflow, or Dead Lever changes as part of refreshing reference.
```
