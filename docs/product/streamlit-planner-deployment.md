# Streamlit Dashboard Launch and Deployment Guide

Status: decoupled public analytics dashboard + local CLI transfer solver. Single manager, one web application process. Explorer (with Watchlist & Dream Team), Research, Model Methodology share public web app. Transfer optimization exclusively CLI. ADR 0060.

Daily workflow: [dashboard usage guide](dashboard-usage.md). Window/sidebar behavior: [responsive layout](dashboard-responsive-layout.md).

## Architecture Decoupling

- **Web Dashboard (`streamlit_app.py`):** Public analytics surface. Zero credentials required. Zero manager squad/ITB/chip leakage. Available on Streamlit Community Cloud without `.env`.
- **CLI Transfer Solver (`commands.solve`):** Private optimization engine. Runs locally where `.env` credentials live. Default: single-arm no-hit MILP (`weekly_hit_limit=0`, gap 0.0). Writes `data/solution.json`.
- **Public Data Export (`commands.export_dashboard`):** Defaults to impersonal dataset (`with_squad=False`). Personal squad embedded only when explicitly requested via `--with-squad`.

## Local Launch

```powershell
uv sync --locked
uv run python -m commands.dashboard
```

Open `http://127.0.0.1:8000`. Alternate launcher `uv run python -m commands.streamlit_planner` opens identical app on port 8501. `streamlit run streamlit_app.py` opens same dashboard. Public player projections load from `dashboard/dashboard_data.json`.

Navigation: upper-left chevron opens sidebar workspace selector.
- **Explorer:** Player table, scatter charts, filtering, player inspection modal with Watchlist toggle, interactive Watchlist table (up to 15 players, FDR/fixture breakdown, CSV export), Dream Team MILP solve.
- **Research:** Live research topic reader and note downloader.
- **Model Methodology:** Mathematical documentation, component weights, scoring formulas.

Stop with Ctrl+C. Custom port: `uv run python -m commands.dashboard --port 8001`; suppress browser opening: `--no-browser`.

## CLI Transfer Solver

Run transfer planning locally:

```bash
# Default: single arm, no-hit (weekly_hit_limit=0), gap 0.0
uv run python -m commands.solve

# Allow hits (e.g., up to 1 hit per week)
uv run python -m commands.solve --allow-hits --hit-limit 1

# Run all 3 arms (Optimal, No Hit, Conservative) into transfer_plan_scenarios.json
uv run python -m commands.solve --scenarios
```

## Streamlit Community Cloud Deployment

Entrypoint: `streamlit_app.py`. Python runtime: `>=3.12` (configured in `pyproject.toml`).

### Steps for Free Cloud Hosting:
1. Connect GitHub repository to Streamlit Community Cloud.
2. Select main branch, `streamlit_app.py` as main file path.
3. Deploy. No private credentials needed.
4. Optional secrets in Streamlit Cloud Dashboard (Settings → Secrets):
   - `ADMIN_KEY`: Password to gate public data refresh in web sidebar.
   - `GITHUB_TOKEN`: Fine-grained personal access token with Contents: Read & write permission.
   - `GITHUB_REPOSITORY`: `owner/repo-name`.
   When `ADMIN_KEY`, `GITHUB_TOKEN`, and `GITHUB_REPOSITORY` are configured, authorized admin can trigger "Refresh Public Data" in sidebar, which refreshes official FPL data and commits updated `dashboard/dashboard_data.json` directly back to GitHub repository.

## Configuration & Storage

- `FPL_PLANNER_STORAGE`: Drafts, preferences, job records; default `data/planner`.
- `FPL_PLANNER_DATASET`: Projection JSON; default `dashboard/dashboard_data.json`.
- `ADMIN_KEY`: Optional admin authorization key for triggering public data refresh.
- `GITHUB_TOKEN` / `GITHUB_REPOSITORY`: Optional GitHub API token/repository for persisting refreshed dataset back to git repo.
