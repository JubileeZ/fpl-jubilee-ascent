# FPL-Jubilee-Ascent

FPL score projection and optimization engine. Ingests FPL API data, evaluates models via backtesting, generates transfer plans via MILP.

## Requirements

- Python >= 3.14
- Virtual environment with dependencies: `pandas`, `pyarrow`, `sasoptpy`, `highspy`, `scipy`, `tabulate`, `tenacity`
- Dev tools: `playwright`, `pytest`, `ruff`

## Installation

1. Install [uv](https://docs.astral.sh/uv/) (Python package manager).
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Install Playwright Chromium binary (required for data refresh/auth):
   ```bash
   uv run playwright install chromium
   ```
4. Setup environment variables. Copy `.env.example` to `.env` and fill:
   - `FPL_EMAIL`: FPL account email (optional, for manager squad data)
   - `FPL_PASSWORD`: FPL account password (optional)
   - `FPL_TOKEN`: FPL API token (optional, see [Manual Token Extraction](#manual-fpl-token-extraction) below)

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
uv run python -m commands.run_model <model_name> --horizon <gws>
```
*Example (default 5 gameweeks horizon):*
```bash
uv run python -m commands.run_model linear_baseline --horizon 5
```

### 3. Generate Transfer Plan (Solve MILP)

Compute optimal squad selection and transfer plans over planning horizon using MILP solver.

- Preseason solver (new squad selection):
  ```bash
  uv run python -m commands.solve --preseason --xmin_lb 0
  ```
- Regular season solver (optimizes active manager squad):
  ```bash
  uv run python -m commands.solve --model linear_baseline --horizon 5
  ```
  *Note:* CLI accepts options/settings overrides dynamically (e.g. `--xmin_lb 0` or `--decay_base 0.85`).

### 4. Print Report

Produce console ranking tables by position and save full CSV report to `data/reports/top_picks_<model_name>.csv`.

```bash
uv run python -m commands.report --model linear_baseline --horizon 5
```

### 5. Backtest Models

Simulate historical model performance over specified gameweek range using player performances archive.

```bash
uv run python -m commands.backtest linear_baseline --gw_range 20-30
```

### 6. Season Archiving

Snapshot and process raw/processed data for historical season analysis.

```bash
uv run python -m commands.snapshot_season
```

## Adding Custom Models

Create custom prediction model inside [models/](file:///home/jubileez/FPL-Jubilee-Ascent/models/) directory.

1. Create Python file, e.g. `models/my_custom_model.py`.
2. Inherit from `BaseModel` class in [models/base.py](file:///home/jubileez/FPL-Jubilee-Ascent/models/base.py).
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
        # Implement custom projection logic matching ProjectionContract
        # Returns DataFrame with columns: player_id, gameweek_id, projected_points, projected_minutes
        ...
```

## Development and Verification

Run tests and checks before committing changes.

- Lint codebase:
  ```bash
  uv run ruff check .
  ```
- Run test suite:
  ```bash
  uv run pytest
  ```

## Manual FPL Token Extraction

Playwright browser automation can be blocked by bot detection. To bypass, extract the JWT token manually:

1. Log in to [fantasy.premierleague.com](https://fantasy.premierleague.com) in your browser.
2. Open browser DevTools (F12) → **Network** tab.
3. Navigate to any authenticated page (e.g. Transfers, My Team).
4. Find a request to `fantasy.premierleague.com/api/` (e.g. `/api/me/`).
5. In the request headers, copy the value of `x-api-authorization`.
6. Paste into `.env`:
   ```
   FPL_TOKEN=<copied JWT value>
   ```
7. Run commands normally — token will be used instead of Playwright login.
