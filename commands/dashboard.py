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
from commands.dream_team import execute_dream_team
from commands import refresh_data
from features.builder import build_features, resolve_operational_processed_dir
from features.expected_role_prior import LIVE_SEASON
from models import get_default_model_name, get_model
from models.selection import projection_model_names
from projections.exporter import write_solver_projection_csvs
from solver.planning import clamp_planning_horizon, planning_window
from solver.utils import DEFAULT_PLANNING_HORIZON
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_job_lock = threading.Lock()
_refresh_lock = threading.Lock()
_refresh_state: dict[str, object] = {"status": "idle", "error": None, "detail": None}
_dream_lock = threading.Lock()
_dream_state: dict[str, object] = {
    "status": "idle",
    "error": None,
    "detail": None,
    "player_ids": None,
    "budget": None,
    "leftover": None,
    "model": None,
}


def should_project_on_open(processed_dir: Path, json_path: Path) -> bool:
    """True when processed tables exist and are newer than dashboard JSON (or JSON is missing)."""
    players = processed_dir / "players.parquet"
    if not players.exists():
        return False
    if not json_path.exists():
        return True
    json_mtime = json_path.stat().st_mtime
    for name in ("players.parquet", "player_performances.parquet", "fixtures.parquet"):
        path = processed_dir / name
        if path.exists() and path.stat().st_mtime > json_mtime:
            return True
    return False


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


def dream_team_status() -> dict[str, object]:
    with _dream_lock:
        return dict(_dream_state)


def _set_dream_state(**kwargs: object) -> None:
    with _dream_lock:
        _dream_state.update(kwargs)


def reset_dream_team_state() -> None:
    _set_dream_state(
        status="idle",
        error=None,
        detail=None,
        player_ids=None,
        budget=None,
        leftover=None,
        model=None,
    )


def ingest_live_data(season: str = LIVE_SEASON) -> None:
    """FPL ingest plus Season Archive pin. Does not scrape lineups."""
    asyncio.run(refresh_data.main(["--season", season]))


def posted_primary_model(body: dict[str, object] | None) -> str:
    """Posted Primary Model, or Champion when missing/placeholder `default`."""
    raw = str((body or {}).get("model") or "").strip()
    if not raw or raw.lower() == "default":
        return get_default_model_name()
    return raw


def run_dashboard_export(
    model_name: str | None = None,
    horizon: int = DEFAULT_PLANNING_HORIZON,
    target_gw: int | None = None,
    model_names: list[str] | None = None,
) -> Path:
    processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
    if not (processed_dir / "players.parquet").exists():
        raise FileNotFoundError("No processed data found. Run Dashboard Refresh or commands.refresh_data first.")

    names = projection_model_names(model_name, model_names)
    default_model = model_name or names[0]
    horizon = clamp_planning_horizon(horizon)
    if target_gw is None:
        target_gw = resolve_horizon_start(processed_dir)

    logger.info(
        f"Generating Full-Season Window projections GW{SEASON_START_GW}–{SEASON_END_GW}; "
        f"Planning Horizon {horizon} from GW{target_gw}"
    )
    df_feat = build_features(
        processed_dir,
        SEASON_START_GW,
        horizon=SEASON_END_GW,
        history_before_gw=SEASON_END_GW + 1,
    )

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
        reset_dream_team_state()
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
) -> tuple[int, dict[str, object]]:
    with _job_lock:
        if dream_team_status()["status"] == "running":
            return 409, {
                "status": "error",
                "error": "Dream Team Solve is running. Wait for it to finish.",
                "detail": "Dream Team Solve is running. Wait for it to finish.",
            }
        with _refresh_lock:
            if _refresh_state["status"] == "running":
                return 202, dict(_refresh_state)
            _refresh_state["status"] = "running"
            _refresh_state["error"] = None
            _refresh_state["detail"] = "Starting…"
    threading.Thread(
        target=run_refresh_job,
        kwargs={"model_name": model_name, "horizon": horizon, "model_names": model_names},
        daemon=True,
    ).start()
    return 202, refresh_status()


