import argparse
import asyncio
import http.server
import json
import logging
from pathlib import Path
import sys
import threading
from typing import Any
from urllib.parse import parse_qs
import uuid

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.env_loader import configure_utf8_stdio, load_env

load_env()
configure_utf8_stdio()

from commands.export_dashboard import (
    PROJECT_ROOT,
    load_owned_picks,
    load_user_state,
    run_dashboard_export,
)
from commands.dream_team import execute_dream_team
from dashboard.content import get_model_methodology, get_research_topic_detail, get_research_topics
from commands.solve import execute_transfer_plan
from commands.transfer_plan_scenarios import (
    SCENARIOS_PATH,
    UserSquadRequired,
    execute_transfer_plan_scenarios,
    mark_scenarios_stale,
)
from commands import refresh_data
from features.builder import resolve_operational_processed_dir
from features.expected_role_prior import LIVE_SEASON
from models import get_default_model_name
from solver.planning import clamp_planning_horizon, planning_window, resolve_default_target_gw
from solver.utils import DEFAULT_PLANNING_HORIZON, load_settings

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
_plan_lock = threading.Lock()
_plan_state: dict[str, object] = {
    "status": "idle",
    "error": None,
    "detail": None,
    "payload": None,
}
_strategy_lock = threading.Lock()
_strategy_state: dict[str, object] = {
    "status": "idle",
    "error": None,
    "detail": None,
    "payload": None,
}


def should_project_on_open(processed_dir: Path, json_path: Path) -> bool:
    """True when processed tables exist and JSON is missing, older than them, or lacks the current Champion."""
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
    try:
        projected = json.loads(json_path.read_text(encoding="utf-8")).get("meta", {}).get("models") or []
    except (OSError, ValueError, AttributeError):
        return True
    return get_default_model_name() not in projected


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


def transfer_plan_status() -> dict[str, object]:
    with _plan_lock:
        return dict(_plan_state)


def _set_plan_state(**kwargs: object) -> None:
    with _plan_lock:
        _plan_state.update(kwargs)


def reset_transfer_plan_state() -> None:
    _set_plan_state(status="idle", error=None, detail=None, payload=None)


def ingest_live_data(season: str = LIVE_SEASON) -> None:
    """FPL ingest plus Official-only Live Season Pin. Does not scrape lineups. Does not git commit."""
    asyncio.run(refresh_data.main(["--season", season]))


def posted_primary_model(body: dict[str, object] | None) -> str:
    """Posted Primary Model, or Champion when missing/placeholder `default`/unknown/retired."""
    from models import resolve_model_name

    raw = str((body or {}).get("model") or "").strip()
    if not raw or raw.lower() == "default":
        return get_default_model_name()
    try:
        return resolve_model_name(raw)
    except ValueError:
        return get_default_model_name()




