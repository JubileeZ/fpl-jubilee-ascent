import argparse
import asyncio
import http.server
import json
import logging
from pathlib import Path
import socketserver
import sys
import threading
import time
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from commands.export_dashboard import (
    PROJECT_ROOT,
    SEASON_END_GW,
    SEASON_START_GW,
    build_dashboard_dataset,
    export_dashboard_data,
    resolve_horizon_start,
)
from commands import refresh_data
from features.builder import build_features
from features.expected_role_prior import (
    DEFAULT_EXPECTED_ROLE_TABLE,
    LIVE_SEASON,
    table_season_status,
)
from models import get_default_model_name, get_model
from projections.exporter import write_solver_projection_csvs
from solver.planning import clamp_planning_horizon
from solver.utils import DEFAULT_PLANNING_HORIZON
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_refresh_lock = threading.Lock()
_refresh_state: dict[str, object] = {"status": "idle", "error": None, "detail": None}


def refresh_status() -> dict[str, object]:
    with _refresh_lock:
        return dict(_refresh_state)


def _set_refresh_state(*, status: str, error: str | None = None, detail: str | None = None) -> None:
    with _refresh_lock:
        _refresh_state["status"] = status
        _refresh_state["error"] = error
        _refresh_state["detail"] = detail


def reset_refresh_state() -> None:
    _set_refresh_state(status="idle", error=None, detail=None)


def ingest_live_data(season: str = LIVE_SEASON) -> None:
    """FPL ingest without Expected Role Rebuild. Defer Role when the table is missing."""
    argv = ["--season", season]
    if table_season_status(DEFAULT_EXPECTED_ROLE_TABLE, season) != "ok":
        argv.append("--keep-roles")
    asyncio.run(refresh_data.main(argv))


def comparison_slate_models(model_name: str | None, model_names: list[str] | None) -> list[str]:
    if model_names:
        return list(model_names)
    if model_name:
        return [model_name]
    try:
        from models.selection import load_model_selection
        sel = load_model_selection()
        return list(dict.fromkeys([sel.champion, *sel.candidates]))
    except Exception:
        return [get_default_model_name()]


def run_dashboard_export(
    model_name: str | None = None,
    horizon: int = DEFAULT_PLANNING_HORIZON,
    target_gw: int | None = None,
    model_names: list[str] | None = None,
) -> Path:
    processed_dir = PROJECT_ROOT / "data" / "processed"
    if not processed_dir.exists():
        raise FileNotFoundError("No processed data found. Run Dashboard Refresh or commands.refresh_data first.")

    names = comparison_slate_models(model_name, model_names)
    default_model = model_name or names[0]
    horizon = clamp_planning_horizon(horizon)
    if target_gw is None:
        target_gw = resolve_horizon_start(processed_dir)

    logger.info(
        f"Generating Full-Season Window projections GW{SEASON_START_GW}–{SEASON_END_GW}; "
        f"Planning Horizon {horizon} from GW{target_gw}"
    )
    df_feat = build_features(processed_dir, SEASON_START_GW, horizon=SEASON_END_GW)

    model_preds: dict[str, pd.DataFrame] = {}
    perf_path = processed_dir / "player_performances.parquet"
    df_perf = pd.read_parquet(perf_path) if perf_path.exists() else None

    for m_name in names:
        logger.info(f"Loading model '{m_name}'...")
        model = get_model(m_name)
        if hasattr(model, "fit") and df_perf is not None:
            model.fit(df_perf[df_perf["gameweek_id"] < target_gw])
        model_preds[m_name] = model.predict(df_feat, SEASON_END_GW)

    dataset = build_dashboard_dataset(
        processed_dir,
        model_preds,
        target_gw,
        horizon,
        default_model_name=default_model,
    )
    df_players = pd.read_parquet(processed_dir / "players.parquet")
    df_clubs = pd.read_parquet(processed_dir / "clubs.parquet")
    write_solver_projection_csvs(model_preds, df_players, df_clubs, PROJECT_ROOT / "data")

    dashboard_dir = PROJECT_ROOT / "dashboard"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    json_path = dashboard_dir / "dashboard_data.json"
    export_dashboard_data(dataset, json_path)
    data_json_path = PROJECT_ROOT / "data" / "dashboard_data.json"
    data_json_path.parent.mkdir(parents=True, exist_ok=True)
    export_dashboard_data(dataset, data_json_path)
    return json_path


