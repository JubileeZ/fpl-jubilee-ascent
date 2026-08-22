import argparse
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
    load_transfer_plan_document,
    load_user_chips,
)
from commands.solve import CHIP_KEYS, execute_transfer_plan, transfer_plan_options_for_dashboard
from solver.planning import available_chips, clamp_planning_horizon, planning_gameweeks
from features.builder import build_features
from models import get_default_model_name, get_model
from projections.exporter import (
    export_projections,
    pad_solver_csv_horizon,
    solver_csv_covers_horizon,
    write_solver_projection_csvs,
)
from solver.utils import DEFAULT_PLANNING_HORIZON
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SOLUTION_PATH = PROJECT_ROOT / "data" / "solution.json"


def resolve_next_gw(processed_dir: Path, preseason: bool) -> int:
    try:
        df_gw = pd.read_parquet(processed_dir / "gameweeks.parquet")
        next_gw = df_gw[df_gw["is_next"]]
        if not next_gw.empty:
            return int(next_gw.iloc[0]["id"])
        unfinished = df_gw[~df_gw["finished"]]
        if not unfinished.empty:
            return int(unfinished.iloc[0]["id"])
    except Exception:
        pass
    return 1 if preseason else 38


def ensure_solver_projection_csv(
    model_name: str,
    processed_dir: Path,
    target_gw: int,
    horizon: int,
    output_dir: Path,
) -> Path:
    """Rebuild Champion ProjectionContract CSV when MILP weeks are missing."""
    csv_path = output_dir / f"{model_name}.csv"
    if solver_csv_covers_horizon(csv_path, target_gw, horizon):
        return csv_path
    logger.info(
        f"{csv_path.name} missing {horizon}-GW columns from GW{target_gw}; regenerating for Transfer Plan"
    )
    df_feat = build_features(processed_dir, target_gw, horizon=horizon)
    model = get_model(model_name)
    perf_path = processed_dir / "player_performances.parquet"
    if hasattr(model, "fit") and perf_path.exists():
        df_perf = pd.read_parquet(perf_path)
        model.fit(df_perf[df_perf["gameweek_id"] < target_gw])
    df_pred = model.predict(df_feat, horizon)
    df_players = pd.read_parquet(processed_dir / "players.parquet")
    df_clubs = pd.read_parquet(processed_dir / "clubs.parquet")
    export_projections(df_pred, df_players, df_clubs, csv_path)
    pad_solver_csv_horizon(csv_path, target_gw, horizon)
    return csv_path


def run_dashboard_transfer_plan(payload: dict[str, object]) -> dict[str, object]:
    processed_dir = PROJECT_ROOT / "data" / "processed"
    booked: dict[str, list[int]] = {}
    for key in CHIP_KEYS:
        raw = payload.get(key, [])
        values = raw if isinstance(raw, list) else []
        booked[key] = [int(g) for g in values]
    preseason = bool(payload.get("preseason")) or not (processed_dir / "user_picks.parquet").exists()
    target_gw = int(payload["target_gw"]) if payload.get("target_gw") else resolve_next_gw(processed_dir, preseason)
    horizon = clamp_planning_horizon(int(payload.get("horizon") or DEFAULT_PLANNING_HORIZON))
    gws = planning_gameweeks(target_gw, horizon)
    user_chips = [] if preseason else load_user_chips(processed_dir)
    available = available_chips(gws, user_chips)
    enabled = [item for item in (payload.get("enabled_chips") or []) if isinstance(item, dict)]
    force_keep = [item for item in (payload.get("force_keep") or []) if isinstance(item, dict)]
    force_ban = [item for item in (payload.get("force_ban") or []) if isinstance(item, dict)]
    options = transfer_plan_options_for_dashboard(
        booked,
        horizon,
        enabled_chips=enabled,
        force_keep=force_keep,
        force_ban=force_ban,
        available=available,
        target_gw=target_gw,
    )
    options["preseason"] = preseason
    ensure_solver_projection_csv(
        str(options["datasource"]),
        processed_dir,
        target_gw,
        horizon,
        PROJECT_ROOT / "data",
    )
    return execute_transfer_plan(
        options,
        processed_dir=processed_dir,
        target_gw=target_gw,
        solution_path=SOLUTION_PATH,
    )


