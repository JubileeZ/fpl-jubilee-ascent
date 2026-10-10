# FPL-Jubilee-Ascent

FPL score projection and optimization engine. Ingests FPL API data, evaluates models via backtesting, generates transfer plans via MILP. Weekly product: Streamlit analytics dashboard with Explorer (Watchlist & Dream Team), Research, and Model Methodology; transfer plan optimization via CLI.

## Start the dashboard

```powershell
uv sync --locked
uv run python -m commands.dashboard
```

Open `http://127.0.0.1:8000`. Public analytics load immediately. Search and filter players in Explorer, track transfer targets in your interactive Watchlist, and run Dream Team optimization. Transfer planning runs privately via CLI (`uv run python -m commands.solve`).

Navigation starts collapsed; open upper-left chevron to switch workspace. Smaller windows stack controls, Player groups, and charts; inspection opens focused dialog; tables scroll locally.

Read [dashboard usage guide](docs/product/dashboard-usage.md) for complete workflow; [launch/deployment guide](docs/product/streamlit-planner-deployment.md) for Streamlit Community Cloud setup. Alternate `commands.streamlit_planner` launches same app on port 8501.

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) for dependency and command management
- Playwright Chromium only when browser-based FPL authentication is needed

## Installation

1. Install [uv](https://docs.astral.sh/uv/).
2. Install dependencies:

    ```bash
    uv sync --locked
    ```

3. Install Playwright Chromium when browser authentication fallback needed:

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

1. Python 3.14 + `uv sync --locked`; configure auth fallback as needed ([Installation](#installation)).
2. Local `.env`: `FPL_EMAIL` and `FPL_PASSWORD` for authenticated User Squad.
3. Open the dashboard:

```bash
uv run python -m commands.dashboard
```

4. Visit `http://127.0.0.1:8000` (prefer `127.0.0.1` over `localhost`).
5. In **Transfer Planner**, click **Refresh**; wait for live ingest and projections to finish.
6. Set **Horizon end**, click **Generate plan**, wait for solver completion. Choose **Preview policy**, then **Adopt preview policy**; compare Optimal / No Hit / Conservative and rolling before adoption.
7. Click Player to inspect stats/projections. Sell or replace from selected week; bench/captain/vice overrides affect selected week. Click Position-labelled vacancy to add replacement. Complete squad, resolve conflicts, then **Optimize remaining transfers**.
8. Read transfers, bank, Free Transfers, Hits, scores below squad. Draft autosaves; reload restores planner. Explorer What-If remains separate.

Dashboard runs refresh and solver jobs; separate CLI commands optional. Without authenticated squad, Explorer can inspect cached public projections; planner/What-If require squad ingestion. Refresh needs network access. Stop with Ctrl+C. [Full usage guide](docs/product/dashboard-usage.md).

Projection model names (CLI identifiers): [docs/model_name.md](docs/model_name.md).

### CLI projections and advanced Transfer Plan

Model Champion: `config/model_selection.json` `champion`. Fixture xP scale on Feature Contract: **Calibrated Matchup Share** when this-season Official club xG exists ([ADR 0040](docs/adr/0040-calibrated-matchup-share-shrinkage.md)); else Club Strength; else neutral ×1.0 ([ADR 0037](docs/adr/0037-fdr-fallback-multiplier-neutral.md)). Modified FDR is difficulty only. Planner solve and `commands.solve` use Champion. Explorer **Projection model** selects available exported model; `--model` projects another catalog name.

```bash
uv run python -m commands.run_model --horizon 5
uv run python -m commands.solve --horizon 5
uv run python -m commands.report --horizon 5
```

`commands.solve` defaults to a single-arm no-hit MILP (`weekly_hit_limit=0`, gap 0.0) and writes to `data/solution.json`. Add `--scenarios` to solve all 3 scenario arms (Optimal, No Hit, Conservative) into `data/transfer_plan_scenarios.json`; add `--allow-hits` to permit transfer hits. Use CLI for preseason draft and advanced flags:

```bash
uv run python -m commands.solve --preseason --xmin_lb 0
```

Full CLI recipes follow.

## Repository Layout

- `clients/` — FPL API and authentication clients
- `features/`, `models/`, `projections/` — feature contracts, projection models, solver exports, Explorer slice metrics
- `backtesting/` — walk-forward evaluation and decision-regret logic
- `commands/` — runnable CLI entry points
- `dashboard/` — complete Streamlit dashboard (`uv run python -m commands.dashboard`)
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

Generate per-player per-gameweek expected points (xP) and minutes projections using the active Model Champion (from `config/model_selection.json`) by default, or an explicit catalog name from [docs/model_name.md](docs/model_name.md). Saves `data/<model_name>.csv`. Minutes come from the Feature Contract Participation State posterior (Club Fixture shrinkage + Trailing Start Window — [ADR 0035](docs/adr/0035-trailing-start-window.md)), not Expected Role.

```bash
uv run python -m commands.run_model [MODEL_NAME] --horizon GWS
```

*Example (Champion by default, 5 gameweeks horizon):*

```bash
uv run python -m commands.run_model --horizon 5
```

You can also pass `--champion` explicitly or choose any registered model:

```bash
uv run python -m commands.run_model --champion --horizon 5
uv run python -m commands.run_model calibrated_matchup_hybrid --horizon 5
```

Champion and Comparison Slate: `config/model_selection.json`; registered model names and catalog status: [docs/model_name.md](docs/model_name.md).

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

**Weekly path:** dashboard **Transfer Planner** → **Generate plan**; inspect/edit recommendations by Gameweek. **Optimize remaining transfers** preserves explicit choices. Saved dashboard draft/results under `data/planner/`. See [dashboard usage guide](docs/product/dashboard-usage.md).

**CLI** for preseason draft or advanced flags:

**Preseason solver** (new squad selection):

```bash
uv run python -m commands.solve --preseason --xmin_lb 0
```

**Regular season solver** (optimizes active manager squad):

```bash
uv run python -m commands.solve --horizon 10
```

Live Transfer Plans (dashboard **Generate plan** / **Optimize remaining transfers**, and `commands.solve`) default to exact mathematical proof with zero gap (`gap=0.0`, [ADR 0057](docs/adr/0057-zero-gap-digest-caching-3-arm-transfer-plan.md), superseding ADR 0043). Solver scenarios use deterministic input digest caching when inputs unchanged. `commands.solve` executes all 3 arms (Optimal, No Hit, Conservative) concurrently by default; pass `--single` for single-plan execution or `--force` to bypass cache. The 20-minute clock remains safety backstop.

**No Hit solver** (disallows paid transfer hits; free transfers only, matching ADR 0042 No Hit arm):

```bash
uv run python -m commands.solve --horizon 6 --no_hit
```

**Full proof** (`--gap 0`): search until the Solver Objective is proven, instead of stopping within 1% of the best value. Live default is `--gap 0.01`.

```bash
uv run python -m commands.solve --horizon 6 --gap 0
```

**Booked chips:** force one chip onto a gameweek inside the horizon. At most one chip per gameweek. The horizon must include every booked gameweek (default horizon 6 from the next deadline does not reach a later chip week).

| Flag | Chip |
|------|------|
| `--use_wc` | Wildcard |
| `--use_bb` | Bench Boost |
| `--use_fh` | Free Hit |
| `--use_tc` | Triple Captain |

Pass a gameweek, or comma-separated gameweeks. No Hit plus a full proof, with Triple Captain in GW11 and Free Hit in GW12, starting from the next deadline (GW6 needs horizon 7 to include GW12):

```bash
uv run python -m commands.solve --horizon 7 --use_tc 11 --use_fh 12 --no_hit --gap 0
```

The solver reads `data/<champion>.csv` (Champion from `config/model_selection.json`), not a leftover `datasource` in `data/user_settings.json`. Pass `--model NAME` only to score a different catalog CSV (or pass `--champion`).

*Note:* Tune the horizon, decay, hit cost, No Hit mode (`--no_hit` / `--weekly_hit_limit 0`), Solver Objective gap (`--gap 0` for a full proof; live default 0.01), booked chips (`--use_wc`, `--use_bb`, `--use_fh`, `--use_tc`), and other supported solver options explicitly
(for example `--horizon 6 --decay_base 0.85 --hit_cost 4 --xmin_lb 0`).
Unsupported solver options fail before solving.

### 4. Print Report

Produce console ranking tables by position, captain/vice recommendations for the
next gameweek, and save the full CSV report (including `Captain` and
`Vice_Captain` columns) to `data/reports/top_picks_<model_name>.csv`. Defaults to active Champion:

```bash
uv run python -m commands.report --horizon 5
```

Or specify a catalog model explicitly:

```bash
uv run python -m commands.report --model calibrated_matchup_hybrid --horizon 5
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

```bash
uv run python -m commands.dashboard
```

Open `http://127.0.0.1:8000`. Launcher projects from local processed tables when exported JSON missing/stale; **Refresh** explicitly ingests live data. Stop with Ctrl+C. Alternate `commands.streamlit_planner` launches identical app on port 8501. Run one launcher at a time against shared storage.

Open upper-left navigation chevron; choose **Transfer Planner**, **Explorer**, **Research**, or **Model Methodology**. Close navigation for more content width. Layout adapts to available window/sidebar width; Player labels wrap, charts stack, tables keep local horizontal scroll.

- **Transfer Planner:** Read deadline/data-age summary; Generate plan, Preview policy, compare with rolling, then Adopt preview policy. Choose Gameweek; click Player for inspection, Sell/Bench/Replace/captain actions. Fill vacancies with eligible replacements; resolve conflicts before Optimize remaining transfers. Draft autosaves; Reset to solver confirms replacement of manual choices.
- **Explorer:** Projection model and independent horizon; filters apply to charts/table, including minimum minutes. Inspect chart/table selection or use Inspect Player + View player details. Squad What-If uses replacement, starter/bench, captain, and bench-order controls; session-only, separate from planner. Dream Team/advanced strategy results remain independent.
- **Research:** search/select topic, read/download note, preview/download companion CSVs.
- **Model Methodology:** Champion, pipeline layers/formulas, Candidate policy; draft/download research prompt without running experiment.

[Complete usage and recovery guide](docs/product/dashboard-usage.md). [Launch/storage/deployment preparation](docs/product/streamlit-planner-deployment.md). [Responsive behavior and verification limits](docs/product/dashboard-responsive-layout.md).

Local `.env`, User Squad, projections, solver exports, and drafts do not sync through git pull. Refresh regenerates live data/projections; disk projection/export/solve resolves Official tables from Live Season Pin when needed, leaving User Squad untouched (ADR 0036).

Launcher flags: `--no-browser`, `--port`; `--model`/`--models` select models when export occurs. `--export-only` writes JSON without serving; `--horizon` (1–10, default 6) and `--target_gw` select export window. Page horizon controls slice available exported projections; changing them does not rerun projection model.

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