def run_refresh_job(
    model_name: str | None = None,
    horizon: int = DEFAULT_PLANNING_HORIZON,
    model_names: list[str] | None = None,
) -> None:
    try:
        _set_refresh_state(status="running", error=None, detail="Ingesting FPL data…")
        ingest_live_data()
        _set_refresh_state(status="running", error=None, detail="Projecting models…")
        run_dashboard_export(model_name=model_name, horizon=horizon, model_names=model_names)
        _set_refresh_state(status="ok", error=None, detail="Charts updated.")
    except Exception as exc:
        logger.exception("Dashboard Refresh failed")
        _set_refresh_state(status="error", error=str(exc), detail="Refresh failed.")


def start_refresh(
    model_name: str | None = None,
    horizon: int = DEFAULT_PLANNING_HORIZON,
    model_names: list[str] | None = None,
) -> dict[str, object]:
    with _refresh_lock:
        if _refresh_state["status"] == "running":
            return dict(_refresh_state)
        _refresh_state["status"] = "running"
        _refresh_state["error"] = None
        _refresh_state["detail"] = "Starting…"
    threading.Thread(
        target=run_refresh_job,
        kwargs={"model_name": model_name, "horizon": horizon, "model_names": model_names},
        daemon=True,
    ).start()
    return refresh_status()


class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serves dashboard/ without caching; Dashboard Refresh on /api/refresh."""

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = str(PROJECT_ROOT / "dashboard")
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _api_path(self) -> str:
        return self.path.split("?", 1)[0].rstrip("/")

    def do_GET(self) -> None:
        if self._api_path() == "/api/refresh":
            self._send_json(200, refresh_status())
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self._api_path() != "/api/refresh":
            self.send_error(404, "Not found")
            return
        state = start_refresh()
        self._send_json(202, state)


def start_server(port: int = 8000, open_browser: bool = True) -> None:
    dashboard_dir = PROJECT_ROOT / "dashboard"
    if not dashboard_dir.exists():
        logger.error(f"Dashboard folder {dashboard_dir} does not exist.")
        sys.exit(1)

    def handler(*args, **kwargs):
        return DashboardHTTPRequestHandler(*args, directory=str(dashboard_dir), **kwargs)

    class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    try:
        with ReusableTCPServer(("", port), handler) as httpd:
            url = f"http://127.0.0.1:{port}"
            logger.info(f"Dashboard web server running at {url}")
            logger.info("Press Ctrl+C to stop the server.")
            if open_browser:
                threading.Thread(target=lambda: (time.sleep(0.5), webbrowser.open(url)), daemon=True).start()
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nServer stopped.")
    except Exception as e:
        logger.error(f"Failed to start server on port {port}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Ownership Explorer. Refresh in the page pulls FPL data and projects.")
    parser.add_argument("--model", type=str, default=None, help="Primary model name")
    parser.add_argument("--models", type=str, nargs="+", default=None, help="List of model names to export")
    parser.add_argument("--horizon", type=int, default=DEFAULT_PLANNING_HORIZON, help="Planning Horizon length")
    parser.add_argument("--target_gw", type=int, help="Horizon Start override for --export-only")
    parser.add_argument("--port", type=int, default=8000, help="Local HTTP server port")
    parser.add_argument("--export-only", action="store_true", help="Project and write JSON without serving")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")
    args = parser.parse_args()

    if args.export_only:
        try:
            run_dashboard_export(
                model_name=args.model,
                horizon=args.horizon,
                target_gw=args.target_gw,
                model_names=args.models,
            )
        except FileNotFoundError as exc:
            logger.error(str(exc))
            sys.exit(1)
        return

    start_server(args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
