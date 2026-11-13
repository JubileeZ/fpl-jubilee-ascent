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

## Current Project Status: **ADR 0069 governance reset active (Map #184); implementation & calibration queued before search**

### Map [#184](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/184) Decision & Implementation Schedule (ADR 0069)

Governs **Annual Rolling Validation (`S`=`2026-27` quarantined via `Randdalf/fplcache` `<= 24h`, `S-1`=`2025-26` Dev, `S-2`=`2024-25` Filter)** and **Dual-Tier (`Provisional Active` + `Confirmed Champion`)** readiness, preserving `#175`–`#179` engineering designs from superseded Map [#174](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/174).

| Ticket | State | Scope & Decision |
|---|---|---|
| [**#185**](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/185) `SeasonLifecycle`, `2026-27` rules & `fplcache` ingestion | **FRONTIER (OPEN)** | `config/season_lifecycle.json` (lifts hardcoded `2026-27 GW6+` code/test seals), verified `2026-27` `SeasonRules` & `< gw` fit isolation, `Randdalf/fplcache` (`<= 24h`) + `+24h` outcome adapter + explicit attribution (`zero 2026-27 model ranking peeks`). |
| [**#186**](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/186) Calibrated `FWER <= 5%`, Early-Harm Fallback & `M<=2` podium rules | **FRONTIER (OPEN, HITL)** | Calibrate MBB/inference method (`#177` source review) to nominal `<= 5%` null rejection at `GW15`/`GW30`/`GW38`, set Early-Harm Fallback limits, finalize projection guard tolerances. |
| [**#189**](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/189) Unified `mode="empirical"`, Strategic parity & Stage A->B replay | **BLOCKED (`#185`)** | Missing `2025-26` dev mirrors & `2024-25` seed manifest (`#176`), unified `mode="empirical"` + 8 negative tests (`#178`), `ADR 0065` Strategic parity + profiler telemetry + Stage A->B suites (`#179`). |
| [**#187**](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/187) Dual-Tier serving, `GW15`/`GW30`/`GW38` evaluator & verification | **BLOCKED (`#189`, `#186`)** | Dual-Tier side-by-side predictions + `Provisional Active` Transfer Plan default, calibrated confirmation evaluator, rollover helpers, `verify.sh` + two-axis review. |
| [**#188**](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/188) Freeze initial finalists & authorize `GW1–15` + search | **BLOCKED (`#187`)** | Score eligible non-dead models on `2025-26` + `2024-25`, freeze `<= 2` finalists (`#1` -> `Provisional Active`), run `2026-27 GW1–15+` check, unlock `explore-candidate` / `ideate-candidate`. |

- **Governance Reset & Clean Charting, 2026-11-13 (`ADR 0069`):** Replaced static `2026-27 GW6+` freeze and `2027-28`-deferred `-30m` gate (`ADR 0066` Section 8 / `#180`) with `ADR 0069` Annual Rolling Validation & Dual-Tier governance (`Randdalf/fplcache` `<= 24h` canonical validation base across `GW1–38`, formally credited; neutral `£100.0m` GW1 replay benchmark retained from `ADR 0066` Sections 1–7). Created and Wayfinder-aligned [Wayfinder Map #184](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/184) (`#185`–`#189`); closed superseded [Map #174](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/174) and `#180`–`#183` while preserving completed `#175`–`#179` engineering specifications. Code lifecycle guards remain unchanged pending `#185`.

- **Preserved Prior Map #174 Foundations (`#175`–`#179`, CLOSED 2026-11-12):** [Input freshness #175](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/175) (`8h/24h` mirror, `can_select` vs owned hold/sell, 6-GW completeness); [Coverage/lineage #176](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/176) (`< gw` `model.fit()`, `2024-25` pos-5 exclusion, 342-cell audit); [Inference review #177](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/177) (`research/promotion-inference-177`); [Empirical admission #178](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/178) (`mode="empirical"`, `development_mirror` + `prospective_receipt`, `GW22` card rule, 8 negative tests); [Replay budget #179](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/179) (Strategic ADR 0065 parity, Stage A->B profiling, `target_gap=0.0` `QualityPolicy`, 15 `MANDATORY_GUARDS`). Superseded: `#180`–`#183`.

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
