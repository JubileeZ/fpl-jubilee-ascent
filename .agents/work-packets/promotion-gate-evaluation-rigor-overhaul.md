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
  - `models/ml_panel_features.py`
  - `models/ml_component_challenger.py`
  - `tests/test_ml_panel_leakage.py`
- **Decisions:**
  - Charted Wayfinder Map #166 on GitHub covering 4 structural audit dilemmas via 7 decision tickets.
  - Linked native sub-issues and blockedBy dependency graph.
  - Added Phase 6: Promotion Gate & Evaluation Rigor Overhaul to ROADMAP.md.
  - Initialized tracking manifest in docs/research/backtest-gate-reform/wayfinder-tickets.json.
  - Resolved Ticket #167: provisioned 2023-24 archive from Vaastav FPL CSVs, updated snapshot_season for multi-season reconstruct, wired default seed_season="2023-24" for confirmation in evaluate_model_promotion and walkforward. Ticket closed.
  - Resolved Ticket #168: implemented Empirical Bayes positional price-tier priors (K_prior=12.0) and continuous Neff sample-size shrinkage (N_min=3500, N_full=7500, seed_weight=0.5) in models/ml_panel_features.py and CausalFeatureScaler. Ticket closed.
- **Blocked:** None
- **Next:** Execute unblocked frontier tickets: #169 (constrained LegalXI), #170 (exogenous playable pool mask).

## Todo
- [x] Chart Wayfinder Map #166 and child decision tickets #167–#173 on GitHub
- [x] Link sub-issues and wire GraphQL blocking dependencies
- [x] Create local manifest `docs/research/backtest-gate-reform/wayfinder-tickets.json`
- [x] Create research note `docs/research/backtest-gate-reform/backtest-gate-reform.md` and link in `docs/research/INDEX.md`
- [x] Update ROADMAP.md and docs/agents/current-state.md for Phase 6
- [x] Implement Ticket #167: provision 2023-24 warm confirmation seed archive
- [ ] Implement Ticket #169: constrained select_legal_formation_xi and squad churn guardrail
- [ ] Implement Ticket #170: exogenous playable pool mask and active-window guardrails
- [x] Implement Ticket #168: short-panel empirical Bayes priors and continuous Neff shrinkage
- [ ] Implement Ticket #171: non-wrapping moving block bootstrap (L=5) & pooled stratified gate
- [ ] Implement Ticket #172: sqrt(ns)-scaled segment loss floors
- [ ] Implement Ticket #173: full test suite verification, candidate re-evaluations, and ADR 0064

## Blockers / Notes
- None. Active unblocked frontier: #169, #170.