def run_dream_team_job(*, model_name: str, target_gw: int, horizon: int) -> None:
    try:
        _set_dream_state(status="running", error=None, detail="Solving Dream Team…", player_ids=None)
        processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
        result = execute_dream_team(
            processed_dir,
            model_name=model_name,
            target_gw=target_gw,
            horizon=horizon,
        )
        _set_dream_state(
            status="ok",
            error=None,
            detail="Dream Team ready.",
            player_ids=result["player_ids"],
            budget=result["budget"],
            leftover=result["leftover"],
            model=result["model"],
        )
    except Exception as exc:
        logger.exception("Dream Team Solve failed")
        _set_dream_state(status="error", error=str(exc), detail="Solve failed.", player_ids=None)


def start_dream_team(*, model_name: str, target_gw: int, horizon: int) -> tuple[int, dict[str, object]]:
    with _job_lock:
        if refresh_status()["status"] == "running":
            return 409, {
                "status": "error",
                "error": "Refresh is running. Wait for it to finish.",
                "detail": "Refresh is running. Wait for it to finish.",
            }
        with _dream_lock:
            if _dream_state["status"] == "running":
                return 202, dict(_dream_state)
            _dream_state["status"] = "running"
            _dream_state["error"] = None
            _dream_state["detail"] = "Starting…"
            _dream_state["player_ids"] = None
            _dream_state["budget"] = None
            _dream_state["leftover"] = None
            _dream_state["model"] = None
    threading.Thread(
        target=run_dream_team_job,
        kwargs={"model_name": model_name, "target_gw": target_gw, "horizon": horizon},
        daemon=True,
    ).start()
    return 202, dream_team_status()


def _dream_team_args(body: dict[str, object] | None) -> tuple[str, int, int]:
    payload = body or {}
    model_name = posted_primary_model(payload)
    start = int(payload.get("horizon_start") or 1)
    end = int(payload.get("horizon_end") or start)
    gws = planning_window(start, end)
    if not gws:
        gws = [max(1, start)]
    horizon = clamp_planning_horizon(len(gws))
    return model_name, int(gws[0]), horizon


def handle_dashboard_api(
    method: str,
    path: str,
    body: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    if path == "/api/refresh":
        if method == "GET":
            return 200, refresh_status()
        if method == "POST":
            model_name = posted_primary_model(body)
            return start_refresh(model_name=model_name)
    if path == "/api/dream-team":
        if method == "GET":
            return 200, dream_team_status()
        if method == "POST":
            model_name, target_gw, horizon = _dream_team_args(body)
            return start_dream_team(
                model_name=model_name, target_gw=target_gw, horizon=horizon
            )
    return 404, {"error": "Not found"}


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

    def _read_json_body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def do_GET(self) -> None:
        api_path = self._api_path()
        if api_path.startswith("/api/"):
            status, payload = handle_dashboard_api("GET", api_path, None)
            if status == 404:
                self.send_error(404, "Not found")
                return
            self._send_json(status, payload)
            return
        super().do_GET()

    def do_POST(self) -> None:
        api_path = self._api_path()
        if not api_path.startswith("/api/"):
            self.send_error(404, "Not found")
            return
        body = self._read_json_body()
        status, payload = handle_dashboard_api("POST", api_path, body)
        if status == 404:
            self.send_error(404, "Not found")
            return
        self._send_json(status, payload)


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
    parser = argparse.ArgumentParser(
        description="Serve Ownership Explorer. Open projects the Primary Model from processed data when JSON is stale. Refresh in the page ingests FPL and re-projects the selected Primary Model. Solve Dream Team paints an Explorer overlay. Refresh and Solve cannot run together."
    )
    parser.add_argument("--model", type=str, default=None, help="Primary model name")
    parser.add_argument("--models", type=str, nargs="+", default=None, help="Comparison Slate override (export all named models)")
    parser.add_argument(
        "--horizon",
        type=int,
        default=DEFAULT_PLANNING_HORIZON,
        help="Planning Horizon length (1-10, default 6)",
    )
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

    processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
    json_path = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
    if should_project_on_open(processed_dir, json_path):
        try:
            logger.info("Processed tables newer than dashboard JSON; projecting without ingest.")
            run_dashboard_export(
                model_name=args.model,
                horizon=args.horizon,
                target_gw=args.target_gw,
                model_names=args.models,
            )
        except FileNotFoundError as exc:
            logger.warning("%s Click Refresh in the page to ingest.", exc)

    start_server(args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
