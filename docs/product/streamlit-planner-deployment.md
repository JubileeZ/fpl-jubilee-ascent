# Streamlit Dashboard Launch and Deployment Preparation

Status: complete local Streamlit dashboard; deployment deferred by user. Single manager, one application process. Transfer Planner, Explorer, Research, Model Methodology share same app. ADR 0060.

## Local Launch

```powershell
uv sync --locked
uv run python -m commands.dashboard
```

Open `http://127.0.0.1:8000`. Alternate launcher `uv run python -m commands.streamlit_planner` opens identical app on port 8501. `streamlit run streamlit_app.py` opens same complete dashboard. Existing local projections + User Squad load automatically. Missing data: configure `FPL_EMAIL` / `FPL_PASSWORD` in local `.env`, then Refresh. Solver button runs all three policies; active policy selects displayed recommendation. No real FPL transfer submission.

Existing project environment needs no Windows Administrator access. Without global `uv`/Python, launch `.venv/Scripts/python.exe -m commands.dashboard` from repository. Container build can run later on separate Docker-enabled host; Docker installation on this device unnecessary.

## Configuration

- `FPL_PLANNER_STORAGE`: draft, navigation preference, job records/results; default `data/planner`. Writable persistent directory required.
- `FPL_PLANNER_DATASET`: projection JSON; default `dashboard/dashboard_data.json`.
- `FPL_PLANNER_PROCESSED_DIR`: optional processed data directory for read/solve. Live Refresh targets repository data; clear override to use Refresh.
- Solver projection CSV + settings remain under repository `data/`; Refresh regenerates Champion CSV. Mount whole `data/` for durable operational data.
- Credentials: environment/host secret configuration; `.env` for local use. Root-level Streamlit secrets supported by Streamlit environment integration. Secrets file excluded from git/image.
- Run one app process for single manager; all heavy jobs share exclusive queue. Multiple browser tabs supported: stale draft writes rejected with reload action. Multiple workers/managers require coordinated durable jobs/storage before enabling them. Run one launcher at a time against shared storage.
- Explorer What-If browser-session state; reset on new session. Dream Team + advanced results persisted separately; no implicit planner replacement.

## Container Preparation

`Dockerfile` installs locked Python 3.14 runtime dependencies and Playwright Chromium for auth fallback. `.dockerignore` excludes private operational data, credentials, session token, drafts, and local caches. Official season archives + code included. Image build not verified on current Windows host: Docker/WSL unavailable.

When deployment requested, validate locally on Docker-enabled host:

```sh
docker build -t fpl-dashboard .
docker run --rm -p 127.0.0.1:8501:8501 --env-file .env -v fpl-planner-data:/app/data fpl-dashboard
```

Named volume persists drafts, solver jobs/results, auth cache, and processed data. Browser restart restores draft; process restart marks unfinished job interrupted. Completed results remain available. For remote access, deploy behind authenticated private hosting; configure host access before exposing service. Hosting provider + durable volume choice deferred.

## Streamlit Community Cloud Option

Entrypoint: `streamlit_app.py`; dependency source: `uv.lock` ([supported dependency files](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)). Target Python 3.14; confirm host version support before selecting it. Configure app as private + credentials through host secrets. Streamlit Cloud local filesystem not durable across redeployment; current file-backed app requires storage adaptation before relying on saved plans there. Playwright Chromium installation and actual MILP memory/runtime require host validation. Prepared Docker path uses same app + persistent volume; Linux image build unverified on current host.

Sources: [Cloud deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [private sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app), [Docker](https://docs.streamlit.io/deploy/tutorials/docker).
