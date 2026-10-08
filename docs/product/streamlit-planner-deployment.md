# Streamlit Planner Launch and Deployment Preparation

Status: local implementation; deployment deferred by user. Single manager, one application process. Existing dashboard remains `uv run python -m commands.dashboard`.

## Local Launch

```powershell
uv sync --locked
uv run python -m commands.streamlit_planner
```

Open `http://127.0.0.1:8501`. Existing local projections + User Squad load automatically. Missing data: configure `FPL_EMAIL` / `FPL_PASSWORD` in local `.env`, then Refresh. Refresh invokes existing ingestion/auth and Champion export. Solver button runs all three policies; active policy selects displayed recommendation. No real FPL transfer submission.

## Configuration

- `FPL_PLANNER_STORAGE`: draft, job records, results; default `data/planner`. Writable persistent directory required.
- `FPL_PLANNER_DATASET`: projection JSON; default `dashboard/dashboard_data.json`.
- `FPL_PLANNER_PROCESSED_DIR`: optional processed data directory for read/solve. Live Refresh targets repository data; clear override to use Refresh.
- Solver projection CSV + settings remain under repository `data/`; Refresh regenerates Champion CSV. Mount whole `data/` for durable operational data.
- Credentials: environment/host secret configuration; `.env` for local use. Root-level Streamlit secrets supported by Streamlit environment integration. Secrets file excluded from git/image.
- Run one app process for single manager; job exclusion and draft persistence assume that deployment topology. Multiple workers/managers require coordinated durable jobs/storage before enabling them.

## Container Preparation

`Dockerfile` installs locked Python 3.14 runtime dependencies and Playwright Chromium for auth fallback. `.dockerignore` excludes private operational data, credentials, session token, drafts, and local caches. Official season archives + code included. Image build not verified on current Windows host: Docker/WSL unavailable.

When deployment requested, validate locally on Docker-enabled host:

```sh
docker build -t fpl-transfer-planner .
docker run --rm -p 127.0.0.1:8501:8501 --env-file .env -v fpl-planner-data:/app/data fpl-transfer-planner
```

Named volume persists drafts, solver jobs/results, auth cache, and processed data. Browser restart restores draft; process restart marks unfinished job interrupted. Completed results remain available. For remote access, deploy behind authenticated private hosting; configure host access before exposing service. Hosting provider + durable volume choice deferred.

## Streamlit Community Cloud Option

Entrypoint: `streamlit_app.py`; Python version: 3.14; dependency source: `uv.lock`. Configure app as private + credentials through host secrets. Streamlit Cloud local filesystem not durable across redeployment; arrange persistent storage before relying on saved plans. Playwright Chromium installation and actual MILP memory/runtime must be validated on that host. Container host with persistent volume offers direct control of those requirements.

Sources: [Cloud deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [private sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app), [Docker](https://docs.streamlit.io/deploy/tutorials/docker).
