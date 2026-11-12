# FPL-Jubilee-Ascent - Project Roadmap

This roadmap tracks the development progress, target architecture, and phases for **FPL-Jubilee-Ascent**.

> **Agents:** read [`docs/agents/current-state.md`](docs/agents/current-state.md) first for what is built today vs this plan.

---

## Personas

| Persona | Goal | Primary surface |
|---------|------|-----------------|
| **User** | Run data refresh, backtest models, run solver to get optimal transfer plans | CLI |
| **Developer** | Plug in new score projection models | Python classes / CLI |

---

## Current Project Status: **Foundation engineering repaired; empirical admission/calibration pending**

- Development coverage and training lineage inventory complete, 2026-11-12: [What development coverage and training lineage can the retained sources actually support?](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/176). Offline audit across 2025-26 (Dev, 38 GWs) and unsealed seeds (`development_coverage_report.md`, `development_coverage_sources.csv`): 342 evaluations (8 `evidenced_bounded`, 37 `carried_from_gw1`, 1 `evidenced_empty`, 113 `partial`, 183 `absent`). GW1 opening anchor (`min_15_cost=640/1000`), GW1–2 universe/prices/availability, and GW2 6-GW schedule evidenced in quarantine; GW1 schedule & GW3–38 contemporaneous snapshots absent locally; terminal May 2026 raw snapshot invalid as point-in-time. `model.fit()` takes strictly `gameweek_id < gw`; `2024-25` seed (`784` players, `20` pos-5 managers) feeds `features/builder.py` only when explicitly passed (`302/685` GW1 direct priors); all `29,747` `2025-26` perf rows ledger-reconciled (`0` mismatches). Next: [Which empirical admission route can satisfy the agreed input rules without weakening authority?](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/178).

- Input evidence and freshness rules resolved, 2026-11-12: [Which input evidence and freshness rules make a historical decision admissible?](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/175). Approved pinned mirror bounded reconstruction, strict 8h/24h bootstrap and 7d/21d schedule bounds, separate can_select purchase eligibility, unknown-chance retention, and fail-closed missing/stale outcomes. Retained 2025-26 GW2 pilot provenance/schema pass; replay blocked on missing history/seed/outcomes/calendar. Closed; unblocked #176.

- Readiness route charted, 2026-11-12: [Candidate Evaluation and Promotion Readiness](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/174). Nine dependency-linked tickets; inference source research complete on separate published branch. Next: human-approved input evidence/freshness policy, then coverage, replay, fresh-confirmation and calibration prerequisites. Model/workflow recommendation saved in current-state. Search readiness and per-finalist promotion remain separate milestones; no Candidate search resumed.

- Offline input contracts and fixed-pilot assessment delivered, 2026-11-12: [Contract](docs/research/backtesting-promotion-foundation/input-evidence-contract.md) · [Delivery/reviews](docs/testing/input-evidence-delivery.md). Future raw receipt format tested offline. Full suite 1062 passed; Ruff/types clean; both reviews zero remaining findings. Empirical gate closed; field-specific approval/calibration/confirmation pending.

- Historical source pilot complete, 2026-11-12: [Report](docs/research/backtesting-promotion-foundation/readiness-source-pilot.md); pinned bytes recovered, partial feasibility. Timing/freshness, eligibility and replay dependency admission unresolved. Prospective protocol proposal prepared; no activation or Candidate search.

- Smoke measurement/readiness preflight delivered, 2026-11-12: oracle common-pool guard, retained stage identities and verified resume; eight synthetic solver probes. Empirical admission remains closed; synthetic significance diagnostics do not establish nominal error control. [Report](docs/research/backtesting-promotion-foundation/smoke_gate_preflight.md) · [Delivery](docs/testing/smoke-gate-preflight-delivery.md). Validation: 1046 tests, Ruff, portable gate; Standards/Spec zero remaining findings; Champion unchanged.

- Correctness repair checkpoint, 2026-10-30: Phase 1–14 Standards/Spec findings resolved; final reviews 0 confirmed findings on both axes. Full suite 1007 passed, Ruff/core types clean; unchanged diagnostic smoke baseline types recorded. Native replay and verified evidence authority validated synthetically. Empirical admission, numerical calibration/approval and prospective validation remain separate prerequisites; no Champion change. Functional local checkpoint `25db911f`; temporary task artifacts removed; no push.

### Backtesting/promotion foundation — delivered (ADR 0066)