class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serves dashboard/ without caching; Transfer Plan Re-solve on /api/transfer-plan."""

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

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0].rstrip("/") == "/api/transfer-plan":
            plan = load_transfer_plan_document(SOLUTION_PATH)
            if plan is None:
                self._send_json(404, {"error": "No Transfer Plan yet. Re-solve or run commands.solve."})
            else:
                self._send_json(200, plan)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0].rstrip("/") != "/api/transfer-plan":
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
            plan = run_dashboard_transfer_plan(payload if isinstance(payload, dict) else {})
            self._send_json(200, plan)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            logger.exception("Transfer Plan Re-solve failed")
            self._send_json(500, {"error": str(exc)})


def run_dashboard_export(
    model_name: str | None = None,
    horizon: int = DEFAULT_PLANNING_HORIZON,
    target_gw: int | None = None,
    model_names: list[str] | None = None,
) -> Path:
    processed_dir = PROJECT_ROOT / "data" / "processed"
    if not processed_dir.exists():
        logger.error("No processed data found. Run 'python -m commands.refresh_data' first.")
        sys.exit(1)

    if model_names is None:
        if model_name:
            model_names = [model_name]
        else:
            try:
                from models.selection import load_model_selection
                sel = load_model_selection()
                model_names = list(dict.fromkeys([sel.champion, *sel.candidates]))
            except Exception:
                model_names = [get_default_model_name()]

    default_model = model_name or model_names[0]

    horizon = clamp_planning_horizon(horizon)
    if target_gw is None:
        try:
            df_gw = pd.read_parquet(processed_dir / "gameweeks.parquet")
            next_gw = df_gw[df_gw["is_next"]]
            if not next_gw.empty:
                target_gw = int(next_gw.iloc[0]["id"])
            else:
                unfinished = df_gw[~df_gw["finished"]]
                target_gw = int(unfinished.iloc[0]["id"]) if not unfinished.empty else 1
        except Exception:
            target_gw = 1

    logger.info(
        f"Generating Full-Season Window projections GW{SEASON_START_GW}–{SEASON_END_GW}; "
        f"pitch Planning Horizon {horizon} from GW{target_gw}"
    )
    df_feat = build_features(processed_dir, SEASON_START_GW, horizon=SEASON_END_GW)

    model_preds: dict[str, pd.DataFrame] = {}
    perf_path = processed_dir / "player_performances.parquet"
    df_perf = pd.read_parquet(perf_path) if perf_path.exists() else None

    for m_name in model_names:
        logger.info(f"Loading model '{m_name}'...")
        model = get_model(m_name)
        if hasattr(model, "fit") and df_perf is not None:
            model.fit(df_perf[df_perf["gameweek_id"] < target_gw])
        model_preds[m_name] = model.predict(df_feat, SEASON_END_GW)

    sol_path = SOLUTION_PATH
    dataset = build_dashboard_dataset(
        processed_dir,
        model_preds,
        target_gw,
        horizon,
        sol_path,
        default_model_name=default_model,
    )
    df_players = pd.read_parquet(processed_dir / "players.parquet")
    df_clubs = pd.read_parquet(processed_dir / "clubs.parquet")
    write_solver_projection_csvs(model_preds, df_players, df_clubs, PROJECT_ROOT / "data")

    dashboard_dir = PROJECT_ROOT / "dashboard"
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    json_path = dashboard_dir / "dashboard_data.json"
    export_dashboard_data(dataset, json_path)

    # Also keep a copy in data/
    data_json_path = PROJECT_ROOT / "data" / "dashboard_data.json"
    data_json_path.parent.mkdir(parents=True, exist_ok=True)
    export_dashboard_data(dataset, data_json_path)

    return json_path


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
    parser = argparse.ArgumentParser(description="Export dashboard data and launch interactive web dashboard.")
    parser.add_argument("--model", type=str, default=None, help="Primary model name")
    parser.add_argument("--models", type=str, nargs="+", default=None, help="List of model names to export")
    parser.add_argument("--horizon", type=int, default=DEFAULT_PLANNING_HORIZON, help="Planning horizon")
    parser.add_argument("--target_gw", type=int, help="Target starting gameweek")
    parser.add_argument("--port", type=int, default=8000, help="Local HTTP server port")
    parser.add_argument("--export-only", action="store_true", help="Only refresh export data without launching server")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")

    args = parser.parse_args()

    run_dashboard_export(
        model_name=args.model,
        horizon=args.horizon,
        target_gw=args.target_gw,
        model_names=args.models,
    )

    if not args.export_only:
        start_server(args.port, open_browser=not args.no_browser)




if __name__ == "__main__":
    main()
