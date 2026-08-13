# Ownership Value Explorer (Full Season)

**Updated**: 2026-08-13T03:40:00+07:00  
**Data stamp**: Stage 2 expected-stats rates 2026-08-13; fixtures GW1–38; `selected_by_percent` pricing stamp 2026-07-29  
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

## Open & use

### Open the interactive chart

Artifact path (repo root):

`data/research/ownership-value-explorer/ownership_value_explorer.html`

**From terminal** (repo root):

```bash
xdg-open data/research/ownership-value-explorer/ownership_value_explorer.html   # Linux
open data/research/ownership-value-explorer/ownership_value_explorer.html       # macOS
```

**From the IDE**: open that file in Cursor/VS Code → right-click → **Reveal in File Explorer** / **Open with Live Server**, or use the editor browser preview if available.

**From file manager**: double-click `ownership_value_explorer.html` in `data/research/ownership-value-explorer/`.

Requires network on first load (Plotly CDN). After that, refresh the browser tab when you regenerate the HTML.

### Read the chart

- **X-axis**: FPL ownership % (`selected_by_percent`) — not EO.
- **Y-axis**: xP per 90 for the selected horizon (default **GW1–38** full season).
- **Marker size**: average expected minutes over that horizon.
- **Colour**: position (GKP / DEF / MID / FWD).
- **Text labels**: player names when avg xMins ≥ 60, or when the row matches **Player list** search.
- **Overlay markers**: diamond = user squad · square = preseason S5 · triangle-up = preseason S1.
- **Player table**: full contention list under the chart (not only labelled dots). Search by name/club; **On chart** shows whether the xMins/position/club/price filters currently plot the row. Search also pins a matching marker on the chart even if it is below the xMins floor.

### Filters

| Control | What it does |
|---------|----------------|
| **Horizon** | `GW1–38 season` (default) or `GW1–6 window` for early-chip comparison |
| **Position** | Checkbox each of GKP / DEF / MID / FWD (all checked = all positions) |
| **Club** | Search box narrows visible clubs; **All** / **None** select or deselect visible matches (search first, then None to exclude e.g. one club); checkboxes per club |
| **Price (£m)** | Min / max cost band |
| **Avg xMins floor** | Hide low-minute spikes from the **chart** (default **45**; lower only to inspect cameos). Table still lists everyone. |
| **Overlays** | Toggle S1 / S5 / user highlights; **Only overlay players** restricts the chart to flagged names |
| **Player list** | Search name or club; table is the full list. Off-chart rows stay visible with a reason (e.g. xMins floor). |

**Typical workflow**: pick position + price band → set xMins floor ≥ 45 → scan low-own, high xP/90 markers on the season horizon → switch to GW1–6 if checking early chip picks → enable user overlay to compare your squad diamonds.

### Regenerate when data changes

When Stage 2 rates, fixtures, ownership stamp, or overlays change:

```bash
uv run python docs/research/ownership-value-explorer/plot_ownership_value_explorer.py
```

Writes `season_projections.csv`, `ownership_value_metrics.csv`, and `ownership_value_explorer.html`. Reopen or refresh the HTML file in your browser.

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
3. Open HTML — see [Open & use](#open--use) above (`data/research/ownership-value-explorer/ownership_value_explorer.html`).
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
- Player table lists all 357 contention rows; chart default floor 45 plots 227. Search finds names the scatter does not label.
- Identity: **B.Fernandes (MUN)** nailed; **Bruno G. (ARS)** Rotation (not United); **Virgil (LIV)** nailed — chart + table.
- Low-xMins players inflate xP/90 — keep floor ≥ 45 unless inspecting cameos (Bruno G. avg xMins 33 sits below the floor; search still lists him).

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
