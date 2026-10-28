# Documentation Map

Authoritative navigation hub for durable documentation in **FPL-Jubilee-Ascent**.

---

## 1. System Architecture, Data Schema & Rules

Core data structures, official rules, and model registries.

- **[Domain Vocabulary & Concepts](../CONTEXT.md)**: Authoritative glossary covering Realized Points, Process Points, Blended Eval Target, Model Champion, and Solver Scenarios.
- **[Projection Model Catalog](model_name.md)**: Catalog of active Champion, Candidates, and historical baseline projection models.
- **[Data Dictionary](data_dictionary.md)**: Field mappings from raw Official FPL API payloads to clean Parquet schemas (`players`, `clubs`, `fixtures`).
- **[FPL Official Rules Registry](rules/README.md)**: Season-by-season official Premier League scoring rules and matrix definitions ([2025/26 Rules](rules/scoring-rules-2025-26.md)).

---

## 2. Architecture Decision Records (ADRs)

Immutable records of technical decisions, trade-offs, and design agreements.

- **[ADR Master Index](adr/README.md)**: Complete catalog of all 65 ADRs organized by functional subsystem and lifecycle status:
  - **Modeling & Score Projections**: ADRs 0001, 0003, 0005, 0006, 0007, 0010, 0013, 0014, 0015, 0022, 0024, 0025, 0026, 0035, 0037, 0039, 0040, 0041, 0045, 0048, 0050, 0051, 0055, 0056, 0063.
  - **Optimization, Scenarios & Solver**: ADRs 0020, 0029, 0030, 0031, 0033, 0042, 0043, 0053, 0057, 0061, 0065.
  - **Dashboard, UI & Product**: ADRs 0008, 0011, 0017, 0018, 0021, 0027, 0028, 0034, 0052, 0058, 0059, 0060.
  - **Data Ingestion & Pipeline**: ADRs 0002, 0004, 0012, 0019, 0023, 0032, 0036.
  - **Evaluation & Promotion Gates**: ADRs 0038, 0044, 0046, 0047, 0049, 0054, 0062, 0064.

---

## 3. Product & Dashboard Specifications

User guides, operator manuals, and layout architecture for the unified Streamlit application.

- **[Product Specifications Hub](product/README.md)**: Overview of all product documentation mapped by persona.
- **[Manager User Manual](product/dashboard-usage.md)**: End-user guide to launching the dashboard, inspecting players, evaluating fixtures, and managing drafts.
- **[Transfer Planner Guide](product/streamlit-transfer-planner.md)**: Specification for interactive transfer planning, chip triggering, and strategic variance controls.
- **[Production Deployment Guide](product/streamlit-planner-deployment.md)**: Safe operator deployment, memory bounds, and credential isolation.
- **[Single-Product Integration Spec](product/dashboard-planner-integration.md)**: Architecture integrating the Transfer Planner and Explorer in a unified process.
- **[Responsive Layout Standards](product/dashboard-responsive-layout.md)**: Standards for pinned columns and 390px mobile viewport compliance.

---

## 4. Research & Evaluation Rigor

Empirical investigations, statistical promotion gates, and model exploration ledgers.

- **[Research Index & Eval Canon](research/INDEX.md)**: Mandatory rules for promotion metrics (Blended Eval Target, Moving Block Bootstrap $L=5$, segment floors) and active research directory.
- **[Candidate Ledger](research/candidate-ledger/candidate-ledger.md)**: Living registry of tested modeling levers, active moratorium periods, and open exploration ideas.
- **[Candidate Ideation Queue](research/candidate-ideation/)**: Queue of candidate models evaluated against the active Champion.
- **[Promotion Gate & Rigor Overhaul](research/backtest-gate-reform/)**: Protected empirical evidence and benchmark re-evaluations under ADR 0064.
- **[Research Archive](archive/)**: Colocated historical research notes, experiment runners, and companion CSVs.

---

## 5. Testing & Agent Infrastructure

Verification commands, backtest protocol, and autonomous agent workflows.

- **[Testing Architecture Hub](testing/README.md)**: Test layer overview: unit tests, delivery gate `verify.sh`, and HTTP mock policies.
- **[Archive Testing Protocol](testing/archive-testing.md)**: Mandatory protocol for running leak-free historical season evaluations.
- **[Agent Instructions & Key Commands](../AGENTS.md)**: Core developer and agent instructions, invariants, and commands.
- **[Current Implementation State](agents/current-state.md)**: Ground-truth record of currently built and verified capabilities.
- **[Roadmap](../ROADMAP.md)**: Project phases and active Wayfinder milestones.
- **[Agent Workflow Guides](agents/)**: [Progress tracking](agents/progress.md), [Domain boundaries](agents/domain.md), and [Issue tracking](agents/issue-tracker.md).
