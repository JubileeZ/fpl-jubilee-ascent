import argparse
import http.server
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
    build_dashboard_dataset,
    export_dashboard_data,
)
from features.builder import build_features
from models import get_default_model_name, get_model
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler ensuring dashboard/ is served correctly without caching."""

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = str(PROJECT_ROOT / "dashboard")
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def run_dashboard_export(
    model_name: str | None = None,
    horizon: int = 5,
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

    logger.info(f"Generating projections starting GW {target_gw} over {horizon} GW horizon...")
    df_feat = build_features(processed_dir, target_gw, horizon=horizon)

    model_preds: dict[str, pd.DataFrame] = {}
    perf_path = processed_dir / "player_performances.parquet"
    df_perf = pd.read_parquet(perf_path) if perf_path.exists() else None

    for m_name in model_names:
        logger.info(f"Loading model '{m_name}'...")
        model = get_model(m_name)
        if hasattr(model, "fit") and df_perf is not None:
            model.fit(df_perf[df_perf["gameweek_id"] < target_gw])
        model_preds[m_name] = model.predict(df_feat, horizon)

    sol_path = PROJECT_ROOT / "data" / "solution.json"
    dataset = build_dashboard_dataset(
        processed_dir,
        model_preds,
        target_gw,
        horizon,
        sol_path,
        default_model_name=default_model,
    )

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

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    try:
        with ReusableTCPServer(("", port), handler) as httpd:
            url = f"http://localhost:{port}"
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
    parser.add_argument("--horizon", type=int, default=5, help="Planning horizon")
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
