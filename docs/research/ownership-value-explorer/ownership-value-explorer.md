# Ownership Value Explorer (Full Season)

**Updated**: 2026-08-12T02:00:00+07:00  
**Data stamp**: Stage 2 expected-stats rates; fixtures GW1–38; `selected_by_percent` pricing stamp 2026-07-29  
**Season**: 2026/27 · default horizon GW1–38  
**Status**: Active Research Model  
**Purpose**: Interactive evaluation of projected rate (xP/90) against ownership popularity across the full season, sized by expected minutes, with position / club / price filters.  
**Scope**: XI Contention rates from Stage 2; Ownership = FPL `selected_by_percent` (not EO); optional GW1–6 toggle; optional preseason S1/S5 + user overlays.  
**Related**: [Expected Stats (Stage 2)](../gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [GW1–6 Chip Matrix](../gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md) · [Project](project_season_points.py) · [Plot](plot_ownership_value_explorer.py)  
**Artifacts**:
- [Season projections CSV](../../../data/research/ownership-value-explorer/season_projections.csv)
- [Metrics CSV](../../../data/research/ownership-value-explorer/ownership_value_metrics.csv)
- [Interactive HTML](../../../data/research/ownership-value-explorer/ownership_value_explorer.html)

---

## Sources

- Rates: `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv`
- Fixtures / clubs / players: `data/processed/`
- Availability priors: `docs/research/gw1-6-preseason-pipeline/availability_priors.py`
- Optional overlays: Stage 3 `gw1-6_wc4_simulation.csv`; `user_picks.parquet`

**Source boundary**: Standalone topic (not a GW1–6 pipeline stage). Ownership ≠ EO. Preseason own% soft.

---

## Agent Prompt & Reproducibility Instructions

```text
Run Ownership Value Explorer (full season):

1. Prerequisite: Stage 2 expected-stats CSV present.
2. Command: uv run python docs/research/ownership-value-explorer/plot_ownership_value_explorer.py
   - Rebuilds GW1–38 season projections via ParticipationStateHybridModel.
   - Writes season_projections.csv, ownership_value_metrics.csv, ownership_value_explorer.html.
   - HTML default horizon GW1–38; toggle to GW1–6; filters position/club/price/xMins floor 45.
3. Open HTML in browser (Plotly CDN).
4. Verification: uv run pytest tests/test_ownership_value_explorer.py, uv run ruff check .
```

---

## Method

1. Build feature rows for each XI Contention player × GW1–38 fixtures.
2. Apply Draft Availability overlays (Watch GW1–5 haircut; exclude_gw1-5 zeros GW1–5).
3. Predict via `ParticipationStateHybridModel` (Softmax bonus over contention set).
4. Aggregate season and GW1–6 totals → xP/90 and avg xMins.
5. Join ownership; flag optional S1/S5/user overlays; emit interactive HTML.

---

## Findings

- Default view is **GW1–38** differentials (own% vs season xP/90).
- GW1–6 toggle retained for early-window comparison only.
- Low-xMins players inflate xP/90 — keep floor ≥ 45 unless inspecting cameos.

---

## Decision

**Verdict**: Use full-season board for draft value / differential screening; use GW1–6 toggle when checking early chip structure picks.

**Recommended Action**: Filter by position + price band; compare user diamonds vs low-own high-xP/90 names on season horizon.

---

## Risks and unknowns

- Season minutes assume Stage 2 role priors hold all year (no mid-season role drift model).
- Not EO — captaincy share missing.
- Softmax bonus over full 38-GW contention grid is compute-heavy but fine at ~XI Contention size.

---

## Verification & Delivery

- Artifacts under `data/research/ownership-value-explorer/`.
- Unit tests cover frame overlays + xP/90 fields on season schema.
