# Product & Dashboard Specifications

User, operator, and developer documentation for the unified Streamlit application.

## Overview

The primary end-user deliverable of FPL-Jubilee-Ascent is an interactive, local-first Streamlit dashboard unifying four core views:
1. **Performance**: Manager trajectory, mini-league rival comparisons, chip history, and KPI strips.
2. **Explorer**: Nailedness metrics, Dream Team overlays, Player Watchlist, and Reality Check triad (Actuals / Opta Expected / Projections).
3. **Transfer Plan Surface**: Interactive multi-period MILP squad planner with inline transfer overrides and 3-arm scenario comparison (`strategic`, `unconstrained`, `no_hit`).
4. **Model Methodology**: Documentation of the active Champion scoring model and empirical evaluation gates.

App launcher: `uv run python -m commands.dashboard` (or `uv run python -m commands.streamlit_planner`).

---

## Guide Index by Persona

### For Users & FPL Managers

| Document | Purpose |
|----------|---------|
| [`dashboard-usage.md`](dashboard-usage.md) | **Manager User Manual**: Step-by-step guide to launching the dashboard, inspecting players, evaluating fixtures, editing transfer drafts, and understanding scenario recommendations. |
| [`streamlit-transfer-planner.md`](streamlit-transfer-planner.md) | **Transfer Planner Guide**: How the interactive transfer plan surface works, including manual player swaps, chip triggering, and strategic variance controls. |

### For Engineers & System Operators

| Document | Purpose |
|----------|---------|
| [`streamlit-planner-deployment.md`](streamlit-planner-deployment.md) | **Production Deployment Guide**: Configuration for hosting the dashboard publicly without credential leakage, memory isolation, and state management. |
| [`dashboard-planner-integration.md`](dashboard-planner-integration.md) | **Architecture Integration Spec**: How the Transfer Planner and Explorer state caches communicate inside a single unified process. |
| [`dashboard-responsive-layout.md`](dashboard-responsive-layout.md) | **Responsive Layout & Viewport Standards**: Pinned column rules, 390px mobile viewport compliance, and table component layout standards. |

---

## Visual Assets

- [`streamlit-planner-preview.jpg`](streamlit-planner-preview.jpg): Visual preview of the Transfer Plan Surface interface and scenario comparison arm.