def run_refresh_job(
    model_name: str | None = None,
    horizon: int = DEFAULT_PLANNING_HORIZON,
    model_names: list[str] | None = None,
) -> None:
    try:
        _set_refresh_state(status="running", error=None, detail="Ingesting FPL data…")
        reset_dream_team_state()
        reset_transfer_plan_state()
        stale = mark_scenarios_stale(SCENARIOS_PATH)
        if stale is not None:
            _set_plan_state(
                status="idle",
                error=None,
                detail="Scenarios stale after Refresh — Solve again for current projections.",
                payload=stale,
            )
        ingest_live_data()
        _set_refresh_state(status="running", error=None, detail="Projecting models…")
        run_dashboard_export(model_name=model_name, horizon=horizon, model_names=model_names)
        _set_refresh_state(status="ok", error=None, detail="Charts updated.")

        processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
        payload = _loaded_scenarios()
        if payload and isinstance(payload.get("meta"), dict):
            cached_digest = payload["meta"].get("data_digest")
            if cached_digest:
                from solver.scenarios import compute_scenarios_digest
                from commands.transfer_plan_scenarios import write_scenarios_payload
                target_gw = int(payload["meta"].get("target_gw", 1))
                h = int(payload["meta"].get("horizon", horizon))
                champ = str(payload["meta"].get("champion", get_default_model_name()))
                new_digest = compute_scenarios_digest(
                    processed_dir=processed_dir,
                    target_gw=target_gw,
                    horizon=h,
                    champion=champ,
                )
                if new_digest == cached_digest:
                    payload["meta"]["stale"] = False
                    write_scenarios_payload(SCENARIOS_PATH, payload)
                    _set_plan_state(
                        status="ok",
                        error=None,
                        detail="Transfer Plan Scenarios up-to-date (data unchanged).",
                        payload=payload,
                    )
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
        if transfer_plan_status()["status"] == "running":
            return 409, {
                "status": "error",
                "error": "Transfer Plan Solve is running. Wait for it to finish.",
                "detail": "Transfer Plan Solve is running. Wait for it to finish.",
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
        if transfer_plan_status()["status"] == "running":
            return 409, {
                "status": "error",
                "error": "Transfer Plan Solve is running. Wait for it to finish.",
                "detail": "Transfer Plan Solve is running. Wait for it to finish.",
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


def _load_dashboard_dataset() -> dict[str, object]:
    json_path = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
    if not json_path.exists():
        raise FileNotFoundError("No dashboard_data.json yet. Click Refresh.")
    return json.loads(json_path.read_text(encoding="utf-8"))


def run_transfer_plan_job(
    *,
    target_gw: int,
    horizon: int,
    booked_chips: dict[str, list[int]],
    enabled_chips: list[dict[str, object]],
    force_keep: list[dict[str, object]] | None = None,
) -> None:
    try:
        _set_plan_state(
            status="running",
            error=None,
            detail="Solving Transfer Plan Scenarios…",
            payload=None,
        )
        processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
        dataset = _load_dashboard_dataset()

        def on_progress(partial: dict[str, object]) -> None:
            meta = partial.get("meta") or {}
            done = len(meta.get("completed_arms") or [])
            total = len(meta.get("arms") or [])
            pending = meta.get("pending_arms") or []
            pending_txt = ", ".join(str(a) for a in pending) if pending else "none"
            _set_plan_state(
                status="running",
                error=None,
                detail=f"Solved {done}/{total} arms · pending: {pending_txt}",
                payload=partial,
            )

        payload = execute_transfer_plan_scenarios(
            processed_dir=processed_dir,
            target_gw=target_gw,
            horizon=horizon,
            dataset=dataset,
            booked_chips=booked_chips,
            enabled_chips=enabled_chips,
            force_keep=force_keep or [],
            on_progress=on_progress,
        )
        _set_plan_state(status="ok", error=None, detail="Transfer Plan Scenarios ready.", payload=payload)
    except UserSquadRequired as exc:
        _set_plan_state(status="error", error=str(exc), detail=str(exc), payload=None)
    except Exception as exc:
        logger.exception("Transfer Plan Solve failed")
        _set_plan_state(status="error", error=str(exc), detail="Solve failed.", payload=None)


def _active_job_conflict() -> tuple[int, dict[str, object]] | None:
    if refresh_status()["status"] == "running":
        return 409, {
            "status": "error",
            "error": "Refresh is running. Wait for it to finish.",
            "detail": "Refresh is running. Wait for it to finish.",
        }
    if dream_team_status()["status"] == "running":
        return 409, {
            "status": "error",
            "error": "Dream Team Solve is running. Wait for it to finish.",
            "detail": "Dream Team Solve is running. Wait for it to finish.",
        }
    return None


def start_transfer_plan(
    *,
    target_gw: int,
    horizon: int,
    booked_chips: dict[str, list[int]],
    enabled_chips: list[dict[str, object]],
    force_keep: list[dict[str, object]] | None = None,
) -> tuple[int, dict[str, object]]:
    with _job_lock:
        conflict = _active_job_conflict()
        if conflict:
            return conflict
        if strategy_solve_status()["status"] == "running":
            return 409, {
                "status": "error",
                "error": "Strategy Solve is running. Wait for it to finish.",
                "detail": "Strategy Solve is running. Wait for it to finish.",
            }
        with _plan_lock:
            if _plan_state["status"] == "running":
                return 202, dict(_plan_state)
            _plan_state["status"] = "running"
            _plan_state["error"] = None
            _plan_state["detail"] = "Starting…"
            _plan_state["payload"] = None
    threading.Thread(
        target=run_transfer_plan_job,
        kwargs={
            "target_gw": target_gw,
            "horizon": horizon,
            "booked_chips": booked_chips,
            "enabled_chips": enabled_chips,
            "force_keep": force_keep or [],
        },
        daemon=True,
    ).start()
    return 202, transfer_plan_status()


def _booked_chips_from_body(body: dict[str, object] | None) -> dict[str, list[int]]:
    raw = (body or {}).get("booked_chips")
    chips = {"use_wc": [], "use_bb": [], "use_fh": [], "use_tc": []}
    if not isinstance(raw, dict):
        return chips
    for key in chips:
        values = raw.get(key) or []
        if isinstance(values, list):
            chips[key] = [int(v) for v in values]
    return chips


def _enabled_chips_from_body(body: dict[str, object] | None) -> list[dict[str, object]]:
    raw = (body or {}).get("enabled_chips") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, object]] = []
    for item in raw:
        if isinstance(item, dict) and item.get("chip"):
            out.append(item)
    return out


def _force_keep_from_body(body: dict[str, object] | None, target_gw: int = 1) -> list[dict[str, object]]:
    raw = (body or {}).get("force_keep") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, object]] = []
    for item in raw:
        if isinstance(item, dict) and "player_id" in item:
            gw = int(item.get("gw") or target_gw)
            out.append({"player_id": int(item["player_id"]), "gw": gw})
        elif isinstance(item, (int, str)):
            try:
                out.append({"player_id": int(item), "gw": int(target_gw)})
            except ValueError:
                pass
    return out


def _transfer_plan_args(
    body: dict[str, object] | None,
) -> tuple[int, int, dict[str, list[int]], list[dict[str, object]], list[dict[str, object]]]:
    processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
    target_gw = resolve_default_target_gw(processed_dir)
    horizon = clamp_planning_horizon(int((body or {}).get("horizon") or DEFAULT_PLANNING_HORIZON))
    return (
        target_gw,
        horizon,
        _booked_chips_from_body(body),
        _enabled_chips_from_body(body),
        _force_keep_from_body(body, target_gw),
    )


def _loaded_scenarios() -> dict[str, object] | None:
    if not SCENARIOS_PATH.exists():
        return None
    try:
        payload = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


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


def strategy_solve_status() -> dict[str, object]:
    with _strategy_lock:
        return dict(_strategy_state)


