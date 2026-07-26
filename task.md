# Active Task: FPL Strategy Evaluation (MILP vs. Template) & Hybrid Draft

- **Status:** Complete — Evaluated Pure Model vs. Standard Template strategy; built and verified Recommended Hybrid Strategy Draft (Haaland + Bruno + Saka + Gabriel + Milan van Ewijk) with 308.6 5-GW xPts and max bank flexibility.
- **Objective:** Evaluate MILP strategy against mainstream template strategy, identify pros & cons of each, and establish the optimal hybrid approach.
- **Acceptance:** Strategy comparison matrix, qualitative trade-off analysis, locked MILP solution with Saka & van Ewijk, and updated artifact `template_vs_milp_strategy_evaluation.md`.

## Work Packet (SFDBN)

- **Status:** Complete & verified.
- **Files:** `data/availability_overrides.csv`, `data/metrics_component_hybrid.csv`, `data/images/squad_timeline_metrics_component_hybrid.png`, `commands/solve.py`
- **Decisions:** Adopt Hybrid Strategy combining Saka (£9.5M), Haaland (£15.5M), Bruno (£12.0M), Gabriel (£8.0M), and Milan van Ewijk (£4.0M promoted enabler).
- **Blocked:** None.
- **Next:** Pre-season friendly monitoring prior to GW1 deadline.

## Todo
- [x] Compare Pure MILP vs. Standard Template strategy dimensions.
- [x] Evaluate trade-offs (GW1 peak ceiling vs. bank flexibility & rotation protection).
- [x] Formulate Hybrid Strategy concept.
- [x] Solve for Hybrid squad locking Saka, Haaland, Bruno, Gabriel, and van Ewijk.
- [x] Publish final strategy evaluation artifact and visual timeline.
