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

## How to use

Weekly path: ingest Official FPL data, then open Ownership Explorer. Transfer Plan is CLI (`commands.solve`), not a dashboard tab. Projection model names (CLI identifiers) are listed in [docs/model_name.md](docs/model_name.md).

### Weekly loop

```bash
uv run python -m commands.refresh_data
uv run python -m commands.dashboard
```

Server: `http://127.0.0.1:8000` (prefer `127.0.0.1` over `localhost`). Click **Refresh** in the page to ingest live data and re-project the selected Primary Model without restarting. You can skip `commands.refresh_data` if you will click Refresh after opening. First load needs network access for the Plotly CDN. Stop with Ctrl+C.

Playwright Chromium plus `.env` (`FPL_EMAIL`, `FPL_PASSWORD`) are required for authenticated User Squad ingest. See [Installation](#installation).

### CLI projections and Transfer Plan

The Model Champion is `config/model_selection.json` `champion` (currently `dual_vector_state_hybrid`). `commands.solve` always uses the Champion. Ownership Explorer Primary defaults to Champion; pass `--model` to project a different catalog name.

```bash
uv run python -m commands.run_model dual_vector_state_hybrid --horizon 5
uv run python -m commands.solve --horizon 6
uv run python -m commands.report --model dual_vector_state_hybrid --horizon 5
```

Preseason draft (no User Squad):

```bash
uv run python -m commands.solve --preseason --xmin_lb 0
```

Full CLI recipes follow.

## Repository Layout

- `clients/` — FPL API and authentication clients
- `features/`, `models/`, `projections/` — feature contracts, projection models, solver exports, Ownership Explorer slice metrics
- `backtesting/` — walk-forward evaluation and decision-regret logic
- `commands/` — runnable CLI entry points
- `dashboard/` — Ownership Explorer (`uv run python -m commands.dashboard`)
- `config/` — Model Champion selection
- `solver/` — vendored MILP solver
- `tests/` — automated checks
- `data/` — ignored live caches and reports; tracked historical archives in `data/archive/`
- `docs/` — project documentation; start with the [documentation map](docs/README.md) and [model names](docs/model_name.md)

## CLI Usage Flow

All commands use `uv run python -m ...`.

> **Fallback:** If `uv` is not installed globally, use `PYTHONPATH=. .venv/bin/python -m ...` instead (on Windows the interpreter is `.venv/Scripts/python.exe`).

### 1. Ingest Data

Fetch public FPL data, player statistics, fixtures, and manager-specific team/squad data. Convert raw JSON to processed Parquet tables.

```bash
uv run python -m commands.refresh_data
```

### 2. Run Projections

Generate per-player per-gameweek expected points (xP) and minutes projections using a catalog name from [docs/model_name.md](docs/model_name.md). Saves `data/<model_name>.csv`.

```bash
uv run python -m commands.run_model MODEL_NAME --horizon GWS
```
*Example (Champion, default 5 gameweeks horizon):*
```bash
uv run python -m commands.run_model dual_vector_state_hybrid --horizon 5
```

Champion is `config/model_selection.json` `champion`. Comparison Slate Candidates
(`participation_state_hybrid`, `metrics_component_hybrid`) stay available while
snapshot-backed promotion validation continues.

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

The solver reads `data/<champion>.csv` (Champion from `config/model_selection.json`), not a leftover `datasource` in `data/user_settings.json`. Pass `--model NAME` only to score a different catalog CSV.

*Note:* Tune the horizon, decay, hit cost, and supported solver options explicitly
(for example `--horizon 6 --decay_base 0.85 --hit_cost 4 --xmin_lb 0`).
Unsupported solver options fail before solving.

### 4. Print Report

Produce console ranking tables by position, captain/vice recommendations for the
next gameweek, and save the full CSV report (including `Captain` and
`Vice_Captain` columns) to `data/reports/top_picks_<model_name>.csv`.

```bash
uv run python -m commands.report --model dual_vector_state_hybrid --horizon 5
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

Read [docs/testing/archive-testing.md](docs/testing/archive-testing.md) first. Pass a catalog name from [docs/model_name.md](docs/model_name.md).

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

The local dashboard is Ownership Explorer. Transfer Plan is CLI (`commands.solve`), not a tab.

**Open it**

```bash
uv run python -m commands.dashboard
```

The command starts `http://127.0.0.1:8000`. If processed tables are newer than `dashboard/dashboard_data.json` (or JSON is missing), it projects the Primary Model (Champion by default) from disk without calling the FPL API. If the window does not appear, visit that URL (prefer `127.0.0.1` over `localhost` on Windows). First load needs network access for the Plotly CDN. Stop the server with Ctrl+C.

Click **Refresh** in the header to ingest live FPL data, re-project the **Primary Model** currently selected, rewrite `dashboard/dashboard_data.json`, and update the charts without restarting the server. You do not need `commands.refresh_data` before opening the dashboard. Refresh pins the current season into `data/archive/<season>/`. Refresh and Solve cannot run at the same time; both buttons disable until the running job finishes.

Click **Solve Dream Team** to run MILP for a Dream Team overlay on the current Planning Horizon and Primary Model. Spend cap is ITB + Selling Prices, or £100.0m when there is no User Squad. Chart markers get a gold ring and the table shows a `Dream` badge. The 15 is session-only and clears if you change Horizon Start/End, Primary Model, or Refresh. It is not a Transfer Plan and does not load onto the Squad Board. The solver runs single-threaded so the same projections should yield the same 15 on different machines.

Projections, solver CSVs, and `dashboard_data.json` are local (gitignored). A git pull does not copy them. After pull, open the dashboard (or Refresh) on each machine from the same processed tables. Leftover `data/processed` on one machine vs the Season Archive pin on another will disagree. Live Refresh at different times can also disagree because FPL data moved.

Optional flags: `--export-only` writes JSON without serving (needs `data/processed`); `--no-browser` skips auto-open; `--port` changes the port; `--model` sets Primary; `--models` still exports a Comparison Slate. `--horizon` is Planning Horizon length (1–6, default 6) for `--export-only` only. Horizon Start / End in the page re-slice the Full-Season export.

**Planning Horizon**

Two dropdowns. **Horizon begins** is any unfinished Gameweek (live week allowed; finished weeks are not). **Horizon to** is the inclusive last Gameweek, at most five weeks after Start (length 1–6), clipped at GW38. Default Start is the earliest unfinished Gameweek; default End is `min(Start+5, 38)`. Changing Start/End updates totals and charts immediately. It does not re-run the model.

**Ownership Explorer**

**Primary Model** selects which projection drives ranking, Squad Board, Component Profile, and Dream Team. Ranking is the Planning Horizon only — there is no Season Window or Score Mode in this view.

**Squad Board** draws the User Squad (pitch + Squad xP strip). Drag a pool player onto a slot for a same-Position Squad What-If transfer; drag on the pitch to sub XI ↔ bench. Header shows ITB, Free Transfer Bank, and Hit warning (not applied). Reset and Reload restore the owned 15. A Rule Breach (club cap, ITB, Starting Shape) is flagged; numbers still move. Auto Captain is the highest xMins-weighted xP in the XI that Gameweek.

**Squad components** under the board are xMins plus Event Component xP per Gameweek, as `xMins | Assume 90`. Select a player in the Explorer table for **Player components**: horizon total and average per Gameweek on the selected Planning Horizon.

**Y-axis** is shared by both charts: **Projected Rate** (xP per 90 minutes) or **xP per Gameweek** (horizon total divided by gameweeks).

Two linked scatter charts sit above the table:

- Left: ownership % (`selected_by_percent`) vs the selected Y-axis
- Right: price (£m) vs the same Y-axis

Marker colour is position (GKP / DEF / MID / FWD). Marker size is average
minutes in the horizon. Click a marker to label that player and highlight the
table row; click empty chart background or the same row again to clear.

**Assume 90** (toolbar, next to Projected Rate / xP per Gameweek) treats every
player as a full 90-minute match on Gameweeks that already have projected
minutes. That is why those two Y-axis metrics then match when there is no
double and no blank Gameweek. Off = Club Fixture xMins. Does not change
Feature Contract minutes.

**Filters**

| Control | Effect |
|---------|--------|
| Position | GKP / DEF / MID / FWD checkboxes; applies to charts and table |
| Club | Checkbox multi-select; none checked = all clubs. Label lists checked shorts as `ARS-BOU-BHA-MCI-NEW`. Charts and table. |
| Price | Min–max £m band; applies to charts and table |
| Avg minutes floor | Default 0. Hides low-minute players from **charts only**; the table still lists them |
| Assume 90 | Toolbar checkbox. All players 90 minutes per existing Gameweek (view-only) |
| Search | Player name or club; applies to charts and table |

The rank table is sorted by horizon **Total** descending by default. Click any
column header to sort. Per-GW xP columns follow the Planning Horizon. Rank `#`
is the player's place by Total before table-only sort. The status line under the
toolbar reports how many players are on the chart vs in the table vs in the
full slice.

### 9. Season Archiving

Snapshot and process raw/processed data for historical season analysis. `--from-vaastav-dir` is a frozen reconstruct of 2024-25 only. `--from-raw-dir` processes local Official FPL raw JSON (no HTTP).

```bash
uv run python -m commands.snapshot_season --season 2024-25 --from-vaastav-dir data/archive/2024-25/vaastav
uv run python -m commands.snapshot_season --season 2024-25 --from-raw-dir <raw>
```

Live `refresh_data` pins the current season into `data/archive/<season>/`.

### 10. Compare and promote models

Read-only Comparison Slate scorecard, then optional Champion write:

```bash
uv run python -m commands.compare_models --gw_range 1-38 --data_dir data/archive/2025-26/processed
uv run python -m commands.evaluate_model_promotion --apply --gw_range 1-38 --data_dir data/archive/2025-26/processed
```

First-Half Transfer Plan Walk-Forward ranking (needs 2024-25 seed; otherwise prints a blocked summary):

```bash
uv run python -m commands.transfer_plan_walkforward
```

## Adding Custom Models

Create a custom prediction model inside [models/](models/). CLI names and the Champion/Candidate split are documented in [docs/model_name.md](docs/model_name.md).

1. Create Python file, e.g. `models/my_custom_model.py`.
2. Inherit from `BaseModel` in [models/base.py](models/base.py).
3. Implement `name` property (the CLI identifier) and `predict` method.
4. Model auto-discovered by matching that `name` value. Add a row to `docs/model_name.md`.

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


