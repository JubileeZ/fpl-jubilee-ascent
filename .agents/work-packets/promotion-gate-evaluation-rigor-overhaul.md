# Active Task: promotion-gate-evaluation-rigor-overhaul

- **Status:** In Progress
- **Objective:** Chart and execute Wayfinder Map #166 for Historical Promotion Gate & Evaluation Rigor Overhaul (ADR 0064) across 7 child decision tickets
- **Acceptance:** Map #166 and decision tickets #167–#173 charted with native sub-issue and blocking dependencies; Phase 6 roadmap updated; local manifest generated; verify.sh passes cleanly
- **Issue/Ticket:** [Wayfinder Map #166](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/166)

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:**
  - `ROADMAP.md`
  - `docs/agents/current-state.md`
  - `docs/research/INDEX.md`
  - `docs/research/backtest-gate-reform/backtest-gate-reform.md`
  - `docs/research/backtest-gate-reform/wayfinder-tickets.json`
  - `docs/research/backtest-gate-reform/prototype_short_panel_shrinkage.html`
  - `docs/research/backtest-gate-reform/prototype_short_panel_shrinkage.py`
  - `docs/research/backtest-gate-reform/prototype_constrained_legal_xi.html`
  - `docs/research/backtest-gate-reform/prototype_constrained_legal_xi.py`
  - `docs/research/backtest-gate-reform/prototype_exogenous_playable_pool.html`
  - `docs/research/backtest-gate-reform/prototype_exogenous_playable_pool.py`
  - `docs/research/backtest-gate-reform/prototype_non_circular_bootstrap.html`
  - `docs/research/backtest-gate-reform/prototype_non_circular_bootstrap.py`
  - `docs/research/backtest-gate-reform/prototype_sqrt_ns_segment_guardrails.html`
  - `docs/research/backtest-gate-reform/prototype_sqrt_ns_segment_guardrails.py`
  - `models/ml_panel_features.py`
  - `models/ml_component_challenger.py`
  - `backtesting/metrics.py`
  - `backtesting/promotion.py`
  - `backtesting/model_evaluation.py`
  - `backtesting/walkforward.py`
  - `tests/test_ml_panel_leakage.py`
  - `tests/test_backtesting_metrics.py`
  - `tests/test_promotion.py`
  - `tests/test_model_evaluation.py`
  - `tests/test_injury_triage.py`
- **Decisions:**
  - Charted Wayfinder Map #166 on GitHub covering 4 structural audit dilemmas via 7 decision tickets.
  - Linked native sub-issues and blockedBy dependency graph.
  - Added Phase 6: Promotion Gate & Evaluation Rigor Overhaul to ROADMAP.md.
  - Initialized tracking manifest in docs/research/backtest-gate-reform/wayfinder-tickets.json.
  - Resolved Ticket #167: provisioned 2023-24 archive from Vaastav FPL CSVs, updated snapshot_season for multi-season reconstruct, wired default seed_season="2023-24" for confirmation in evaluate_model_promotion and walkforward. Ticket closed.
  - Resolved Ticket #168: implemented Empirical Bayes positional price-tier priors (K_prior=12.0) and continuous Neff sample-size shrinkage (N_min=3500, N_full=7500, seed_weight=0.5) in models/ml_panel_features.py and CausalFeatureScaler. Ticket closed.
  - Resolved Ticket #169: upgraded best_legal_xi to select_legal_formation_xi with scipy.optimize.milp enforcing <= 3 players per club, starting XI budget cap (£83.5m), and deterministic tie-breaking [pred DESC, cost ASC, id ASC]; implemented select_top_15_squad and weekly squad churn Churn_g = 15 - |S_g cap S_{g-1}| with guardrail delta <= +0.50 players/GW. Ticket closed.
  - Resolved Ticket #170: anchored playable pool strictly to model-independent exogenous mask (Mins >= 30 or champ xP >= 2.0) with exposed sample_count; implemented active-window isolation G_active and dual-window guardrail enforcement stopping dormant fallback error dilution; extracted diagnose_guardrail_regressions helper. Ticket closed.
  - Resolved Ticket #171: implemented non-wrapping Moving Block Bootstrap (L=5) restricting start indices to 0 <= s <= n - L, eliminating circular modulo wrapping (% n) and final-block truncation; integrated active-gameweek isolation preventing dormant fallback zero-error dilution; formulated pooled 2-season stratified bootstrap gate with raised thresholds (Dev P >= 0.75, Conf P >= 0.65, Pooled P >= 0.85). Ticket closed.
  - Resolved Ticket #172: calibrated seasonal segment regression floors to uniform stringency z ~ -0.25 SE across asymmetric windows (cold_start -0.25 pts/GW max -1.0 pt, early_mid -0.15 max -2.25 pts, late -0.13 max -2.47 pts) with segment_regression_tolerance helper and optional segment_tolerances parameter in evaluate_historical_promotion_gate. Ticket closed.
- **Blocked:** None
- **Next:** Execute unblocked frontier ticket: #173 (full test suite verification, candidate re-evaluations, and ADR 0064).

## Todo
- [x] Chart Wayfinder Map #166 and child decision tickets #167–#173 on GitHub
- [x] Link sub-issues and wire GraphQL blocking dependencies
- [x] Create local manifest `docs/research/backtest-gate-reform/wayfinder-tickets.json`
- [x] Create research note `docs/research/backtest-gate-reform/backtest-gate-reform.md` and link in `docs/research/INDEX.md`
- [x] Update ROADMAP.md and docs/agents/current-state.md for Phase 6
- [x] Implement Ticket #167: provision 2023-24 warm confirmation seed archive
- [x] Implement Ticket #169: constrained select_legal_formation_xi and squad churn guardrail
- [x] Implement Ticket #170: exogenous playable pool mask and active-window guardrails
- [x] Implement Ticket #168: short-panel empirical Bayes priors and continuous Neff shrinkage
- [x] Implement Ticket #171: non-wrapping moving block bootstrap (L=5) & pooled stratified gate
- [x] Implement Ticket #172: sqrt(ns)-scaled segment loss floors
- [ ] Implement Ticket #173: full test suite verification, candidate re-evaluations, and ADR 0064

## Blockers / Notes
- None. Active unblocked frontier: #173.
