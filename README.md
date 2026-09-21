# FPL-Jubilee-Ascent

FPL score projection and optimization engine. Ingests FPL API data, evaluates models via backtesting, generates transfer plans via MILP. Weekly product is the local dashboard: Explorer plus Transfer Plan Surface.

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

### Weekly loop (product path)

1. Python 3.14 + `uv sync` (+ Playwright Chromium for auth ingest — see [Installation](#installation)).
2. `.env`: `FPL_EMAIL` and `FPL_PASSWORD` for User Squad (required for Transfer Plan Scenarios).
3. Open the dashboard:

```bash
uv run python -m commands.dashboard
```

4. Visit `http://127.0.0.1:8000` (prefer `127.0.0.1` over `localhost`).
5. Click **Refresh** (ingest live FPL + project Primary / Champion).
6. Open the **Transfer Plan** tab → **Solve scenarios** (ranks Roll / 1 FT / Optimal by horizon Σ Expected GW Score).

You do not need `commands.refresh_data` or `commands.solve` for that weekly path. Without login, Explorer still works; Squad Board stays empty; Solve scenarios is blocked. First load needs network access for the Plotly CDN. Stop with Ctrl+C.

Projection model names (CLI identifiers): [docs/model_name.md](docs/model_name.md).

### CLI projections and advanced Transfer Plan

The Model Champion is `config/model_selection.json` `champion` (currently `participation_penalty_hybrid`). Fixture xP scale on the Feature Contract: **Matchup Share** when this-season Official club xG exists; else Club Strength; else neutral ×1.0 ([ADR 0037](docs/adr/0037-fdr-fallback-multiplier-neutral.md)). Modified FDR is difficulty only. Dashboard Solve scenarios and `commands.solve` always use the Champion. Explorer Primary defaults to Champion; pass `--model` to project a different catalog name.

```bash
uv run python -m commands.run_model participation_penalty_hybrid --horizon 5
uv run python -m commands.solve --horizon 5
uv run python -m commands.report --model participation_penalty_hybrid --horizon 5
```

`commands.solve` writes `data/solution.json`. Product ranking lives on Transfer Plan Surface (`data/transfer_plan_scenarios.json`). Use CLI for preseason draft and advanced flags:

```bash
uv run python -m commands.solve --preseason --xmin_lb 0
```

Full CLI recipes follow.

## Repository Layout

- `clients/` — FPL API and authentication clients
- `features/`, `models/`, `projections/` — feature contracts, projection models, solver exports, Explorer slice metrics
- `backtesting/` — walk-forward evaluation and decision-regret logic
- `commands/` — runnable CLI entry points
- `dashboard/` — Explorer and Transfer Plan Surface (`uv run python -m commands.dashboard`)
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

Generate per-player per-gameweek expected points (xP) and minutes projections using a catalog name from [docs/model_name.md](docs/model_name.md). Saves `data/<model_name>.csv`. Minutes come from the Feature Contract Participation State posterior (Club Fixture shrinkage + Trailing Start Window — [ADR 0035](docs/adr/0035-trailing-start-window.md)), not Expected Role.

```bash
uv run python -m commands.run_model MODEL_NAME --horizon GWS
```

*Example (Champion, default 5 gameweeks horizon):*

```bash
uv run python -m commands.run_model participation_penalty_hybrid --horizon 5
```

Champion is `config/model_selection.json` `champion`. Comparison Slate keeps
`participation_state_hybrid` as the sole Model Candidate while snapshot-backed
promotion validation continues. `metrics_component_hybrid` remains in the catalog
only.

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

**Weekly path:** use the dashboard Transfer Plan tab → **Solve scenarios** (writes `data/transfer_plan_scenarios.json`; top arm also mirrors to `data/solution.json`). See [How to use](#how-to-use).

**CLI** for preseason draft or advanced flags:

**Preseason solver** (new squad selection):

```bash
uv run python -m commands.solve --preseason --xmin_lb 0
```

**Regular season solver** (optimizes active manager squad):

```bash
uv run python -m commands.solve --horizon 10
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
uv run python -m commands.report --model participation_penalty_hybrid --horizon 5
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

Champion signed bias (ADR 0033) writes a research companion, not `data/reports/`:

```bash
uv run python -m commands.measure_champion_bias
```

The companion is `docs/research/champion-signed-bias-2025-26/champion_bias_summary.csv` column `signed_bias`.



### 7. Evaluate Decision Regret

Compare a public User Squad's actual one-Gameweek lineup, captain, and
vice-captain decision against the best legal hindsight alternative:

```bash
uv run python -m commands.decision_regret --entry_id PUBLIC_ENTRY_ID \
  --gw_range START-END --data_dir PROCESSED_DATA_DIR
```

The command writes `data/reports/decision_regret.csv` by default.

### 8. Open and use the Dashboard

The local dashboard is Explorer plus Transfer Plan Surface (peer tabs). Happy path: **Refresh** → **Transfer Plan** → **Solve scenarios**. `commands.solve` remains the CLI writer for preseason / advanced flags (`data/solution.json`).

**Open it**

```bash
uv run python -m commands.dashboard
```

The command starts `http://127.0.0.1:8000`. If processed tables are newer than `dashboard/dashboard_data.json` (or JSON is missing), it projects the Primary Model (Champion by default) from disk without calling the FPL API. If the window does not appear, visit that URL (prefer `127.0.0.1` over `localhost` on Windows). First load needs network access for the Plotly CDN. Stop the server with Ctrl+C.

Click **Refresh** in the header to ingest live FPL data, re-project the **Primary Model** currently selected, rewrite `dashboard/dashboard_data.json`, and update the charts without restarting the server. You do not need `commands.refresh_data` before opening the dashboard. Refresh pins Official FPL (not User Squad) into `data/archive/<season>/` and prints whether that Official hash changed; it does not git commit. Refresh, Dream Team Solve, and Transfer Plan Solve cannot run at the same time; those buttons disable until the running job finishes.

Click **Solve Dream Team** (Explorer only) to run MILP for a Dream Team overlay on the current Planning Horizon and Primary Model. Spend cap is ITB + Selling Prices, or £100.0m when there is no User Squad. Chart markers get a gold ring and the table shows a `Dream` badge. The 15 is session-only and clears if you change Horizon Start/End, Primary Model, or Refresh. It is not a Transfer Plan and does not load onto the Squad Board. The solver runs single-threaded so the same projections should yield the same 15 on different machines.

Open the **Transfer Plan** tab and click **Solve scenarios** to rank Roll / 1 FT / Optimal by horizon sum of Expected GW Score. Needs a User Squad from Refresh with `FPL_EMAIL` and `FPL_PASSWORD`. Without login, Explorer still works; Squad Board stays empty; Solve scenarios is blocked. Booked Chip and Enabled Chip live on this tab only. Plan XI is read-only and does not load into Squad What-If. Payload: `data/transfer_plan_scenarios.json` (not embedded in `dashboard_data.json`).

Projections, solver CSVs, and `dashboard_data.json` are local (gitignored). A git pull does not copy them. On project/export/solve resolve, Official tables in `data/processed` are healed from the Live Season Pin when they disagree (User Squad untouched; ADR 0036). After pull, open the dashboard or run export/`run_model`/`solve` — heal aligns Official tables automatically. Live Refresh at different times can still disagree because FPL data moved; Refresh advances both processed and pin.

Optional flags: `--export-only` writes JSON without serving (needs `data/processed`); `--no-browser` skips auto-open; `--port` changes the port; `--model` sets Primary; `--models` still exports a Comparison Slate. `--horizon` is Planning Horizon length (1–10, default 6) for `--export-only` only. Horizon Start / End in the page re-slice the Full-Season export.

**Planning Horizon**

Two dropdowns. **Horizon begins** is any unfinished Gameweek (live week allowed; finished weeks are not). **Horizon to** is the inclusive last Gameweek, at most nine weeks after Start (length 1–10), clipped at GW38. Default Start is the earliest unfinished Gameweek; default End is `min(Start+5, 38)`. Changing Start/End updates totals and charts immediately. It does not re-run the model.

**Explorer**

**Primary Model** selects which projection drives ranking, Squad Board, Component Profile, and Dream Team. Ranking is the Planning Horizon only — there is no Season Window or Score Mode in this view. **Champion Trust** in the header shows Champion name and provisional flag when promotion is provisional.

**Squad Board** draws the User Squad (pitch + Squad xP strip + Squad components). Drag a pool player onto a slot for a same-Position Squad What-If transfer; drag on the pitch to sub XI ↔ bench. Header shows ITB, Free Transfer Bank, and Hit warning (not applied). Reset and Reload restore the owned 15. A Rule Breach (club cap, ITB, Starting Shape) is flagged; numbers still move. Auto Captain is the highest xMins-weighted xP in the XI that Gameweek.

Below the board: toolbar filters, **Differentials Ranking** (when EO cache exists), then the **rank table**, then ownership % and price scatter charts, then **Player components** for the selected player.

The rank table and Differentials show **Total** (horizon xP) and **/GW** (xP per Gameweek = Total ÷ gameweeks). The rank table also has **/90** (Projected Rate), per-GW xP with fixture labels, status / chance / news, Δ£, Own%, and xMins. On-screen legend under the toolbar: Total · /GW · /90 · xMins · Δ£ · Dream.

**Y-axis** is shared by both charts: **xP per Gameweek** (default) or **Projected Rate**. Charts sit under the table. Marker colour is position; marker size is average minutes. Click a marker to label that player and highlight the table row.

**Filters**


| Control           | Effect                                                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Position          | GKP / DEF / MID / FWD checkboxes; applies to charts and table                                                           |
| Club              | Checkbox multi-select; none checked = all clubs. Label lists checked shorts as `ARS-BOU-BHA-MCI-NEW`. Charts and table. |
| Price             | Min–max £m band; applies to charts and table                                                                            |
| Avg minutes floor | Default 0. Hides low-minute players from **charts only**; the table still lists them                                    |
| Search            | Player name or club; applies to charts and table                                                                        |


The rank table is sorted by horizon **Total** descending by default. Click any
column header to sort. Per-GW xP columns follow the Planning Horizon and include
fixture labels. Rank `#`
is the player's place by Total before table-only sort. The status line under the
toolbar reports how many players are on the chart vs in the table vs in the
full slice.

**Transfer Plan Surface**

Peer tab beside Explorer. **Plan Start** = upcoming open deadline (`is_next`). Horizon length 1–10 (default 6). **Solve scenarios** ranks Roll / 1 FT / Optimal by undiscounted sum of Expected GW Score (1 FT omitted when Free Transfer Bank = 0). Solver Objective is secondary only. Click a week on the EGS strip to inspect that Gameweek’s buys/sells, Hits, and read-only plan XI (plan captain marked); default = Plan Start. Auto Captain / Auto Vice-Captain / next-best 1–2 XI stay on Plan Start. Booked Chip and Enabled Chip calendar on this tab only. Champion Trust echoed under the plan header. Does not load into Squad What-If.

### 9. Season Archiving

Snapshot and process raw/processed data for historical season analysis. `--from-vaastav-dir` is a frozen reconstruct of 2024-25 only. `--from-raw-dir` processes local Official FPL raw JSON (no HTTP).

```bash
uv run python -m commands.snapshot_season --season 2024-25 --from-vaastav-dir data/archive/2024-25/vaastav
uv run python -m commands.snapshot_season --season 2024-25 --from-raw-dir <raw>
```

Live `refresh_data` pins Official FPL into `data/archive/<season>/` (Live Season Pin). It does not pin User Squad files and does not git commit. Commit the pin yourself when the printed Official hash changed.

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