def _set_strategy_state(
    *,
    status: str,
    error: str | None = None,
    detail: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    with _strategy_lock:
        _strategy_state["status"] = status
        _strategy_state["error"] = error
        _strategy_state["detail"] = detail
        if payload is not None or status != "running":
            _strategy_state["payload"] = payload


def _resolve_player_ids(values: object, processed_dir: Path) -> list[int]:
    if not values:
        return []
    raw_list: list[str | int]
    if isinstance(values, str):
        raw_list = [v.strip() for v in values.split(",") if v.strip()]
    elif isinstance(values, list):
        raw_list = values
    else:
        return []

    name_to_id: dict[str, int] = {}
    players_path = processed_dir / "players.parquet"
    if players_path.exists():
        try:
            df = pd.read_parquet(players_path)
            if "id" in df.columns:
                for _, row in df.iterrows():
                    pid = int(row["id"])
                    if "web_name" in row and pd.notna(row["web_name"]):
                        name_to_id[str(row["web_name"]).strip().lower()] = pid
                    if "second_name" in row and pd.notna(row["second_name"]):
                        name_to_id[str(row["second_name"]).strip().lower()] = pid
                    if "first_name" in row and "second_name" in row and pd.notna(row["first_name"]) and pd.notna(row["second_name"]):
                        name_to_id[f"{row['first_name']} {row['second_name']}".strip().lower()] = pid
        except Exception as exc:
            logger.warning("Could not build player name lookup: %s", exc)

    resolved: list[int] = []
    for item in raw_list:
        if isinstance(item, int):
            resolved.append(item)
        elif isinstance(item, str):
            item_clean = item.strip()
            if item_clean.isdigit():
                resolved.append(int(item_clean))
            else:
                match_id = name_to_id.get(item_clean.lower())
                if match_id is not None:
                    resolved.append(match_id)
                else:
                    logger.warning("Unknown player name or ID: '%s'", item_clean)
    return resolved


def run_strategy_solve_job(*, options: dict[str, object], target_gw: int = 1) -> None:
    try:
        processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
        solution_path = PROJECT_ROOT / "data" / "strategy_solution.json"

        solver_opts = load_settings()
        solver_opts.update(options)
        solver_opts["datasource"] = options.get("datasource") or get_default_model_name()

        horizon = clamp_planning_horizon(int(solver_opts.get("horizon", DEFAULT_PLANNING_HORIZON)))
        solver_opts["horizon"] = horizon

        for chip in ("use_wc", "use_bb", "use_fh", "use_tc"):
            if chip in solver_opts:
                val = solver_opts[chip]
                if isinstance(val, (int, str)):
                    try:
                        iv = int(val)
                        solver_opts[chip] = [iv] if iv > 0 else []
                    except (ValueError, TypeError):
                        solver_opts[chip] = []
                elif isinstance(val, list):
                    clean_list = []
                    for item in val:
                        try:
                            clean_list.append(int(item))
                        except (ValueError, TypeError):
                            pass
                    solver_opts[chip] = clean_list

        for key in ("locked", "banned"):
            if key in solver_opts:
                solver_opts[key] = _resolve_player_ids(solver_opts[key], processed_dir)

        plan = execute_transfer_plan(
            solver_opts,
            processed_dir=processed_dir,
            target_gw=target_gw,
            solution_path=solution_path,
        )
        _set_strategy_state(status="ok", error=None, detail="Strategy solve ready.", payload=plan)
    except FileNotFoundError:
        msg = (
            "Squad picks not found. Run Refresh with credentials, "
            "or check 'Preseason / Blank Squad' to solve without a loaded squad."
        )
        _set_strategy_state(status="error", error=msg, detail=msg, payload=None)
    except Exception as exc:
        logger.exception("Strategy Solve failed")
        _set_strategy_state(status="error", error=str(exc), detail=f"Solve failed: {exc}", payload=None)


def start_strategy_solve(*, options: dict[str, object], target_gw: int = 1) -> tuple[int, dict[str, object]]:
    with _job_lock:
        conflict = _active_job_conflict()
        if conflict:
            return conflict
        if transfer_plan_status()["status"] == "running":
            return 409, {
                "status": "error",
                "error": "Transfer Plan Solve is running. Wait for it to finish.",
                "detail": "Transfer Plan Solve is running. Wait for it to finish.",
            }
        with _strategy_lock:
            if _strategy_state["status"] == "running":
                return 202, dict(_strategy_state)
            _strategy_state["status"] = "running"
            _strategy_state["error"] = None
            _strategy_state["detail"] = "Starting Strategy Solve…"
            _strategy_state["payload"] = None
    threading.Thread(
        target=run_strategy_solve_job,
        kwargs={"options": options, "target_gw": target_gw},
        daemon=True,
    ).start()
    return 202, strategy_solve_status()


_solve_lock = threading.Lock()
_solve_state: dict[str, object] = {
    "status": "idle",
    "error": None,
    "detail": None,
    "payload": None,
}


def solve_status() -> dict[str, object]:
    with _solve_lock:
        return dict(_solve_state)


def _set_solve_state(
    *,
    status: str,
    error: str | None = None,
    detail: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    with _solve_lock:
        _solve_state["status"] = status
        _solve_state["error"] = error
        _solve_state["detail"] = detail
        if payload is not None or status != "running":
            _solve_state["payload"] = payload


RISK_PRESETS: dict[str, dict[str, Any]] = {
    "optimistic": {"decay_base": 1.00, "bench_weight": 0.03, "hit_cost": 4.0, "weekly_hit_limit": 1},
    "safe": {"decay_base": 0.75, "bench_weight": 0.20, "hit_cost": 4.5, "weekly_hit_limit": 0},
    "default": {"decay_base": 0.85, "bench_weight": 0.10, "hit_cost": 4.0, "weekly_hit_limit": 1},
    "high_risk": {"decay_base": 0.92, "bench_weight": 0.05, "hit_cost": 3.5, "weekly_hit_limit": 2},
}
DDP_PRESETS = RISK_PRESETS  # alias for backwards compatibility


def _build_branch_nodes_from_plan(
    plan: dict[str, Any],
    parent_node_id: str,
    target_gw: int,
    arm_label: str = "MILP Optimal",
) -> dict[str, Any]:
    weeks = plan.get("weeks") or []
    nodes: dict[str, Any] = {}
    prev_id = parent_node_id
    cum_xp = 0.0
    hit_cost = float(plan.get("meta", {}).get("hit_cost", 4.0) or 4.0)

    for i, w in enumerate(weeks):
        gw = int(w.get("gw", target_gw + i))
        node_id = f"node-gw{gw}-opt-{uuid.uuid4().hex[:5]}"
        xp = float(w.get("xp", 0.0) or 0.0)
        hits = int(w.get("hits", 0) or 0)
        cum_xp += xp
        net_xp = cum_xp - (hits * hit_cost)
        itb = round(float(w.get("itb", 0.0) or 0.0), 1)
        ft = int(w.get("ft", 1) or 1)
        chip = w.get("chip")

        buys = w.get("buy") or w.get("buys") or []
        sells = w.get("sell") or w.get("sells") or []
        transfers = []
        for b_item, s_item in zip(buys, sells, strict=False):
            b_id = b_item.get("id") if isinstance(b_item, dict) and "id" in b_item else (b_item.get("element") if isinstance(b_item, dict) else b_item)
            s_id = s_item.get("id") if isinstance(s_item, dict) and "id" in s_item else (s_item.get("element") if isinstance(s_item, dict) else s_item)
            b_name = b_item.get("name") if isinstance(b_item, dict) and "name" in b_item else (b_item.get("web_name", f"P#{b_id}") if isinstance(b_item, dict) else f"P#{b_id}")
            s_name = s_item.get("name") if isinstance(s_item, dict) and "name" in s_item else (s_item.get("web_name", f"P#{s_id}") if isinstance(s_item, dict) else f"P#{s_id}")
            transfers.append({
                "slot": 1,
                "playerOutId": s_id,
                "playerOutName": s_name,
                "playerInId": b_id,
                "playerInName": b_name,
                "purchasePrice": 5.0,
                "sellingPrice": 5.0,
            })

        lineup_items = w.get("lineup_ids") or w.get("lineup") or []
        bench_items = w.get("bench_ids") or w.get("bench") or []
        slots: dict[str, int] = {}
        idx = 1
        for item in lineup_items:
            pid = item.get("element") if isinstance(item, dict) else item
            try:
                slots[str(idx)] = int(pid)
                idx += 1
            except (ValueError, TypeError):
                pass
        for item in bench_items:
            pid = item.get("element") if isinstance(item, dict) else item
            try:
                slots[str(idx)] = int(pid)
                idx += 1
            except (ValueError, TypeError):
                pass

        captain_id = w.get("captain_id")
        vice_id = w.get("vice_id")
        captain_slot = 1
        vice_captain_slot = 2
        for s_str, pid in slots.items():
            if captain_id is not None and pid == captain_id:
                captain_slot = int(s_str)
            elif vice_id is not None and pid == vice_id:
                vice_captain_slot = int(s_str)

        node = {
            "id": node_id,
            "parentId": prev_id,
            "childIds": [],
            "gameweek": gw,
            "title": f"GW{gw} ({arm_label})",
            "lineup": {
                "slots": slots,
                "captainSlot": captain_slot,
                "viceCaptainSlot": vice_captain_slot,
                "benchOrder": [12, 13, 14, 15],
            },
            "transfers": transfers,
            "chip": chip,
            "evaluation": {
                "expectedPoints": round(xp, 1),
                "pointsVariance": 0.0,
                "cumulativePoints": round(cum_xp, 1),
                "hitsTaken": hits,
                "netPoints": round(net_xp, 1),
                "bankRemaining": itb,
                "freeTransfersNext": ft,
            },
            "solverRecommendation": {
                "lineup": {
                    "slots": dict(slots),
                    "captainSlot": captain_slot,
                    "viceCaptainSlot": vice_captain_slot,
                    "benchOrder": [12, 13, 14, 15],
                },
                "transfers": list(transfers),
                "chip": chip,
                "evaluation": {
                    "expectedPoints": round(xp, 1),
                    "pointsVariance": 0.0,
                    "cumulativePoints": round(cum_xp, 1),
                    "hitsTaken": hits,
                    "netPoints": round(net_xp, 1),
                    "bankRemaining": itb,
                    "freeTransfersNext": ft,
                },
            },
            "isCustom": False,
        }
        nodes[node_id] = node
        prev_id = node_id

    node_ids = list(nodes.keys())
    for j in range(len(node_ids) - 1):
        nodes[node_ids[j]]["childIds"] = [node_ids[j + 1]]

    return {
        "nodes": nodes,
        "rootChildId": node_ids[0] if node_ids else None,
        "rootChildIds": [node_ids[0]] if node_ids else [],
        "leafNodeId": node_ids[-1] if node_ids else None,
        "parentNodeId": parent_node_id,
    }


def run_branch_solve_job(*, options: dict[str, object], parent_node_id: str, target_gw: int = 1) -> None:
    try:
        processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
        solution_path = PROJECT_ROOT / "data" / "branch_solution.json"

        solver_opts = load_settings()
        solver_opts.update(options)

        preset_key = str(solver_opts.get("preset", "default")).lower().replace(" ", "_").replace("-", "_")
        preset_settings = DDP_PRESETS.get(preset_key, DDP_PRESETS["default"])
        for k, v in preset_settings.items():
            if k not in options:
                solver_opts[k] = v

        solver_opts["datasource"] = options.get("datasource") or get_default_model_name()

        horizon = clamp_planning_horizon(int(solver_opts.get("horizon", DEFAULT_PLANNING_HORIZON)))
        solver_opts["horizon"] = horizon

        for chip in ("use_wc", "use_bb", "use_fh", "use_tc"):
            if chip in solver_opts:
                val = solver_opts[chip]
                if isinstance(val, (int, str)):
                    try:
                        iv = int(val)
                        solver_opts[chip] = [iv] if iv > 0 else []
                    except (ValueError, TypeError):
                        solver_opts[chip] = []
                elif isinstance(val, list):
                    clean_list = []
                    for item in val:
                        try:
                            clean_list.append(int(item))
                        except (ValueError, TypeError):
                            pass
                    solver_opts[chip] = clean_list

        horizon_end = target_gw + horizon - 1
        for chip in ("use_wc", "use_bb", "use_fh", "use_tc"):
            if chip in solver_opts and isinstance(solver_opts[chip], list):
                solver_opts[chip] = [gw for gw in solver_opts[chip] if target_gw <= gw <= horizon_end]

        for key in ("locked", "banned"):
            if key in solver_opts:
                solver_opts[key] = _resolve_player_ids(solver_opts[key], processed_dir)

        if options.get("solve_3_arms"):
            from solver.scenarios import (
                ARM_CONSERVATIVE,
                ARM_NAMES,
                ARM_NO_HIT,
                ARM_OPTIMAL,
                apply_scenario_arm,
                find_protected_one_match_missed_starters,
                find_unowned_flagged_players,
            )
            players_path = processed_dir / "players.parquet"
            perf_path = processed_dir / "player_performances.parquet"
            players_df = pd.read_parquet(players_path) if players_path.exists() else pd.DataFrame()
            perf_df = pd.read_parquet(perf_path) if perf_path.exists() else pd.DataFrame()
            try:
                owned_ids, _c, _v, _meta = load_owned_picks(processed_dir)
                _itb, free_transfers = load_user_state(processed_dir)
                parent_data = options.get("parentNode") or options.get("parent_state")
                if isinstance(parent_data, dict):
                    parent_eval = parent_data.get("evaluation") or {}
                    if "freeTransfersNext" in parent_eval:
                        free_transfers = int(parent_eval["freeTransfersNext"])
                    parent_slots = (parent_data.get("lineup") or {}).get("slots")
                    if isinstance(parent_slots, dict) and len(parent_slots) == 15:
                        owned_ids = [int(v) for v in parent_slots.values() if v]
                unowned_flagged = find_unowned_flagged_players(players_df, owned_ids)
                protected_starters = find_protected_one_match_missed_starters(perf_df, owned_ids)
            except Exception:
                unowned_flagged = []
                protected_starters = []
                free_transfers = 1

            arms = (ARM_OPTIMAL, ARM_NO_HIT, ARM_CONSERVATIVE)
            merged_nodes: dict[str, Any] = {}
            root_child_ids: list[str] = []
            best_plan = None

            for i, arm in enumerate(arms):
                _set_solve_state(
                    status="running",
                    detail=f"Solving arm {i+1}/3: {ARM_NAMES[arm]}…",
                )
                arm_opts = dict(solver_opts)
                arm_opts = apply_scenario_arm(
                    arm_opts,
                    arm,
                    start_gw=target_gw,
                    free_transfer_bank=free_transfers,
                    banned_next_gw=unowned_flagged,
                    locked_next_gw=protected_starters,
                )
                arm_path = PROJECT_ROOT / "data" / f".branch_{arm}_{uuid.uuid4().hex[:6]}.json"
                try:
                    plan = execute_transfer_plan(
                        arm_opts,
                        processed_dir=processed_dir,
                        target_gw=target_gw,
                        solution_path=arm_path,
                    )
                finally:
                    if arm_path.exists():
                        arm_path.unlink()
                if best_plan is None:
                    best_plan = plan
                arm_branch = _build_branch_nodes_from_plan(
                    plan, parent_node_id, target_gw, arm_label=ARM_NAMES[arm]
                )
                merged_nodes.update(arm_branch["nodes"])
                if arm_branch["rootChildId"]:
                    root_child_ids.append(arm_branch["rootChildId"])
                _set_solve_state(
                    status="running",
                    detail=f"Solved {i+1}/3 arms ({ARM_NAMES[arm]})…",
                    payload={
                        "branch": {
                            "nodes": dict(merged_nodes),
                            "rootChildId": root_child_ids[0] if root_child_ids else None,
                            "rootChildIds": list(root_child_ids),
                            "parentNodeId": parent_node_id,
                        },
                        "plan": best_plan,
                    },
                )

            _set_solve_state(
                status="ok",
                error=None,
                detail="3-Arm branch solve complete.",
                payload={
                    "branch": {
                        "nodes": merged_nodes,
                        "rootChildId": root_child_ids[0] if root_child_ids else None,
                        "rootChildIds": root_child_ids,
                        "parentNodeId": parent_node_id,
                    },
                    "plan": best_plan,
                },
            )
            return

        plan = execute_transfer_plan(
            solver_opts,
            processed_dir=processed_dir,
            target_gw=target_gw,
            solution_path=solution_path,
        )
        branch_data = _build_branch_nodes_from_plan(plan, parent_node_id, target_gw)
        _set_solve_state(
            status="ok",
            error=None,
            detail="Branch solve complete.",
            payload={"branch": branch_data, "plan": plan},
        )
    except FileNotFoundError:
        msg = (
            "Squad picks not found. Run Refresh with credentials, "
            "or solve from Preseason."
        )
        _set_solve_state(status="error", error=msg, detail=msg, payload=None)
    except Exception as exc:
        logger.exception("Branch Solve failed")
        _set_solve_state(status="error", error=str(exc), detail=f"Solve failed: {exc}", payload=None)


def start_branch_solve(*, options: dict[str, object], parent_node_id: str, target_gw: int = 1) -> tuple[int, dict[str, object]]:
    with _job_lock:
        conflict = _active_job_conflict()
        if conflict:
            return conflict
        with _solve_lock:
            if _solve_state["status"] == "running":
                return 202, dict(_solve_state)
            _solve_state["status"] = "running"
            _solve_state["error"] = None
            _solve_state["detail"] = "Optimizing branch with Highs MILP…"
            _solve_state["payload"] = None
    threading.Thread(
        target=run_branch_solve_job,
        kwargs={"options": options, "parent_node_id": parent_node_id, "target_gw": target_gw},
        daemon=True,
    ).start()
    return 202, solve_status()


USER_PLANS_PATH = PROJECT_ROOT / "data" / "user_plans.json"


def _generate_default_user_plans() -> dict[str, object]:
    processed_dir = resolve_operational_processed_dir(PROJECT_ROOT)
    target_gw = resolve_default_target_gw(processed_dir)

    bank = 0.0
    free_transfers = 1
    state_path = processed_dir / "user_state.parquet"
    if state_path.exists():
        try:
            df_state = pd.read_parquet(state_path)
            if not df_state.empty:
                bank = float(df_state.iloc[0].get("bank", 0)) / 10.0
                free_transfers = int(df_state.iloc[0].get("free_transfers", 1))
        except Exception as exc:
            logger.warning("Could not read user_state: %s", exc)

    picks_path = processed_dir / "user_picks.parquet"
    slots: dict[str, int] = {}
    captain_slot = 1
    vice_captain_slot = 2
    bench_order = [12, 13, 14, 15]
    if picks_path.exists():
        try:
            df_picks = pd.read_parquet(picks_path)
            if not df_picks.empty:
                for _, row in df_picks.iterrows():
                    idx = int(row.get("lineup_index", 1))
                    slots[str(idx)] = int(row.get("player_id", 0))
                    if row.get("is_captain"):
                        captain_slot = idx
                    elif row.get("is_vice_captain"):
                        vice_captain_slot = idx
        except Exception as exc:
            logger.warning("Could not read user_picks: %s", exc)

    if len(slots) < 15:
        slots = {str(i): 100 + i for i in range(1, 16)}

    # Dynamically compute expected points from dashboard projections if available
    xp_lookup: dict[int, dict[int, float]] = {}
    json_path = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
    if json_path.exists():
        try:
            d_data = json.loads(json_path.read_text(encoding="utf-8"))
            for p in d_data.get("players", []):
                pid = p.get("id")
                if pid:
                    proj = p.get("projections", {})
                    m = {}
                    for k, v in proj.items():
                        if k.startswith("gw") and isinstance(v, dict):
                            try:
                                gw_num = int(k[2:])
                                m[gw_num] = float(v.get("total_xp", 0.0) or 0.0)
                            except (ValueError, TypeError):
                                pass
                    xp_lookup[int(pid)] = m
        except Exception as exc:
            logger.warning("Could not read dashboard_data.json for baseline projections: %s", exc)

    players_path = processed_dir / "players.parquet"
    pos_map: dict[int, str] = {}
    if players_path.exists():
        try:
            df_pl = pd.read_parquet(players_path)
            pos_code = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
            for _, r in df_pl.iterrows():
                pos_map[int(r["id"])] = pos_code.get(int(r["position_id"]), "MID")
        except Exception:
            pass

    def optimize_squad_for_gw(gw: int) -> tuple[dict[str, int], int, int, list[int], float]:
        """Selects highest legal xP starting XI, orders bench by xP, and sets captain/vice based on score."""
        all_pids = [slots[str(i)] for i in range(1, 16) if str(i) in slots]
        squad_items = []
        for pid in all_pids:
            pos = pos_map.get(pid, "MID")
            xp = xp_lookup.get(pid, {}).get(gw, 4.0)
            squad_items.append({"id": pid, "pos": pos, "xp": xp})

        gkps = sorted([p for p in squad_items if p["pos"] == "GKP"], key=lambda x: x["xp"], reverse=True)
        defs = sorted([p for p in squad_items if p["pos"] == "DEF"], key=lambda x: x["xp"], reverse=True)
        mids = sorted([p for p in squad_items if p["pos"] == "MID"], key=lambda x: x["xp"], reverse=True)
        fwds = sorted([p for p in squad_items if p["pos"] == "FWD"], key=lambda x: x["xp"], reverse=True)

        if not gkps or len(defs) < 3 or len(mids) < 2 or not fwds:
            tot = sum(xp_lookup.get(slots.get(str(s), 0), {}).get(gw, 4.0) for s in range(1, 12))
            cap = xp_lookup.get(slots.get(str(captain_slot), 0), {}).get(gw, 4.0)
            return dict(slots), captain_slot, vice_captain_slot, list(bench_order), round(tot + cap, 1)

        legal_shapes = [
            (3, 4, 3), (3, 5, 2), (4, 3, 3), (4, 4, 2), (4, 5, 1), (5, 2, 3), (5, 3, 2), (5, 4, 1)
        ]

        best_score = -1.0
        best_starters: list[dict[str, Any]] = []
        best_bench: list[dict[str, Any]] = []

        for req_defs, req_mids, req_fwds in legal_shapes:
            if len(defs) < req_defs or len(mids) < req_mids or len(fwds) < req_fwds:
                continue
            st_def = defs[:req_defs]
            st_mid = mids[:req_mids]
            st_fwd = fwds[:req_fwds]
            score = gkps[0]["xp"] + sum(p["xp"] for p in st_def) + sum(p["xp"] for p in st_mid) + sum(p["xp"] for p in st_fwd)
            if score > best_score:
                best_score = score
                bench_outfield = sorted(defs[req_defs:] + mids[req_mids:] + fwds[req_fwds:], key=lambda x: x["xp"], reverse=True)
                best_starters = [gkps[0]] + st_def + st_mid + st_fwd
                best_bench = ([gkps[1]] if len(gkps) > 1 else []) + bench_outfield

        gw_slots: dict[str, int] = {}
        for idx, p in enumerate(best_starters, start=1):
            gw_slots[str(idx)] = p["id"]
        for idx, p in enumerate(best_bench, start=12):
            gw_slots[str(idx)] = p["id"]

        sorted_starters = sorted(enumerate(best_starters, start=1), key=lambda x: x[1]["xp"], reverse=True)
        c_slot = sorted_starters[0][0] if len(sorted_starters) > 0 else 1
        v_slot = sorted_starters[1][0] if len(sorted_starters) > 1 else (2 if c_slot != 2 else 1)

        cap_bonus = sorted_starters[0][1]["xp"] if len(sorted_starters) > 0 else 4.0
        tot_xp = round(best_score + cap_bonus, 1)
        return gw_slots, c_slot, v_slot, [12, 13, 14, 15], tot_xp

    horizon = 5
    nodes: dict[str, Any] = {}
    cum_xp = 0.0
    root_id = "node-root"

    # Root Node: Current Pre-Deadline User Squad
    nodes[root_id] = {
        "id": root_id,
        "parentId": None,
        "childIds": [],
        "gameweek": max(1, target_gw - 1),
        "title": "Current Squad",
        "lineup": {
            "slots": slots,
            "captainSlot": captain_slot,
            "viceCaptainSlot": vice_captain_slot,
            "benchOrder": bench_order,
        },
        "transfers": [],
        "chip": None,
        "evaluation": {
            "expectedPoints": 0.0,
            "pointsVariance": 0.0,
            "cumulativePoints": 0.0,
            "hitsTaken": 0,
            "netPoints": 0.0,
            "bankRemaining": bank,
            "freeTransfersNext": free_transfers,
        },
        "solverRecommendation": None,
        "isCustom": False,
    }

    first_node_id = None
    scenarios_path = PROJECT_ROOT / "data" / "transfer_plan_scenarios.json"
    if scenarios_path.exists():
        try:
            sc_data = json.loads(scenarios_path.read_text(encoding="utf-8"))
            sc_list = sc_data.get("scenarios") or []
            if sc_list and isinstance(sc_list, list):
                optimal_plan = sc_list[0].get("plan")
                if optimal_plan and optimal_plan.get("weeks"):
                    branch = _build_branch_nodes_from_plan(
                        optimal_plan, root_id, target_gw, arm_label="MILP Optimal"
                    )
                    b_nodes = branch.get("nodes") or {}
                    if b_nodes:
                        nodes.update(b_nodes)
                        first_node_id = branch.get("rootChildId")
                        if first_node_id:
                            nodes[root_id]["childIds"] = [first_node_id]

                        # Extend chain if scenario has fewer weeks than horizon
                        leaf_id = first_node_id
                        while leaf_id and nodes.get(leaf_id, {}).get("childIds"):
                            leaf_id = nodes[leaf_id]["childIds"][0]
                        last_gw = nodes[leaf_id]["gameweek"] if leaf_id and leaf_id in nodes else target_gw - 1
                        curr_prev_id = leaf_id
                        for step_gw in range(last_gw + 1, target_gw + horizon):
                            ext_id = f"node-gw{step_gw}-1"
                            ext_slots, ext_c, ext_v, ext_b, ext_xp = optimize_squad_for_gw(step_gw)
                            prev_node = nodes[curr_prev_id]
                            prev_eval = prev_node.get("evaluation") or {}
                            ext_cum = round(float(prev_eval.get("cumulativePoints", 0.0)) + ext_xp, 1)
                            ext_ft = min(5, int(prev_eval.get("freeTransfersNext", 1)) + 1)
                            ext_node = {
                                "id": ext_id,
                                "parentId": curr_prev_id,
                                "childIds": [],
                                "gameweek": step_gw,
                                "title": f"GW{step_gw} (Roll)",
                                "lineup": {
                                    "slots": ext_slots,
                                    "captainSlot": ext_c,
                                    "viceCaptainSlot": ext_v,
                                    "benchOrder": ext_b,
                                },
                                "transfers": [],
                                "chip": None,
                                "evaluation": {
                                    "expectedPoints": ext_xp,
                                    "pointsVariance": 0.0,
                                    "cumulativePoints": ext_cum,
                                    "hitsTaken": 0,
                                    "netPoints": ext_cum,
                                    "bankRemaining": prev_eval.get("bankRemaining", bank),
                                    "freeTransfersNext": ext_ft,
                                },
                                "solverRecommendation": {
                                    "lineup": {
                                        "slots": dict(ext_slots),
                                        "captainSlot": ext_c,
                                        "viceCaptainSlot": ext_v,
                                        "benchOrder": list(ext_b),
                                    },
                                    "transfers": [],
                                    "chip": None,
                                    "evaluation": {
                                        "expectedPoints": ext_xp,
                                        "pointsVariance": 0.0,
                                        "cumulativePoints": ext_cum,
                                        "hitsTaken": 0,
                                        "netPoints": ext_cum,
                                        "bankRemaining": prev_eval.get("bankRemaining", bank),
                                        "freeTransfersNext": ext_ft,
                                    },
                                },
                                "isCustom": False,
                            }
                            nodes[ext_id] = ext_node
                            nodes[curr_prev_id]["childIds"] = [ext_id]
                            curr_prev_id = ext_id
        except Exception as exc:
            logger.warning("Could not populate default plan from scenarios: %s", exc)

    if len(nodes) <= 1:
        prev_id = root_id
        for step in range(horizon):
            gw = target_gw + step
            node_id = f"node-gw{gw}-1"
            if first_node_id is None:
                first_node_id = node_id

            gw_slots, c_slot, v_slot, b_order, xp = optimize_squad_for_gw(gw)
            cum_xp = round(cum_xp + xp, 1)
            ft_next = min(5, free_transfers + step + 1)

            node = {
                "id": node_id,
                "parentId": prev_id,
                "childIds": [],
                "gameweek": gw,
                "title": f"GW{gw} (Hold & Roll)" if step == 0 else f"GW{gw} (Roll)",
                "lineup": {
                    "slots": gw_slots,
                    "captainSlot": c_slot,
                    "viceCaptainSlot": v_slot,
                    "benchOrder": b_order,
                },
                "transfers": [],
                "chip": None,
                "evaluation": {
                    "expectedPoints": xp,
                    "pointsVariance": 0.0,
                    "cumulativePoints": cum_xp,
                    "hitsTaken": 0,
                    "netPoints": cum_xp,
                    "bankRemaining": bank,
                    "freeTransfersNext": ft_next,
                },
                "solverRecommendation": {
                    "lineup": {
                        "slots": dict(gw_slots),
                        "captainSlot": c_slot,
                        "viceCaptainSlot": v_slot,
                        "benchOrder": list(b_order),
                    },
                    "transfers": [],
                    "chip": None,
                    "evaluation": {
                        "expectedPoints": xp,
                        "pointsVariance": 0.0,
                        "cumulativePoints": cum_xp,
                        "hitsTaken": 0,
                        "netPoints": cum_xp,
                        "bankRemaining": bank,
                        "freeTransfersNext": ft_next,
                    },
                },
                "isCustom": False,
            }
            nodes[node_id] = node
            nodes[prev_id]["childIds"] = [node_id]
            prev_id = node_id

    default_plan = {
        "id": "plan-primary",
        "name": "Base Scenario",
        "startGameweek": target_gw,
        "horizonGameweeks": horizon,
        "initialBank": bank,
        "initialFreeTransfers": free_transfers,
        "availableChips": {
            "wildcard1": True,
            "wildcard2": True,
            "freeHit": True,
            "tripleCaptain": True,
            "benchBoost": True,
        },
        "rootNodeId": root_id,
        "activeNodeId": first_node_id or root_id,
        "nodes": nodes,
    }

    return {"plans": [default_plan], "activePlanId": "plan-primary"}


def get_user_plans() -> dict[str, object]:
    if USER_PLANS_PATH.exists():
        try:
            data = json.loads(USER_PLANS_PATH.read_text(encoding="utf-8"))
            modified = False
            for plan in data.get("plans", []):
                for nid, node in plan.get("nodes", {}).items():
                    if not node.get("solverRecommendation") and nid != plan.get("rootNodeId"):
                        node["solverRecommendation"] = {
                            "lineup": dict(node.get("lineup") or {}),
                            "transfers": list(node.get("transfers") or []),
                            "chip": node.get("chip"),
                            "evaluation": dict(node.get("evaluation") or {}),
                        }
                        modified = True
            if modified:
                USER_PLANS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return data
        except Exception as exc:
            logger.warning("Could not read user_plans.json: %s", exc)
    default_payload = _generate_default_user_plans()
    try:
        USER_PLANS_PATH.write_text(json.dumps(default_payload, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not save initial user_plans.json: %s", exc)
    return default_payload


def save_user_plans(payload: dict[str, object]) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {"error": "Invalid payload format"}
    try:
        USER_PLANS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Failed to write user_plans.json: %s", exc)
        return {"error": str(exc)}


def handle_dashboard_api(
    method: str,
    path: str,
    body: dict[str, object] | None = None,
    query_string: str = "",
) -> tuple[int, dict[str, object]]:
    if path == "/api/champion" and method == "GET":
        return 200, {"champion": get_default_model_name()}
    if path == "/api/user-plans":
        if method == "GET":
            return 200, get_user_plans()
        if method == "POST":
            return 200, save_user_plans(body or {})
    if path == "/api/solve":
        if method == "GET":
            return 200, solve_status()
        if method == "POST":
            opts = body or {}
            target_gw = int(opts.get("target_gw") or 6)
            parent_id = str(opts.get("parentNodeId") or "node-root")
            return start_branch_solve(options=opts, parent_node_id=parent_id, target_gw=target_gw)
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
    if path == "/api/transfer-plan":
        if method == "GET":
            state = transfer_plan_status()
            if state.get("payload") is None:
                loaded = _loaded_scenarios()
                if loaded is not None:
                    state = {**state, "payload": loaded}
            return 200, state
        if method == "POST":
            target_gw, horizon, booked, enabled, force_keep = _transfer_plan_args(body)
            return start_transfer_plan(
                target_gw=target_gw,
                horizon=horizon,
                booked_chips=booked,
                enabled_chips=enabled,
                force_keep=force_keep,
            )
    if path == "/api/strategy-solve":
        if method == "GET":
            return 200, strategy_solve_status()
        if method == "POST":
            opts = body or {}
            target_gw = int(opts.get("target_gw") or 1)
            return start_strategy_solve(options=opts, target_gw=target_gw)
    if path == "/api/research/topics" and method == "GET":
        return 200, {"topics": get_research_topics()}
    if path == "/api/research/topic" and method == "GET":
        query = parse_qs(query_string)
        slug = query.get("slug", [""])[0]
        return 200, get_research_topic_detail(slug)
    if path == "/api/methodology" and method == "GET":
        return 200, get_model_methodology()
    return 404, {"error": "Not found"}


class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serves dashboard/ without caching; Dashboard Refresh on /api/refresh."""

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            dist_index = PROJECT_ROOT / "dashboard" / "dist" / "index.html"
            directory = str(PROJECT_ROOT / "dashboard" / "dist") if dist_index.exists() else str(PROJECT_ROOT / "dashboard")
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
        query_string = self.path.split("?", 1)[1] if "?" in self.path else ""
        if api_path.startswith("/api/"):
            status, payload = handle_dashboard_api("GET", api_path, None, query_string=query_string)
            if status == 404:
                self.send_error(404, "Not found")
                return
            self._send_json(status, payload)
            return
        if api_path == "/dashboard_data.json":
            json_path = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
            if json_path.exists():
                data = json_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
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
    from commands.streamlit_planner import launch

    raise SystemExit(launch([f"--server.port={port}", f"--server.headless={str(not open_browser).lower()}"]))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve Explorer and Transfer Plan Surface. Open projects the Primary Model from processed data when JSON is stale. Refresh in the page ingests FPL and re-projects the selected Primary Model. Solve Dream Team paints an Explorer overlay. Solve scenarios ranks Optimal / No Hit on the Transfer Plan tab. Refresh, Dream Team, and Transfer Plan Solve cannot run together."
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
