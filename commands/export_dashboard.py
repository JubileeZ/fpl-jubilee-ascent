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
from models import get_default_model_name, get_model
from projections.explorer_slice import (
    COMPONENT_KEYS,
    GameweekScore,
    planning_horizon_slice,
)
from solver.planning import (
    MAX_PLANNING_HORIZON,
    SEASON_END_GW,
    available_chips,
    clamp_planning_horizon,
    planning_window,
)
from solver.utils import DEFAULT_PLANNING_HORIZON

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROLE_CSV = PROJECT_ROOT / "features/expected-role-gw1-5.csv"
SEASON_START_GW = 1

import math

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
        res = float(val)
        return default if math.isnan(res) or math.isinf(res) else res
    except (ValueError, TypeError):
        return default


def _clean_json_obj(obj: Any) -> Any:
    """Recursively replaces NaN and Infinity with None/null for valid JSON output."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _clean_json_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_json_obj(v) for v in obj]
    return obj


def _load_expected_roles() -> dict[int, str]:
    if not ROLE_CSV.exists():
        return {}
    roles = pd.read_csv(ROLE_CSV)
    if "player_id" not in roles.columns or "expected_role" not in roles.columns:
        return {}
    return dict(zip(roles["player_id"].astype(int), roles["expected_role"].astype(str)))


def _finished_gameweeks(processed_dir: Path) -> set[int]:
    path = processed_dir / "gameweeks.parquet"
    if not path.exists():
        return set()
    df_gw = pd.read_parquet(path)
    if "finished" not in df_gw.columns:
        return set()
    return {int(gid) for gid in df_gw.loc[df_gw["finished"], "id"]}


def unfinished_gameweeks(processed_dir: Path) -> list[int]:
    finished = _finished_gameweeks(processed_dir)
    return [gw for gw in range(1, SEASON_END_GW + 1) if gw not in finished]


def resolve_horizon_start(processed_dir: Path) -> int:
    """Earliest unfinished Gameweek. Live deadline-passed week is allowed."""
    gws = unfinished_gameweeks(processed_dir)
    return gws[0] if gws else 1


def _groupby_predictions(df_pred: pd.DataFrame) -> pd.DataFrame:
    agg: dict[str, str] = {"projected_points": "sum", "projected_minutes": "sum"}
    for col in COMPONENT_KEYS:
        if col in df_pred.columns:
            agg[col] = "sum"
    return df_pred.groupby(["player_id", "gameweek_id"], as_index=False).agg(agg)


def _score_from_pred_row(row: pd.Series) -> GameweekScore:
    return GameweekScore(
        points=_safe_float(row["projected_points"]),
        minutes=_safe_float(row["projected_minutes"]),
        xp_minutes=_safe_float(row.get("xp_minutes")),
        xp_goals=_safe_float(row.get("xp_goals")),
        xp_assists=_safe_float(row.get("xp_assists")),
        xp_clean_sheet=_safe_float(row.get("xp_clean_sheet")),
        xp_conceded=_safe_float(row.get("xp_conceded")),
        xp_defcon=_safe_float(row.get("xp_defcon")),
        xp_saves=_safe_float(row.get("xp_saves")),
        xp_bonus=_safe_float(row.get("xp_bonus")),
    )


def load_transfer_plan_document(solution_path: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Return a Transfer Plan dict, or None if missing, invalid JSON, or legacy solver dump."""
    if not solution_path or not solution_path.exists():
        return None
    try:
        sol = json.loads(solution_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Could not load solver solution from {solution_path}: {e}")
        return None
    if isinstance(sol, dict) and "weeks" in sol and "meta" in sol:
        return sol
    return None


def load_transfer_plan(
    solution_path: Optional[Path],
) -> tuple[List[int], Optional[str], Optional[Dict[str, Any]]]:
    if not solution_path or not solution_path.exists():
        return [], None, None
    try:
        sol = json.loads(solution_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Could not load solver solution from {solution_path}: {e}")
        return [], None, None
    if isinstance(sol, dict) and "weeks" in sol and "meta" in sol:
        weeks = sol.get("weeks") or []
        first = weeks[0] if weeks else {}
        squad_ids = [int(i) for i in first.get("squad_ids") or []]
        return squad_ids, sol.get("meta", {}).get("champion"), sol
    if isinstance(sol, dict) and "picks" in sol:
        prefilled = [p["element"] for p in sol["picks"] if isinstance(p, dict) and "element" in p]
        return prefilled, sol.get("model_name"), None
    return [], None, None


def load_owned_squad(processed_dir: Path) -> tuple[List[int], Optional[int], Optional[int]]:
    """Return User Squad player IDs in Lineup Index order, plus captain and vice IDs."""
    path = processed_dir / "user_picks.parquet"
    if not path.exists():
        return [], None, None
    df = pd.read_parquet(path)
    if df.empty or "player_id" not in df.columns:
        return [], None, None
    ordered = df.sort_values("lineup_index") if "lineup_index" in df.columns else df
    ids = [int(pid) for pid in ordered["player_id"].tolist()]
    captain_id: Optional[int] = None
    vice_id: Optional[int] = None
    if "is_captain" in ordered.columns:
        caps = ordered.loc[ordered["is_captain"].fillna(False).astype(bool)]
        if not caps.empty:
            captain_id = int(caps.iloc[0]["player_id"])
    if "is_vice_captain" in ordered.columns:
        vices = ordered.loc[ordered["is_vice_captain"].fillna(False).astype(bool)]
        if not vices.empty:
            vice_id = int(vices.iloc[0]["player_id"])
    return ids, captain_id, vice_id


def load_user_chips(processed_dir: Path) -> list[dict[str, Any]]:
    path = processed_dir / "user_chips.parquet"
    if not path.exists():
        return []
    df = pd.read_parquet(path)
    if df.empty:
        return []
    return df.to_dict(orient="records")


def build_dashboard_dataset(
    processed_dir: Path,
    predictions_df: pd.DataFrame | Dict[str, pd.DataFrame],
    target_gw: int,
    horizon: int,
    solution_path: Optional[Path] = None,
    default_model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Compiles player metadata, historical rates, and per-GW projections across models into JSON format."""
    horizon = clamp_planning_horizon(horizon)
    players_df = pd.read_parquet(processed_dir / "players.parquet")
    clubs_df = pd.read_parquet(processed_dir / "clubs.parquet")

    club_map = dict(zip(clubs_df["id"], clubs_df["short_name"]))
    club_name_map = dict(zip(clubs_df["id"], clubs_df["name"]))

    if isinstance(predictions_df, pd.DataFrame):
        def_name = default_model_name or get_default_model_name()
        model_preds_map = {def_name: predictions_df}
    else:
        model_preds_map = predictions_df

    model_names = list(model_preds_map.keys())
    primary_model_name = default_model_name if default_model_name in model_preds_map else model_names[0]

    owned_squad_ids, owned_captain_id, owned_vice_captain_id = load_owned_squad(processed_dir)

    unfinished_gws = unfinished_gameweeks(processed_dir)
    horizon_start = int(target_gw)
    if unfinished_gws and horizon_start not in unfinished_gws:
        horizon_start = unfinished_gws[0]
    horizon_end = min(horizon_start + horizon - 1, SEASON_END_GW)
    planning_gw_ids = planning_window(horizon_start, horizon_end)
    planning_gw_set = set(planning_gw_ids)
    finished_gws = _finished_gameweeks(processed_dir)
    expected_roles = _load_expected_roles()

    grouped_models: Dict[str, pd.DataFrame] = {}
    all_gw_ids: set[int] = set(planning_gw_ids)

    for m_name, df_pred in model_preds_map.items():
        gw_grp = _groupby_predictions(df_pred)
        grouped_models[m_name] = gw_grp
        all_gw_ids.update(int(g) for g in gw_grp["gameweek_id"].unique().tolist())

    gw_ids = sorted(all_gw_ids) if all_gw_ids else planning_gw_ids

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

        g_pts_factor = _GOAL_POINTS.get(pos_id, 5.0)
        cs_pts_factor = _CLEAN_SHEET_POINTS.get(pos_id, 1.0)
        defcon_pts_factor = _DEFCON_POINTS.get(pos_id, 0.0)

        player_models_dict: Dict[str, Any] = {}

        for m_name, gw_grouped in grouped_models.items():
            p_preds = gw_grouped[gw_grouped["player_id"] == pid]
            projections: Dict[str, Dict[str, float]] = {}
            total_xp_horizon = 0.0
            total_xmins_horizon = 0.0
            projection_by_gw: dict[int, GameweekScore] = {}

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
                    xp_min = _safe_float(r.get("xp_minutes"))
                    xp_conc = _safe_float(r.get("xp_conceded"))
                    xp_saves = _safe_float(r.get("xp_saves"))
                    xg_pts = round(xp_g * g_pts_factor, 2)
                    xa_pts = round(xp_a * _ASSIST_POINTS, 2)
                    xcs_pts = round(xp_cs * cs_pts_factor, 2)
                    xdefcon_pts = round(xp_def * defcon_pts_factor, 2)
                    xb_pts = round(xp_b, 2)
                    projection_by_gw[gw] = _score_from_pred_row(r)
                else:
                    xp_pts = 0.0
                    xmins = 0.0
                    xg_pts = 0.0
                    xa_pts = 0.0
                    xcs_pts = 0.0
                    xdefcon_pts = 0.0
                    xb_pts = 0.0
                    xp_min = 0.0
                    xp_conc = 0.0
                    xp_saves = 0.0

                projections[f"gw{gw}"] = {
                    "total_xp": xp_pts,
                    "xmins": xmins,
                    "xg_pts": xg_pts,
                    "xa_pts": xa_pts,
                    "xcs_pts": xcs_pts,
                    "xdefcon_pts": xdefcon_pts,
                    "xb_pts": xb_pts,
                    "xp_minutes": xp_min,
                    "xp_conceded": xp_conc,
                    "xp_saves": xp_saves,
                }
                if gw in planning_gw_set:
                    total_xp_horizon += xp_pts
                    total_xmins_horizon += xmins

            explorer = {"planning_horizon": planning_horizon_slice(projection_by_gw, planning_gw_ids)}
            player_models_dict[m_name] = {
                "projections": projections,
                "total_xp_horizon": round(total_xp_horizon, 2),
                "total_xmins_horizon": round(total_xmins_horizon, 1),
                "explorer": explorer,
            }

        primary_model_data = player_models_dict.get(primary_model_name) or list(player_models_dict.values())[0]

        web_name = str(p.get("web_name", f"Player {pid}"))
        first_name = str(p.get("first_name", ""))
        second_name = str(p.get("second_name", ""))

        raw_chance = p.get("chance_of_playing_next_round")
        chance_val = None if pd.isna(raw_chance) or raw_chance is None else int(raw_chance)

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
            "chance": chance_val,
            "news": str(p.get("news", "") or ""),
            "ownership_pct": round(_safe_float(p.get("selected_by_percent")), 1),
            "expected_role": expected_roles.get(pid, ""),
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
            "models": player_models_dict,
            "projections": primary_model_data["projections"],
            "total_xp_horizon": primary_model_data["total_xp_horizon"],
            "total_xmins_horizon": primary_model_data["total_xmins_horizon"],
            "explorer": primary_model_data["explorer"],
        }
        players_data.append(player_dict)

    user_chips = load_user_chips(processed_dir)
    _ = solution_path
    dataset = {
        "meta": {
            "target_gw": horizon_start,
            "horizon": horizon,
            "horizon_start": horizon_start,
            "horizon_end": horizon_end,
            "max_horizon": MAX_PLANNING_HORIZON,
            "gw_ids": gw_ids,
            "planning_gw_ids": planning_gw_ids,
            "unfinished_gameweeks": unfinished_gws,
            "finished_gameweeks": sorted(finished_gws),
            "available_chips": available_chips(planning_gw_ids, user_chips),
            "models": model_names,
            "default_model": primary_model_name,
            "owned_squad_ids": owned_squad_ids,
            "owned_captain_id": owned_captain_id,
            "owned_vice_captain_id": owned_vice_captain_id,
        },
        "players": players_data,
    }
    return dataset


def export_dashboard_data(data: Dict[str, Any], output_path: Path) -> None:
    cleaned = _clean_json_obj(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)
    logger.info(f"Dashboard data exported successfully to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export player projections and stats for dashboard.")
    parser.add_argument("--model", type=str, default=None, help="Primary model name")
    parser.add_argument("--models", type=str, nargs="+", default=None, help="List of model names to export")
    parser.add_argument("--horizon", type=int, default=DEFAULT_PLANNING_HORIZON, help="Planning horizon")
    parser.add_argument("--target_gw", type=int, help="Target starting gameweek")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "dashboard_data.json",
        help="JSON output path",
    )
    args = parser.parse_args()

    # Determine model list to export
    if args.models:
        model_names = args.models
    elif args.model:
        model_names = [args.model]
    else:
        try:
            from models.selection import load_model_selection
            sel = load_model_selection()
            model_names = list(dict.fromkeys([sel.champion, *sel.candidates]))
        except Exception:
            model_names = [get_default_model_name()]

    default_model = args.model or model_names[0]

    processed_dir = PROJECT_ROOT / "data" / "processed"
    if not processed_dir.exists():
        logger.error("No processed data found. Please run 'python -m commands.refresh_data' first.")
        sys.exit(1)

    if args.target_gw is not None:
        target_gw = args.target_gw
    else:
        target_gw = resolve_horizon_start(processed_dir)

    args.horizon = clamp_planning_horizon(args.horizon)
    logger.info(
        f"Building Full-Season Window features GW{SEASON_START_GW}–{SEASON_END_GW}; "
        f"Planning Horizon {args.horizon} from GW{target_gw}"
    )
    df_feat = build_features(processed_dir, SEASON_START_GW, horizon=SEASON_END_GW)

    model_preds: Dict[str, pd.DataFrame] = {}
    perf_path = processed_dir / "player_performances.parquet"
    df_perf = pd.read_parquet(perf_path) if perf_path.exists() else None

    for m_name in model_names:
        logger.info(f"Generating projections using model '{m_name}'...")
        model = get_model(m_name)
        if hasattr(model, "fit") and df_perf is not None:
            model.fit(df_perf[df_perf["gameweek_id"] < target_gw])
        model_preds[m_name] = model.predict(df_feat, SEASON_END_GW)

    dataset = build_dashboard_dataset(
        processed_dir,
        model_preds,
        target_gw,
        args.horizon,
        default_model_name=default_model,
    )

    output_path = args.output
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    export_dashboard_data(dataset, output_path)


if __name__ == "__main__":
    main()

