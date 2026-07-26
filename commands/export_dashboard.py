import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from features.builder import build_features
from models import get_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_POS_MAP = {1: "G", 2: "D", 3: "M", 4: "F"}
_POS_NAME_MAP = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}

_GOAL_POINTS = {1: 10.0, 2: 6.0, 3: 5.0, 4: 4.0}
_ASSIST_POINTS = 3.0
_CLEAN_SHEET_POINTS = {1: 4.0, 2: 4.0, 3: 1.0, 4: 0.0}
_DEFCON_POINTS = {1: 0.0, 2: 2.0, 3: 2.0, 4: 0.0}


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or pd.isna(val):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def build_dashboard_dataset(
    processed_dir: Path,
    predictions_df: pd.DataFrame,
    target_gw: int,
    horizon: int,
    solution_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Compiles player metadata, historical rates, and per-GW projections into JSON format."""
    players_df = pd.read_parquet(processed_dir / "players.parquet")
    clubs_df = pd.read_parquet(processed_dir / "clubs.parquet")

    club_map = dict(zip(clubs_df["id"], clubs_df["short_name"]))
    club_name_map = dict(zip(clubs_df["id"], clubs_df["name"]))

    # Check for latest solver solution if available
    prefilled_squad_ids: List[int] = []
    if solution_path and solution_path.exists():
        try:
            with open(solution_path, "r", encoding="utf-8") as f:
                sol = json.load(f)
                if "picks" in sol:
                    prefilled_squad_ids = [p["element"] for p in sol["picks"] if "element" in p]
        except Exception as e:
            logger.warning(f"Could not load solver solution from {solution_path}: {e}")

    # Group predictions by (player_id, gameweek_id) in case of multiple fixtures per GW
    gw_grouped = (
        predictions_df.groupby(["player_id", "gameweek_id"], as_index=False)
        .agg({
            "projected_points": "sum",
            "projected_minutes": "sum",
            "xp_goals": "sum",
            "xp_assists": "sum",
            "xp_clean_sheet": "sum",
            "xp_defcon": "sum",
            "xp_bonus": "sum",
        })
    )

    gw_ids = sorted(gw_grouped["gameweek_id"].unique().tolist())
    if not gw_ids:
        gw_ids = list(range(target_gw, target_gw + horizon))

    players_data: List[Dict[str, Any]] = []

    for _, p in players_df.iterrows():
        pid = int(p["id"])
        pos_id = int(p["position_id"])
        pos_code = _POS_MAP.get(pos_id, "M")
        pos_name = _POS_NAME_MAP.get(pos_id, "Midfielder")
        club_id = int(p["club_id"])
        team_short = club_map.get(club_id, "UNK")
        team_full = club_name_map.get(club_id, "Unknown")

        total_pts = _safe_float(p.get("total_points"))
        mins = _safe_float(p.get("minutes"))
        starts = _safe_float(p.get("starts"))
        ict = _safe_float(p.get("ict_index"))
        inf = _safe_float(p.get("influence"))
        cre = _safe_float(p.get("creativity"))
        thr = _safe_float(p.get("threat"))
        xg = _safe_float(p.get("expected_goals"))
        xa = _safe_float(p.get("expected_assists"))

        pts_per_start = round(total_pts / starts, 2) if starts > 0 else 0.0
        pts_per_90 = round((total_pts / mins) * 90.0, 2) if mins > 0 else 0.0
        ict_per_90 = round((ict / mins) * 90.0, 2) if mins > 0 else 0.0
        inf_per_90 = round((inf / mins) * 90.0, 2) if mins > 0 else 0.0
        cre_per_90 = round((cre / mins) * 90.0, 2) if mins > 0 else 0.0
        thr_per_90 = round((thr / mins) * 90.0, 2) if mins > 0 else 0.0
        xg_per_90 = round((xg / mins) * 90.0, 2) if mins > 0 else 0.0
        xa_per_90 = round((xa / mins) * 90.0, 2) if mins > 0 else 0.0

        p_preds = gw_grouped[gw_grouped["player_id"] == pid]

        projections: Dict[str, Dict[str, float]] = {}
        total_xp_horizon = 0.0
        total_xmins_horizon = 0.0

        g_pts_factor = _GOAL_POINTS.get(pos_id, 5.0)
        cs_pts_factor = _CLEAN_SHEET_POINTS.get(pos_id, 1.0)
        defcon_pts_factor = _DEFCON_POINTS.get(pos_id, 0.0)

        for gw in gw_ids:
            gw_row = p_preds[p_preds["gameweek_id"] == gw]
            if not gw_row.empty:
                r = gw_row.iloc[0]
                xp_pts = round(_safe_float(r["projected_points"]), 2)
                xmins = round(_safe_float(r["projected_minutes"]), 1)
                xp_g = _safe_float(r.get("xp_goals"))
                xp_a = _safe_float(r.get("xp_assists"))
                xp_cs = _safe_float(r.get("xp_clean_sheet"))
                xp_def = _safe_float(r.get("xp_defcon"))
                xp_b = _safe_float(r.get("xp_bonus"))

                xg_pts = round(xp_g * g_pts_factor, 2)
                xa_pts = round(xp_a * _ASSIST_POINTS, 2)
                xcs_pts = round(xp_cs * cs_pts_factor, 2)
                xdefcon_pts = round(xp_def * defcon_pts_factor, 2)
                xb_pts = round(xp_b, 2)
            else:
                xp_pts = 0.0
                xmins = 0.0
                xg_pts = 0.0
                xa_pts = 0.0
                xcs_pts = 0.0
                xdefcon_pts = 0.0
                xb_pts = 0.0

            projections[f"gw{gw}"] = {
                "total_xp": xp_pts,
                "xmins": xmins,
                "xg_pts": xg_pts,
                "xa_pts": xa_pts,
                "xcs_pts": xcs_pts,
                "xdefcon_pts": xdefcon_pts,
                "xb_pts": xb_pts,
            }
            total_xp_horizon += xp_pts
            total_xmins_horizon += xmins

        web_name = str(p.get("web_name", f"Player {pid}"))
        first_name = str(p.get("first_name", ""))
        second_name = str(p.get("second_name", ""))

        player_dict = {
            "id": pid,
            "code": int(p.get("code", pid)),
            "name": web_name,
            "full_name": f"{first_name} {second_name}".strip(),
            "pos": pos_code,
            "pos_name": pos_name,
            "pos_id": pos_id,
            "team": team_short,
            "team_full": team_full,
            "team_id": club_id,
            "price": round(_safe_float(p.get("now_cost")) / 10.0, 1),
            "status": str(p.get("status", "a")),
            "chance": p.get("chance_of_playing_next_round"),
            "news": str(p.get("news", "") or ""),
            "pts_per_start": pts_per_start,
            "pts_per_90": pts_per_90,
            "ict_per_90": ict_per_90,
            "inf_per_90": inf_per_90,
            "cre_per_90": cre_per_90,
            "thr_per_90": thr_per_90,
            "xg_per_90": xg_per_90,
            "xa_per_90": xa_per_90,
            "total_points": int(total_pts),
            "minutes": int(mins),
            "starts": int(starts),
            "projections": projections,
            "total_xp_horizon": round(total_xp_horizon, 2),
            "total_xmins_horizon": round(total_xmins_horizon, 1),
        }
        players_data.append(player_dict)

    dataset = {
        "meta": {
            "target_gw": target_gw,
            "horizon": horizon,
            "gw_ids": gw_ids,
            "prefilled_squad_ids": prefilled_squad_ids,
        },
        "players": players_data,
    }
    return dataset


def export_dashboard_data(data: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Dashboard data exported successfully to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export player projections and stats for dashboard.")
    parser.add_argument("--model", type=str, default="metrics_component_hybrid", help="Model name")
    parser.add_argument("--horizon", type=int, default=5, help="Planning horizon")
    parser.add_argument("--target_gw", type=int, help="Target starting gameweek")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "dashboard_data.json",
        help="JSON output path",
    )
    args = parser.parse_args()

    processed_dir = PROJECT_ROOT / "data" / "processed"
    if not processed_dir.exists():
        logger.error("No processed data found. Please run 'python -m commands.refresh_data' first.")
        sys.exit(1)

    if args.target_gw is not None:
        target_gw = args.target_gw
    else:
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

    logger.info(f"Building features starting GW {target_gw} over {args.horizon} horizon...")
    df_feat = build_features(processed_dir, target_gw, horizon=args.horizon)

    logger.info(f"Generating projections using model '{args.model}'...")
    model = get_model(args.model)
    perf_path = processed_dir / "player_performances.parquet"
    if hasattr(model, "fit") and perf_path.exists():
        df_perf = pd.read_parquet(perf_path)
        model.fit(df_perf[df_perf["gameweek_id"] < target_gw])

    df_proj = model.predict(df_feat, args.horizon)

    sol_path = PROJECT_ROOT / "data" / "solution.json"
    dataset = build_dashboard_dataset(processed_dir, df_proj, target_gw, args.horizon, sol_path)

    output_path = args.output
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    export_dashboard_data(dataset, output_path)


if __name__ == "__main__":
    main()
