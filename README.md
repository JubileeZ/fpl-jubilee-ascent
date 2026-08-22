# FPL-Jubilee-Ascent

FPL score projection and optimization engine. Ingests FPL API data, evaluates models via backtesting, generates transfer plans via MILP.

## Requirements

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) for dependency and command management
- Playwright Chromium only when browser-based FPL authentication is needed

## Installation

1. Install [uv](https://docs.astral.sh/uv/).
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Install Playwright Chromium binary (required for data refresh/auth):
   ```bash
   uv run playwright install chromium
   ```
4. Setup environment variables. Copy `.env.example` to `.env` and fill:
   - `FPL_EMAIL`: FPL account email (required for authenticated manager squad data)
   - `FPL_PASSWORD`: FPL account password (required for authenticated manager squad data)

The complete locked dependency set is defined in [pyproject.toml](pyproject.toml)
and [uv.lock](uv.lock).

## Repository Layout

- `clients/` — FPL API and authentication clients
- `features/`, `models/`, `projections/` — feature contracts, projection models, solver exports, Ownership Explorer slice metrics
- `backtesting/` — walk-forward evaluation and decision-regret logic
- `commands/` — runnable CLI entry points
- `dashboard/` — Transfer Plan and Ownership Explorer (`uv run python -m commands.dashboard`)
- `config/` — Model Champion selection
- `solver/` — vendored MILP solver
- `tests/` — automated checks
- `data/` — ignored live caches and reports; tracked historical archives in `data/archive/`
- `docs/` — project documentation; start with the [documentation map](docs/README.md)

## CLI Usage Flow

All commands use `uv run python -m ...`.

> **Fallback:** If `uv` is not installed globally, use `PYTHONPATH=. .venv/bin/python -m ...` instead (on Windows the interpreter is `.venv/Scripts/python.exe`).

### 1. Ingest Data

Fetch public FPL data, player statistics, fixtures, and manager-specific team/squad data. Convert raw JSON to processed Parquet tables.

```bash
uv run python -m commands.refresh_data
```

### 2. Run Projections

Generate per-player per-gameweek expected points (xP) and minutes projections using chosen model. Saves projection table to `data/<model_name>.csv`.

```bash
uv run python -m commands.run_model MODEL_NAME --horizon GWS
```
*Example (default 5 gameweeks horizon):*
```bash
uv run python -m commands.run_model participation_state_hybrid --horizon 5
```

`participation_state_hybrid` is the operational default. `metrics_component_hybrid`
remains available as the comparison baseline while snapshot-backed promotion
validation continues.

The component seed/current-season blend can be tuned without editing code:

```bash
uv run python -m commands.run_model component_baseline \
  --horizon 5 --blend_start_appearances 1 --blend_full_appearances 5
```

For verified preseason availability information, optionally create
`data/availability_overrides.csv`:

```csv
player_code,xmins_cap,source,expires_after_gw
223094,60,https://example.com/team-news,1
```

Each cap is validated, applies to all models, and expires after its stated
gameweek. Missing, expired, malformed, duplicate, or unknown-player rows stop
the projection run.

### 3. Generate Transfer Plan (Solve MILP)

Compute optimal squad selection and transfer plans over planning horizon using MILP solver.

**Preseason solver** (new squad selection):

```bash
uv run python -m commands.solve --preseason --xmin_lb 0
```

**Regular season solver** (optimizes active manager squad):

```bash
uv run python -m commands.solve --horizon 6
```

*Note:* Tune the horizon, decay, hit cost, and supported solver options explicitly
(for example `--horizon 6 --decay_base 0.85 --hit_cost 4 --xmin_lb 0`).
Unsupported solver options fail before solving.

### 4. Print Report

Produce console ranking tables by position, captain/vice recommendations for the
next gameweek, and save the full CSV report (including `Captain` and
`Vice_Captain` columns) to `data/reports/top_picks_<model_name>.csv`.

```bash
uv run python -m commands.report --model participation_state_hybrid --horizon 5
```

Record player prices after each refresh and report risers/fallers:

```bash
uv run python -m commands.price_report --top 10
```

Price history is appended to `data/processed/price_history.parquet` with the
player, gameweek, UTC capture time, and FPL `now_cost`.

Print fixture difficulty for each club across the planning horizon. The report
reads `data/processed/fixtures.parquet` (and optionally `clubs.parquet`) without
making an API request, preserves double gameweeks, and sorts by average FDR by
default.

```bash
uv run python -m commands.fdr_report --horizon 5 --sort_by average
```

### 5. Capture Availability Snapshots

Capture immutable, changed-only availability packages during the 48 hours before
a Gameweek deadline:

```bash
uv run python -m commands.capture_availability_snapshot --season 2026-27
```

Packages are written below
`data/availability-snapshots/<season>/GW<gameweek>/`. The scheduled GitHub
workflow stores changed packages on the `availability-snapshots` branch.

### 6. Backtest Models

Run a point-in-time walk-forward evaluation over a specified gameweek range.
Predictions are fixture-level and aggregate to player/gameweek before scoring;
reports include MAE, RMSE, signed bias, rank validity, position strata, and
shortlist overlap/regret. If active processed data has no
`player_performances.parquet`, the command automatically uses the latest
processed season archive.

```bash
uv run python -m commands.backtest metrics_component_hybrid --gw_range 20-30 --seed_season 2025-26
```

Seed-based Cold-Start backtests require a distinct earlier season archive; a
season cannot be both evaluation data and its Prior-Season Seed.

To require verified point-in-time availability packages:

```bash
uv run python -m commands.backtest participation_state_hybrid \
  --gw_range 20-30 --snapshot_root data/availability-snapshots \
  --season 2026-27 --require_snapshots
```

### 7. Evaluate Decision Regret

Compare a public User Squad's actual one-Gameweek lineup, captain, and
vice-captain decision against the best legal hindsight alternative:

```bash
uv run python -m commands.decision_regret --entry_id PUBLIC_ENTRY_ID \
  --gw_range START-END --data_dir PROCESSED_DATA_DIR
```

The command writes `data/reports/decision_regret.csv` by default.

### 8. Open and use the Dashboard

The local dashboard serves the Transfer Plan plus Ownership Explorer.

**Open it**

1. Refresh processed data if `data/processed/` is empty:

   ```bash
   uv run python -m commands.refresh_data
   ```

2. Export Full-Season Window projections and start the server:

   ```bash
   uv run python -m commands.dashboard
   ```
3. The command writes `dashboard/dashboard_data.json` (and a copy under
   `data/`), then tries to open `http://127.0.0.1:8000` in your browser. If
   the window does not appear, visit that URL yourself (prefer `127.0.0.1` over
   `localhost` on Windows). The first load needs
   network access for the Plotly CDN. Stop the server with Ctrl+C.

Optional flags: `--export-only` refreshes the JSON without serving;
`--no-browser` skips auto-open; `--port` changes the port; `--model` /
`--models` override Champion/Candidate export. `--horizon` is the Planning
Horizon (1–5, default 5, from the next gameweek whose deadline has not passed).
Values above 5 are clamped to 5.

The header has two tabs. **Transfer Plan** opens first. **Ownership Explorer**
is the ranking and Mix view. Both share the Planning Horizon clock.

#### Transfer Plan

This tab is the only 15-player surface. It always uses the **Model Champion**
and **Official Fixture Difficulty**. Starting 15 is the User Squad
(`user_picks.parquet`) when present; otherwise Re-solve uses preseason (same as
`commands.solve --preseason`). It does not load research Dual-Vector chip-path
CSVs.

On load it shows the last `data/solution.json` if that file is a Transfer Plan.
Pick a gameweek in the ledger: chip, FT, hits, buy/sell, undiscounted xP, this-week
Solver Objective, plus a **read-only** pitch for that week’s scoring 15. Header
shows decayed **Solver Objective** and undiscounted horizon xP as separate
numbers.

| Control | What it does |
|---------|----------------|
| Planning Horizon | Shorten the exported 1–5 window for this view and Re-solve |
| Enabled Chips | Solver must place each checked Available Chip once in that Chip Set (default: none) |
| Booked Chips | Pin at most one Available Chip to a specific gameweek |
| Force Keep / Force Ban | Attach to the selected ledger gameweek’s scoring 15. Hits allowed; infeasible overrides fail the solve |
| Re-solve | POST the calendar, Enabled Chips, and Keep/Ban. Can take minutes |

Chip Set 1 is GW1–19; Chip Set 2 is GW20–38. A horizon that includes GW19 and
GW20 can Enable **BB (Set 1)** and **BB (Set 2)** as two chips. Do not Enable a
chip that is already Booked in the same Chip Set.

#### Ownership Explorer

Click **Ownership Explorer**. **Primary Model** selects which projection drives
ranking and Mix (not the Transfer Plan). Ranking is the Planning Horizon only —
there is no Season Window or Score Mode in this view.

**Y-axis** is shared by both charts: **Projected Rate** (xP per 90 minutes) or
**xP per Gameweek** (horizon total divided by gameweeks).

Two linked scatter charts sit above the table:

- Left: ownership % (`selected_by_percent`) vs the selected Y-axis
- Right: price (£m) vs the same Y-axis

Marker colour is position (GKP / DEF / MID / FWD). Marker size is average
minutes in the horizon. Click a marker to label that player and highlight the
table row; click empty chart background or the same row again to clear.

**Mix vs Mix** is view-only. Add 1–5 players to Mix A and the same number to
Mix B (same size, not same position). The panel shows combined price, per-GW
xP, and horizon total. Mix does not Force Keep, Force Ban, or Re-solve.

**Filters**

| Control | Effect |
|---------|--------|
| Position | GKP / DEF / MID / FWD checkboxes; applies to charts and table |
| Club | Checkbox multi-select; none checked = all clubs. Label lists checked shorts as `ARS-BOU-BHA-MCI-NEW`. Charts and table. |
| Price | Min–max £m band; applies to charts and table |
| Avg minutes floor | Default 45. Hides low-minute players from **charts only**; the table still lists them |
| Search | Player name, club, or expected role; applies to charts and table |

The rank table is sorted by horizon **Total** descending by default. Click any
column header to sort. Per-GW xP columns follow the Planning Horizon. Rank `#`
is the player's place by Total before table-only sort. The status line under the
toolbar reports how many players are on the chart vs in the table vs in the
full slice.

### 9. Season Archiving

Snapshot and process raw/processed data for historical season analysis.

```bash
uv run python -m commands.snapshot_season
```

## Adding Custom Models

Create custom prediction model inside the [models/](models/) directory.

1. Create Python file, e.g. `models/my_custom_model.py`.
2. Inherit from `BaseModel` in [models/base.py](models/base.py).
3. Implement `name` property and `predict` method.
4. Model auto-discovered dynamically matching defined `name` value.

Example:
```python
from models.base import BaseModel
import pandas as pd

class MyCustomModel(BaseModel):
    @property
    def name(self) -> str:
        return "my_custom_model"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        # Implement custom projection logic matching ProjectionContract.
        # Return fixture rows: player_id, fixture_id, gameweek_id,
        # projected_points, projected_minutes.
        ...
```

## Development and Verification

Run tests and checks before committing changes.

**Lint codebase:**

```bash
uv run ruff check .
```

**Run test suite:**

```bash
uv run pytest
```

**Run the repository delivery checks in Git Bash:**

```bash
bash tests/verify.sh
```