- Phase 0 complete `a96af707`: versioned evidence contracts, entry-point inventory, recommendation-only CI guard.
- Phase 1 complete `d4536c42`: strict synthetic causal admission, source/fixture checks and complete-origin inventory.
- Phase 2 complete `d8fa3ad6`: native state transitions, financial/chip accounting and explicit season scoring.
- Phase 3 complete `2676a568`: causal issue-by-target forecasts, strict export, identity/cache/resume storage.
- Phase 4 complete `324a20eb`: neutral GW1 ownership anchor construction, exact two-stage tie-breaking and freezing.
- Phase 5 complete `98537076`: independent rolling replay implementation and verification.
- Phase 6 complete `265fbb0a`: substantive projection guards and staged diagnostics.
- Phase 7 complete `e171dc23`: transfer plan replay profiler within bounded experiment.
- Phase 8 complete `4f56e975`: numerical and statistical evaluation protocol, stored-score block bootstrap, family-wise error control.
- Phase 9 complete `d3f1d72b`: confirmation admission, immutable attempt registry, tamper detection, dead-lever checks.
- Phase 10 complete `4157dd35`: prospective capture, shadow replay state transitions, outcome finalization, rollback recommendations.
- Phase 11 complete `e803e2fc`: unify recommendation paths, read-only pipelines, explicit manual adoption.
- Phase 12 complete `f5e71b7e`: legacy candidate ledger audit using recorded evidence only; lock preservation verified.
- Phase 13 complete `6f60734d`: adopt durable documentation, ADR 0066, operator workflow, and workflow/skill migration.
- Phase 14 complete: full delivery validation (869 tests pass), temporary implementation plan and finished packet deleted.
- Durable canon: [ADR 0066](docs/adr/0066-backtesting-and-promotion-foundation.md), [Operator Workflow](docs/testing/operator-workflow.md), [Delivery Record](docs/testing/foundation-delivery.md), and [Foundation Topic](docs/research/backtesting-promotion-foundation/). Production Model Champion `def_xg_shrink_challenger` stands unchanged; sealed season 2026-27 GW6+ protected.

Wayfinder Map: [Promotion Gate & Evaluation Rigor Overhaul (ADR 0064) #166](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/166) completed. Resolved 4 structural distortions identified in quantitative audit: unseeded confirmation regime mismatch, short-panel Nickell bias, unconstrained LegalXI churn blindness, circular bootstrap boundary bugs, and endogenous playable pool masking across 7 closed decision tickets (#167–#173).

```mermaid
flowchart TD
    P1["Phase 1: Foundations & Auth ✅"] --> P2["Phase 2: Ingestion & Processing ✅"]
    P2 --> P3["Phase 3: Modeling & Backtesting ✅"]
    P3 --> P4["Phase 4: Solver Vendoring & Execution ✅"]
    P4 --> P5["Phase 5: New-Season Readiness ✅"]
    P5 --> P6["Phase 6: Gate & Evaluation Rigor ✅"]
    style P1 fill:#1c7a30,stroke:#155724,stroke-width:2px,color:#fff
    style P2 fill:#1c7a30,stroke:#155724,stroke-width:2px,color:#fff
    style P3 fill:#1c7a30,stroke:#155724,stroke-width:2px,color:#fff
    style P4 fill:#1c7a30,stroke:#155724,stroke-width:2px,color:#fff
    style P5 fill:#1c7a30,stroke:#155724,stroke-width:2px,color:#fff
    style P6 fill:#1c7a30,stroke:#155724,stroke-width:2px,color:#fff
```

---

## Implementation Phases

### ✅ Phase 1: Repo Infrastructure, Foundations & Auth (Completed)
All repository scaffolding, tiered authentication (Playwright, direct HTTP, environment tokens), and developer checks (ruff, pytest) are fully implemented.

---

### ✅ Phase 2: Ingestion, Processing & Archiving (Completed)
Raw data refresh pipeline, historical season snapshot scripts, and raw-to-parquet processors are fully implemented.

---

### ✅ Phase 3: Pluggable Modeling & Backtesting (Completed)
Baseline models, feature and projection exporters, and historical backtesting evaluations are fully implemented.

---

### ✅ Phase 4: Solver Vendoring & Execution (Completed)
Vendored MILP solver, multi-period transfer optimization wrapper, and top-picks console/CSV rank reports are fully implemented.

---

### ✅ Phase 5: New-Season Readiness (Completed)

Prior-season seed component model, Cold-Start, long-format Feature Contract, Modified FDR, CLI reports, Champion/solver tuning. Issues #75–#87 closed. Design: `docs/adr/0003`. Vocabulary: `CONTEXT.md`.

---

### ✅ Phase 6: Promotion Gate & Evaluation Rigor Overhaul (Completed Map #166)

Re-architected Historical Promotion Gate (`backtesting/promotion.py`, `backtesting/metrics.py`, `backtesting/walkforward.py`, `models/ml_panel_features.py`) under ADR 0064:
- Ingest and wire 2023-24 warm confirmation seed archive ([#167](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/167)) ✅.
- Short-panel Empirical Bayes priors & continuous $N_{\text{eff}}$ ML shrinkage ([#168](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/168)) ✅.
- Constrained Legal Formation XI (£83.5m budget cap, 3-per-club max, deterministic tie-breaking) and squad churn guardrail ([#169](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/169)) ✅.
- Exogenous Playable Pool mask & Active-Window Guardrails ([#170](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/170)) ✅.
- Non-wrapping Moving Block Bootstrap ($L=5$, Active GWs) & Pooled Stratified Gate ([#171](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/171)) ✅.
- $\sqrt{n_s}$-scaled segment floors ([#172](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/172)) ✅.
- Verification suite, candidate re-evaluations, and ADR 0064 ([#173](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/173)) ✅.

---

> [!NOTE]
> **Pre-commit gate:** run all test and lint commands successfully before proposing commits.
