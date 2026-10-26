# Active Task: adr-0064-review-fixes

- **Status:** Complete
- **Objective:** Fix Map #166 / ADR 0064 review findings across spec and standards axes
- **Acceptance:** All tests pass, verify.sh clean, ruff clean, all spec defects resolved
- **Issue/Ticket:** #166

## Work Packet (SFDBN)

- **Status:** Complete
- **Files:** commands/evaluate_model_promotion.py, backtesting/walkforward.py, models/ml_panel_features.py, models/ml_component_challenger.py, backtesting/metrics.py, tests/test_backtesting_metrics.py, docs/research/backtest-gate-reform/evaluate_historical_candidates_reformed_gate.py, docs/research/backtest-gate-reform/backtest-gate-reform.md, docs/testing/archive-testing.md, docs/research/INDEX.md, ROADMAP.md, CONTEXT.md, docs/adr/0064-promotion-gate-and-evaluation-rigor-overhaul.md
- **Decisions:** Resolve dev archive fallback to 2025-26; wire obs_counts to CausalFeatureScaler; deduplicate MILP selection in metrics.py; default 2024-25 walkforward to 2023-24 seed
- **Blocked:** None
- **Next:** Propose commit

## Todo
- [x] Step 1: Fix --two_season dev archive resolution & type annotations in commands/evaluate_model_promotion.py
- [x] Step 2: Default 2024-25 walkforward confirmation seed to 2023-24 in backtesting/walkforward.py
- [x] Step 3: Wire obs_counts shrinkage & Neff blending in models/ml_panel_features.py & models/ml_component_challenger.py
- [x] Step 4: Deduplicate MILP lineup selector and fix tie-break logic/tests in backtesting/metrics.py
- [x] Step 5: Deduplicate walk-forward runner in evaluate_historical_candidates_reformed_gate.py
- [x] Step 6: Fix docs, research note schema, Mermaid syntax in ROADMAP.md, comment hygiene
- [x] Step 7: Verify test suite, lint, delivery gate
- [ ] Monitor live validation windows on next ingest

## Blockers / Notes
- None
