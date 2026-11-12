# Inference-method source review

**Updated:** 2026-11-12T19:41:57+01:00
**Data stamp:** Primary papers and local statistical-kernel source inspected 2026-11-12; no new experiments or FPL outcome inspection.
**Season:** Methodological; no season outcomes accessed.
**Status:** Source groundwork complete; method selection, calibration and numerical approval pending.
**Purpose:** Identify defensible inference candidates and assumptions before calibrating Historical Promotion Gate.
**Scope:** Paired stored replay scores, dependent observations, multiplicity and evidence duration. No model/solver runs, confirmation reuse, sealed access or authority changes.
**Related:** [Wayfinder research question](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/177), [Candidate Evaluation and Promotion Readiness](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/174).
**Artifact:** This source-synthesis note only; no numerical companion or figure generated.

## Sources

- **Hall and Wilson (1991), Two Guidelines for Bootstrap Hypothesis Testing**, Biometrics 47, 757–762: [DOI](https://doi.org/10.2307/2532163), [original paper PDF mirror inspected](https://ruc-econometrics.weebly.com/uploads/2/3/3/8/23387606/two_guidelines_for_bootstrap_hypothesis_testing.pdf). Null construction and studentization; original article, not mirror commentary.
- **Künsch (1989), The Jackknife and the Bootstrap for General Stationary Observations**, Annals of Statistics 17, 1217–1241: [DOI](https://doi.org/10.1214/aos/1176347265), [author-uploaded record/abstract inspected](https://www.researchgate.net/publication/2355926_The_Jackknife_and_the_Bootstrap_for_General_Stationary_Observations), [author publication index](https://people.math.ethz.ch/~hkuensch/papers/). Publisher full text not retrievable through browser; claims here limited to author abstract's stationary/block consistency conditions.
- **Romano and Wolf (2005), Stepwise Multiple Testing as Formalized Data Snooping**, Econometrica 73, 1237–1282: [publisher abstract](https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0262.2005.00615.x), [original full paper inspected](https://www.ssc.wisc.edu/~bhansen/718/RomanoWolf2005.pdf), especially sections 2–4, 7 and Appendix B. Dependence, studentization and family-wise inference.
- **Hansen (2005), A Test for Superior Predictive Ability**, JBES 23, 365–380: [DOI](https://doi.org/10.1198/073500105000000063), [original full paper inspected](https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Hansen.pdf). Multiple forecast alternatives, composite null and studentization.
- **Repository:** `backtesting/evidence_statistics.py`, [stored preflight](smoke_gate_preflight.md), [calibration companion](smoke_gate_calibration.csv), [foundation agreements](backtesting-promotion-foundation.md), ADR 0066.

**Source boundary:** Papers establish results under stated statistical assumptions. None certifies this football replay, current kernel, finite evaluation window or future performance. Project interpretation below separated from source claims.

## Method

Read primary methodological statements and relevant algorithm descriptions; cross-check current stored-score kernel. No aggregate recomputation, statistical simulation, empirical rule fitting or outside FPL data retrieval. Existing preflight evidence remains in named companion cells, especially `superiority_rejections`, `simulations` and `wilson95_lower/upper`; no copied result cache here.

## Findings — source claims

**Null distribution and confidence intervals.** Hall/Wilson distinguish observed null deviation from centered bootstrap estimation error. They recommend reproducing the null distribution and suitable pivoting/studentization. A raw bootstrap fraction needs an inferential justification; its label does not establish calibrated significance. [Hall/Wilson](https://doi.org/10.2307/2532163)

**Dependence and block length.** Künsch extends bootstrap/error estimation to stationary sequences using consecutive blocks rather than reducing observations to independent draws. Consistency requires additional conditions and asymptotic block growth with block length small relative to sample length. This does not establish a universal fixed block length or finite-sample accuracy for a short history. [Künsch](https://doi.org/10.1214/aos/1176347265)

**Selection and multiplicity.** Romano/Wolf formulate simultaneous strategy-versus-benchmark tests, estimate joint dependence and propose stepwise procedures with asymptotic family-wise control under their conditions. They advocate studentization when feasible. Appendix B describes moving blocks that preserve calendar-vector dependence. Their result does not make an arbitrary sequential test history equivalent to a prespecified comparison family. [Romano/Wolf](https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0262.2005.00615.x)

**Composite superiority null.** Hansen's SPA test asks whether any of a specified collection of forecast procedures outperforms a benchmark. Studentization and sample-dependent null construction address sensitivity to irrelevant alternatives; the tested family and null construction matter. This is a potential later comparator if a complete family of paired traces exists, not automatic replacement for this project's initially single-finalist confirmation. [Hansen](https://doi.org/10.1198/073500105000000063)

## Project interpretation — candidates to examine

1. **Centered, studentized paired block test.** Compare weighted mean improvement, scaled by a dependence-aware standard error, against a centered resampled statistic. Define nuisance means, weights, degenerate variance and interval/test inversion. A pooled null does not require every seasonal mean to be zero. Implementation candidate only. [Hall/Wilson](https://doi.org/10.2307/2532163)

2. **Block-based confidence-bound inversion.** Evaluate a coherent one-sided lower bound and its corresponding superiority test. Preserve Candidate–Champion pairing, chronology and declared season boundaries. Examine block-length and endpoint-weighting sensitivity rather than choosing the length that gives a desired winner. Within-season stationarity/weak-dependence conditions need justification; rule or policy changes may require a different design. A calendar block is not proof these assumptions hold. [Künsch](https://doi.org/10.1214/aos/1176347265)

3. **Fixed-family joint-resampling sensitivity.** If later comparing several frozen finalists, synchronized resampling can retain cross-model dependence. Romano/Wolf stepdown or Hansen SPA would require their own approved specification and calibration. Current frozen-budget Bonferroni remains the simpler existing policy; it cannot repair invalid component tests. Changing family after observing results requires explicit search accounting. [Romano/Wolf](https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0262.2005.00615.x), [Hansen](https://doi.org/10.1198/073500105000000063)

Uncentered percentile tails need not always fail: some models yield equivalent valid interval-based tests. The implemented statistic, tails and dependence approximation still require justification here.

### Current-kernel observations

`run_stored_score_bootstrap` uses uncentered resampled seasonal means, percentile intervals and a below-zero fraction with tie credit. These quantities require demonstrated interpretation; their names do not establish null-tail validity.

`resample_paired_blocks` silently falls back to independent sampling when sample length does not exceed block size. This changes the dependence approximation. Calibration must cover or explicitly reject that case. No code change proposed by this source note.

The preflight checks only a significance component, omitting admission, registry and projection guards. Its rejection-rate diagnostics cannot be reported as complete-gate empirical FWER. More bootstrap draws reduce resampling noise; they add no independent football observations.

## Required next evidence

Before selecting or approving numerical protocol:

- Define estimand, season/window weights, horizon policy, admitted populations and scope of generalization. Freeze complete paired calendar traces and all relevant selection history.
- Specify the null, statistic, interval/test relation, centering, variance estimator, block scheme, degenerate cases and fixed attempt-family accounting.
- Preregister development/synthetic cases: zero/positive/negative means, unequal seasonal means with pooled null, dependence strengths, heterogeneous variances, heavy-tail/outlier behavior, inactive stretches and allowed policy nonstationarity. Test missing/duplicate/reordered dates and short panels separately.
- Report null rejection and interval coverage with Monte Carlo uncertainty; evaluate the entire intended decision rule as well as components. Simulation success is evidence for tested mechanisms, not universal proof.
- Report power over hypothetical effect sizes and feasible window lengths. Such effects are planning scenarios, not a new minimum-gain eligibility floor. Quantify sensitivity to dependence assumptions; do not promise a calendar duration from row count alone.
- Explain how frozen fresh confirmation and no-peeking/review rules prevent development selection from being disguised as untouched evidence. Reject unsupported inference as Inconclusive.
- Submit practical season/segment/projection harm limits to the human separately. Statistical variability cannot determine acceptable football harm.

## Metric definitions and direction

- **Paired improvement:** `d[s,g] = candidate_net[s,g] - champion_net[s,g]`; weighted mean `mu_hat = sum_s w_s mean_g(d[s,g])`, normalized fixed weights. Higher better; neutral zero. Future expected improvement is an estimand under explicit generalization assumptions.
- **FWER:** probability of at least one false superiority recommendation within declared family. Lower better; agreed target at most 0.05, not established here and not posterior probability of future superiority.
- **Null rejection rate:** rejected independent null replicates divided by total replicates. Lower toward declared size target; ideal conservative/accurate control conditional on tested mechanism.
- **Power:** rejection probability under specified positive-effect mechanism. Higher better at valid size; no project power threshold approved here.
- **Interval coverage:** proportion covering true simulated estimand. Desired nominal coverage conditional on valid design; narrow intervals alone not an ideal.
- **Monte Carlo standard error:** approximately `sqrt(p_hat*(1-p_hat)/R)` for independent simulation replicates; lower better. Not uncertainty from real football histories.

## Decision, risks and unknowns

Source groundwork sufficient to frame calibration candidates and failure cases. No final inference method selected; no block length, replication budget, harm tolerance, alpha interpretation or empirical authority approved. Short dependent histories, nonstationary policy paths and adaptive search may leave useful improvements undetectable. Fresh confirmation and live review remain separate requirements.

## Agent Prompt

Revisit this note through the linked primary papers and exact current kernel. Distinguish source theorem conditions from project assumptions. Preserve preflight companion references instead of copied numerical caches. Propose a bounded calibration plan for human approval; do not run experiments, inspect confirmation/sealed outcomes, change thresholds or issue promotion verdicts from this note.
