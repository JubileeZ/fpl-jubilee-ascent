"""Injury triage, return date parsing, Broad Pool Shield, and override synthesis."""

from __future__ import annotations

from datetime import date
import logging
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import pandas as pd

logger = logging.getLogger(__name__)

MONTH_MAP: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

RETURN_DATE_REGEX = re.compile(
    r"(?:expected back|suspended until)\s+(\d{1,2})\s+([a-zA-Z]{3})",
    re.IGNORECASE,
)

POS_MAP: dict[int, str] = {1: "G", 2: "D", 3: "M", 4: "F"}


def resolve_gw_reference_date(processed_dir: Path, target_gw: int) -> date:
    """Resolve point-in-time reference date from target gameweek deadline."""
    gw_path = processed_dir / "gameweeks.parquet"
    if gw_path.exists():
        df_gw = pd.read_parquet(gw_path)
        row = df_gw[df_gw["id"] == target_gw]
        if not row.empty and "deadline_time" in row.columns:
            d_str = str(row.iloc[0]["deadline_time"])
            parsed = pd.to_datetime(d_str, utc=True, errors="coerce")
            if pd.notna(parsed):
                return parsed.date()
    return date.today()


def get_flagged_players(df_players: pd.DataFrame) -> pd.DataFrame:
    """Return filtered DataFrame of flagged or doubtful Premier League assets."""
    flagged = df_players[
        (df_players["status"] != "a") | (df_players["chance_of_playing_next_round"] < 100)
    ].copy()
    return flagged


def parse_fpl_return_date(news: str, reference_date: date | None = None) -> date | None:
    """Parse return date from FPL news string (e.g. 'Expected back 31 Oct' or 'Suspended until 7 Nov')."""
    if not news or not isinstance(news, str):
        return None

    match = RETURN_DATE_REGEX.search(news)
    if not match:
        return None

    day = int(match.group(1))
    mon_str = match.group(2).lower()
    month = MONTH_MAP.get(mon_str)
    if not month:
        return None

    ref = reference_date or date.today()
    # Next calendar year rollover (e.g. January return when reference is October)
    year = ref.year + 1 if month < ref.month else ref.year

    try:
        return date(year, month, day)
    except ValueError:
        return None


def compute_healthy_baseline_xmins(
    players_df: pd.DataFrame,
    performances_df: pd.DataFrame | None = None,
) -> dict[int, float]:
    """Estimate healthy starter baseline minutes to prevent multi-week injury depression."""
    baseline: dict[int, float] = {}

    active_means: dict[int, float] = {}
    if performances_df is not None and not performances_df.empty and "minutes" in performances_df.columns:
        active_perfs = performances_df[performances_df["minutes"] > 0]
        if not active_perfs.empty:
            active_means = active_perfs.groupby("player_id")["minutes"].mean().to_dict()

    for _, row in players_df.iterrows():
        pid = int(row["id"])
        pos = int(row.get("position_id", 3))
        cost = float(row.get("now_cost", 50)) / 10.0

        if pid in active_means and active_means[pid] >= 55.0:
            mins = float(active_means[pid])
        else:
            if pos == 1:
                mins = 90.0 if cost >= 4.5 else 45.0
            elif pos == 2:
                mins = 85.0 if cost >= 5.5 else (75.0 if cost >= 4.5 else 60.0)
            elif pos == 3:
                mins = 82.0 if cost >= 7.5 else (74.0 if cost >= 5.5 else 60.0)
            else:
                mins = 82.0 if cost >= 7.5 else (74.0 if cost >= 5.5 else 60.0)

        baseline[pid] = round(min(90.0, max(20.0, mins)), 1)

    return baseline


def _build_broad_pool_shield_layers(
    processed_dir: Path,
    target_gw: int,
    horizon: int,
    reference_date: date | None = None,
    *,
    native_mins_map: Mapping[tuple[int, int], float] | None = None,
) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], float], dict[tuple[int, int], float]]:
    """
    Construct Soft Empirical Broad Pool Shield split into:
    - hard_guard: pre-return 0.0 zeros, status='u' horizon 0.0, t=0 loan/hard-DNP, injury 20m -> 65m ramps
    - soft_curve: S-1 calibrated recovery curves (unknown-return injuries, non-loan 'n', doubtfuls < 100%)
    - post_return_fallback: healthy starter baseline fallback once recovered or ban expires
    """
    players_path = processed_dir / "players.parquet"
    fixtures_path = processed_dir / "fixtures.parquet"
    if not players_path.exists() or not fixtures_path.exists():
        return {}, {}, {}

    from features.internal_xmins import build_soft_shield_layers

    df_players = pd.read_parquet(players_path)
    df_fixtures = pd.read_parquet(fixtures_path)
    perfs_path = processed_dir / "player_performances.parquet"
    df_perfs = pd.read_parquet(perfs_path) if perfs_path.exists() else pd.DataFrame()
    ref = reference_date or resolve_gw_reference_date(processed_dir, target_gw)
    return build_soft_shield_layers(
        df_players,
        df_fixtures,
        df_perfs,
        target_gw,
        horizon,
        native_mins_map=native_mins_map,
        reference_date=ref,
    )


def build_broad_pool_shield(
    processed_dir: Path,
    target_gw: int,
    horizon: int,
    reference_date: date | None = None,
    *,
    native_mins_map: Mapping[tuple[int, int], float] | None = None,
    filter_depressed_only: bool = False,
) -> dict[tuple[int, int], float]:
    """
    Construct Soft Empirical Broad Pool Shield across all flagged players.

    Suspensions (`status == 's'`) enforce 0.0 xMins prior to `return_gw` and restore full
    fitness immediately upon return; injuries (`status == 'i'`) apply a 20m -> 65m ramp when a
    return date is known or empirical S-1 recovery curves when unknown; doubtfuls apply S-1
    calibrated curves.
    """
    hard_guard, soft_curve, post_return_fallback = _build_broad_pool_shield_layers(
        processed_dir, target_gw, horizon, reference_date=reference_date, native_mins_map=native_mins_map
    )
    if filter_depressed_only and native_mins_map is not None and post_return_fallback:
        from features.internal_xmins import filter_depressed_post_return

        df_players = pd.read_parquet(processed_dir / "players.parquet")
        df_fixtures = pd.read_parquet(processed_dir / "fixtures.parquet")
        post_return_fallback = filter_depressed_post_return(
            df_players,
            df_fixtures,
            list(range(int(target_gw), int(target_gw) + max(1, int(horizon)))),
            post_return_fallback,
            native_mins_map,
        )
    return {**post_return_fallback, **soft_curve, **hard_guard}


def audit_squad_minutes(
    processed_dir: Path,
    player_ids: Iterable[int],
    target_gw: int,
    horizon: int,
    *,
    base_csv_path: Path | str | None = None,
    override_csv_path: Path | str | None = None,
    recent_mins_threshold: float = 60.0,
    layer2_gap_threshold: float = 25.0,
    layer2_cliff_threshold: float = 25.0,
) -> list[dict[str, Any]]:
    """
    Audit unflagged squad Players for rotation/drop risk using three triggers:
    1. recent_non_start_or_sub60: last played GW < 60m or non-start
    2. recent_vs_external_gap: Layer 2 target-GW xMins exceeds recent mins by > 25m
    3. external_xmins_cliff: Layer 2 horizon xMins drops >= 25m below 65m
    """
    pids = [int(pid) for pid in player_ids]
    players_path = processed_dir / "players.parquet"
    if not pids or not players_path.exists():
        return []

    df_players = pd.read_parquet(players_path)
    df_players = df_players[df_players["id"].isin(pids)].copy()
    if df_players.empty:
        return []

    chance_series = pd.to_numeric(df_players.get("chance_of_playing_next_round"), errors="coerce")
    unflagged_mask = (df_players["status"].astype(str) == "a") & (chance_series.isna() | (chance_series >= 100.0))
    df_unflagged = df_players[unflagged_mask].copy()
    if df_unflagged.empty:
        return []

    perf_stats: dict[int, dict[str, Any]] = {}
    perfs_path = processed_dir / "player_performances.parquet"
    if perfs_path.exists():
        df_perfs = pd.read_parquet(perfs_path)
        df_perfs = df_perfs[(df_perfs["player_id"].isin(df_unflagged["id"])) & (df_perfs["gameweek_id"] < int(target_gw))]
        for pid, grp in df_perfs.groupby("player_id"):
            grp_sorted = grp.sort_values("gameweek_id")
            last_row = grp_sorted.iloc[-1]
            last_3 = grp_sorted.tail(3)
            last_mins = float(last_row.get("minutes", 0.0) or 0.0)
            last_starts = int(last_row["starts"]) if "starts" in grp_sorted.columns and pd.notna(last_row.get("starts")) else None
            avg_3 = float(pd.to_numeric(last_3["minutes"], errors="coerce").fillna(0.0).mean())
            perf_stats[int(pid)] = {
                "last_gw": int(last_row["gameweek_id"]),
                "last_gw_minutes": round(last_mins, 1),
                "last_gw_starts": last_starts,
                "last_3gw_avg_minutes": round(avg_3, 1),
            }

    planning_gws = list(range(int(target_gw), int(target_gw) + max(1, int(horizon))))
    ext_map: dict[tuple[int, int], float] = {}
    csv_source = override_csv_path if override_csv_path and Path(override_csv_path).exists() else base_csv_path
    if csv_source is not None and Path(csv_source).exists():
        from features.builder import load_xmins_override
        ext_map = load_xmins_override(csv_source, planning_gws)

    risks: list[dict[str, Any]] = []
    for _, row in df_unflagged.iterrows():
        pid = int(row["id"])
        pstat = perf_stats.get(pid, {})
        last_gw = pstat.get("last_gw")
        last_mins = pstat.get("last_gw_minutes")
        last_starts = pstat.get("last_gw_starts")
        avg_3 = pstat.get("last_3gw_avg_minutes")

        ext_series = [ext_map[(pid, gw)] for gw in planning_gws if (pid, gw) in ext_map]
        ext_target = ext_map.get((pid, int(target_gw)))
        min_ext = min(ext_series) if ext_series else None
        max_ext = max(ext_series) if ext_series else None

        triggers: list[str] = []
        details: list[str] = []

        if last_mins is not None and (last_mins < recent_mins_threshold or last_starts == 0):
            triggers.append("recent_non_start_or_sub60")
            details.append(f"GW{last_gw}: {last_mins:.0f}m" + (" (non-start)" if last_starts == 0 else ""))

        if ext_target is not None and last_mins is not None:
            gap_last = ext_target - last_mins
            gap_3 = (ext_target - avg_3) if avg_3 is not None else 0.0
            if gap_last > layer2_gap_threshold or gap_3 > layer2_gap_threshold:
                triggers.append("recent_vs_external_gap")
                details.append(f"GW{target_gw} ext {ext_target:.1f}m vs last {last_mins:.0f}m / 3gw {avg_3:.1f}m")

        if min_ext is not None and max_ext is not None and (max_ext - min_ext) >= layer2_cliff_threshold and min_ext < 65.0:
            triggers.append("external_xmins_cliff")
            details.append(f"ext cliff {max_ext:.1f}m -> {min_ext:.1f}m")

        if triggers:
            risks.append({
                "id": pid,
                "web_name": str(row.get("web_name", "")),
                "club_id": int(row.get("club_id", 0)),
                "position_id": int(row.get("position_id", 3)),
                "price": float(row.get("now_cost", 0)) / 10.0,
                "status": str(row.get("status", "a")),
                "last_gw": last_gw,
                "last_gw_minutes": last_mins,
                "last_3gw_avg_minutes": avg_3,
                "target_gw_external_xmins": round(ext_target, 1) if ext_target is not None else None,
                "min_horizon_external_xmins": round(min_ext, 1) if min_ext is not None else None,
                "triggers": triggers,
                "trigger_details": "; ".join(details),
            })

    return risks


def select_scouting_targets(
    processed_dir: Path,
    user_squad_ids: set[int] | None = None,
    top_per_tier: int = 2,
    reference_date: date | None = None,
    target_gw: int | None = None,
    horizon: int = 10,
    base_csv_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Selects flagged User Squad Players, unflagged User Squad rotation/minutes risks,
    and top non-squad transfer candidates segmented by Position x Price Bracket.
    """
    players_path = processed_dir / "players.parquet"
    if not players_path.exists():
        return {"squad_flagged": [], "squad_rotation_risk": [], "market_flagged_by_tier": {}}

    df_players = pd.read_parquet(players_path)
    flagged = get_flagged_players(df_players).copy()
    flagged = flagged[flagged["status"] != "u"]
    flagged["price"] = flagged["now_cost"] / 10.0
    flagged["selected_by_percent"] = pd.to_numeric(flagged["selected_by_percent"], errors="coerce").fillna(0.0)

    squad_ids = user_squad_ids or set()
    ref = reference_date or date.today()

    def format_player(r: pd.Series) -> dict[str, Any]:
        raw_ch = r.get("chance_of_playing_next_round")
        return {
            "id": int(r["id"]),
            "web_name": str(r["web_name"]),
            "club_id": int(r["club_id"]),
            "position_id": int(r["position_id"]),
            "price": float(r["price"]),
            "selected_by_percent": float(r["selected_by_percent"]),
            "status": str(r.get("status", "")),
            "chance": 100.0 if raw_ch is None or pd.isna(raw_ch) else float(raw_ch),
            "news": str(r.get("news") or ""),
            "parsed_return_date": parse_fpl_return_date(str(r.get("news") or ""), ref),
        }

    squad_flagged = [
        format_player(r) for _, r in flagged[flagged["id"].isin(squad_ids)].iterrows()
    ]

    resolved_gw = target_gw
    if resolved_gw is None and (processed_dir / "gameweeks.parquet").exists():
        from solver.planning import resolve_default_target_gw
        resolved_gw = resolve_default_target_gw(processed_dir)

    squad_rotation_risk: list[dict[str, Any]] = []
    if squad_ids and resolved_gw is not None:
        squad_rotation_risk = audit_squad_minutes(
            processed_dir,
            squad_ids,
            resolved_gw,
            horizon,
            base_csv_path=base_csv_path,
        )

    market_flagged = flagged[~flagged["id"].isin(squad_ids)].copy()

    tier_defs = {
        "GKP_budget": (1, 0.0, 4.5),
        "GKP_premium": (1, 4.6, 15.0),
        "DEF_budget": (2, 0.0, 4.5),
        "DEF_mid": (2, 4.6, 5.5),
        "DEF_premium": (2, 5.6, 15.0),
        "MID_budget": (3, 0.0, 5.5),
        "MID_mid": (3, 5.6, 7.5),
        "MID_premium": (3, 7.6, 15.0),
        "FWD_budget": (4, 0.0, 6.0),
        "FWD_mid": (4, 6.1, 8.0),
        "FWD_premium": (4, 8.1, 15.0),
    }

    market_tiers: dict[str, list[dict[str, Any]]] = {}
    for tier_name, (pos_id, min_p, max_p) in tier_defs.items():
        sub = market_flagged[
            (market_flagged["position_id"] == pos_id)
            & (market_flagged["price"] >= min_p)
            & (market_flagged["price"] <= max_p)
        ].sort_values("selected_by_percent", ascending=False).head(top_per_tier)

        if not sub.empty:
            market_tiers[tier_name] = [format_player(r) for _, r in sub.iterrows()]

    return {
        "squad_flagged": squad_flagged,
        "squad_rotation_risk": squad_rotation_risk,
        "market_flagged_by_tier": market_tiers,
    }


def synthesize_xmins_override(
    processed_dir: Path,
    target_gw: int,
    horizon: int,
    targeted_overrides: Mapping[tuple[int, int], float] | None = None,
    base_csv_path: Path | str | None = None,
    output_path: Path | str | None = None,
    include_broad_pool_shield: bool = True,
    reference_date: date | None = None,
    native_mins_map: Mapping[tuple[int, int], float] | None = None,
    include_internal_gkp_baseline: bool = True,
) -> Path:
    """
    Synthesize consolidated 3-tier xMins override CSV.

    Precedence per (player_id, gw):
    1. Layer 3a (Top Guard): Targeted Overrides (--set / --set-gw curves & web intel)
    2. Layer 3b (Top Guard): Soft Empirical Shield hard guards (pre-return 0.0m, status='u', 20m/65m ramp)
    3. Layer 2 (Middle, when --base-csv given): External CSV (wins post-return steady-state when > 0.0m)
    4. Layer 2 (Internal, when --base-csv omitted): Sparse M1 GKP allocation + Soft Empirical recovery curves
    5. Layer 3b (Fallback): Healthy baseline fallback when Layer 2 absent or depressed post-return
    6. Layer 1 (Base Foundation): Blank cells stay NaN -> Native In-House Champion (outfielders).
    """
    players_path = processed_dir / "players.parquet"
    if not players_path.exists():
        raise FileNotFoundError(f"Missing {players_path}")
    df_players = pd.read_parquet(players_path)

    planning_gws = list(range(target_gw, target_gw + horizon))

    out_df = pd.DataFrame({
        "ID": df_players["id"].astype(int),
        "Name": df_players["web_name"],
        "Pos": df_players["position_id"].map(POS_MAP).fillna("M"),
    })

    base_map: dict[tuple[int, int], float] = {}
    if base_csv_path is not None:
        from features.builder import load_xmins_override
        base_map = load_xmins_override(base_csv_path, planning_gws)

    hard_guard: dict[tuple[int, int], float] = {}
    soft_curve: dict[tuple[int, int], float] = {}
    post_return_fallback: dict[tuple[int, int], float] = {}
    gkp_baseline: dict[tuple[int, int], float] = {}

    if include_broad_pool_shield or (base_csv_path is None and include_internal_gkp_baseline):
        from features.internal_xmins import build_sparse_gkp_baseline, filter_depressed_post_return

        ref = reference_date or resolve_gw_reference_date(processed_dir, target_gw)
        if include_broad_pool_shield:
            hard_guard, soft_curve, post_return_fallback = _build_broad_pool_shield_layers(
                processed_dir, target_gw, horizon, reference_date=ref, native_mins_map=native_mins_map
            )
        fixtures_path = processed_dir / "fixtures.parquet"
        perfs_path = processed_dir / "player_performances.parquet"
        df_fixtures = pd.read_parquet(fixtures_path) if fixtures_path.exists() else pd.DataFrame()

        if base_csv_path is None and native_mins_map is not None and post_return_fallback:
            post_return_fallback = filter_depressed_post_return(
                df_players, df_fixtures, planning_gws, post_return_fallback, native_mins_map
            )

        if base_csv_path is None and include_internal_gkp_baseline and not df_fixtures.empty:
            df_perfs = pd.read_parquet(perfs_path) if perfs_path.exists() else pd.DataFrame()
            soft_all = {**post_return_fallback, **soft_curve, **hard_guard}
            gkp_baseline = build_sparse_gkp_baseline(
                df_players, df_fixtures, df_perfs, target_gw, horizon, soft_overrides=soft_all
            )

    target_map = dict(targeted_overrides or {})

    for gw in planning_gws:
        col_name = f"{gw}_xMins"
        vals: list[Any] = []
        for pid in out_df["ID"]:
            key = (int(pid), int(gw))
            if key in target_map:
                vals.append(float(target_map[key]))
            elif base_csv_path is None and key in gkp_baseline:
                vals.append(float(gkp_baseline[key]))
            elif key in hard_guard:
                vals.append(float(hard_guard[key]))
            elif base_csv_path is not None:
                if key in base_map and (key not in post_return_fallback or float(base_map[key]) > 0.0):
                    vals.append(float(base_map[key]))
                elif key in post_return_fallback:
                    vals.append(float(post_return_fallback[key]))
                else:
                    vals.append("")
            elif key in soft_curve:
                vals.append(float(soft_curve[key]))
            elif key in post_return_fallback:
                vals.append(float(post_return_fallback[key]))
            else:
                vals.append("")
        out_df[col_name] = vals

    has_any = out_df[[f"{gw}_xMins" for gw in planning_gws]].apply(lambda row: any(v != "" for v in row), axis=1)
    filtered_df = out_df[has_any].copy()

    dest = Path(output_path) if output_path else processed_dir.parent / "planner" / "xmins_override.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    filtered_df.to_csv(dest, index=False)
    logger.info("Saved %d player overrides to %s", len(filtered_df), dest)
    return dest


def _player_audit_info(
    pid: int,
    df_players: pd.DataFrame,
    override_df: pd.DataFrame,
    role: str,
) -> dict[str, Any]:
    if pid not in df_players.index:
        return {"id": pid, "web_name": f"Player {pid}", "role": role, "gameweeks": []}
    row = df_players.loc[pid]
    mins_trajectory: dict[str, float] = {}
    if not override_df.empty and pid in override_df.index:
        o_row = override_df.loc[pid]
        for col in o_row.index:
            if col.endswith("_xMins"):
                val = o_row[col]
                if pd.notna(val) and val != "":
                    try:
                        mins_trajectory[col.replace("_xMins", "")] = float(val)
                    except (ValueError, TypeError):
                        pass

    chance = row.get("chance_of_playing_next_round")
    return {
        "id": pid,
        "web_name": str(row.get("web_name", "")),
        "position": POS_MAP.get(int(row.get("position_id", 3)), "MID"),
        "price": float(row.get("now_cost", 0)) / 10.0,
        "status": str(row.get("status", "a")),
        "chance": float(chance) if pd.notna(chance) else 100.0,
        "news": str(row.get("news", "")) if pd.notna(row.get("news")) else "",
        "is_flagged": str(row.get("status", "a")) != "a" or (pd.notna(chance) and float(chance) < 100),
        "gameweeks": [],
        "override_xmins": mins_trajectory,
    }


def audit_solution_players(
    processed_dir: Path,
    solution_path: Path | str,
    override_csv_path: Path | str | None = None,
) -> dict[str, Any]:
    """Extract solution-involved Players (buys, sells, FH picks, flagged holds, and held rotation risks)."""
    import json
    sol_file = Path(solution_path)
    if not sol_file.exists():
        raise FileNotFoundError(f"Solution file not found: {sol_file}")

    with open(sol_file, encoding="utf-8") as f:
        sol_data = json.load(f)

    players_path = processed_dir / "players.parquet"
    if not players_path.exists():
        raise FileNotFoundError(f"Missing {players_path}")
    df_players = pd.read_parquet(players_path).set_index("id")

    override_df = pd.DataFrame()
    if override_csv_path and Path(override_csv_path).exists():
        override_df = pd.read_csv(override_csv_path).set_index("ID")

    buys_dict: dict[int, dict[str, Any]] = {}
    sells_dict: dict[int, dict[str, Any]] = {}
    held_flagged_dict: dict[int, dict[str, Any]] = {}
    fh_picks_dict: dict[int, dict[str, Any]] = {}
    held_perm_gws: dict[int, list[int]] = {}

    weeks = sol_data.get("weeks", [])
    permanent_squad_ids: set[int] = set()
    picks_path = processed_dir / "user_picks.parquet"
    if picks_path.exists():
        try:
            df_picks = pd.read_parquet(picks_path)
            permanent_squad_ids = {int(pid) for pid in df_picks["player_id"]}
        except Exception:
            permanent_squad_ids = set()

    for w in weeks:
        gw = int(w.get("gw", 0))
        chip = str(w.get("chip") or "").upper()
        for b in w.get("buy", []):
            pid = int(b.get("id"))
            if pid not in buys_dict:
                buys_dict[pid] = _player_audit_info(pid, df_players, override_df, "buy")
            buys_dict[pid]["gameweeks"].append(gw)

        for s in w.get("sell", []):
            pid = int(s.get("id"))
            if pid not in sells_dict:
                sells_dict[pid] = _player_audit_info(pid, df_players, override_df, "sell")
            sells_dict[pid]["gameweeks"].append(gw)

        squad_ids = [int(pid_raw) for pid_raw in w.get("squad_ids", [])]
        if chip == "FH":
            lineup_set = {int(pid_raw) for pid_raw in w.get("lineup_ids", [])}
            for pid in squad_ids:
                if pid not in permanent_squad_ids:
                    if pid not in fh_picks_dict:
                        info = _player_audit_info(pid, df_players, override_df, "free_hit")
                        info["fh_role"] = "starter" if pid in lineup_set else "bench"
                        fh_picks_dict[pid] = info
                    if gw not in fh_picks_dict[pid]["gameweeks"]:
                        fh_picks_dict[pid]["gameweeks"].append(gw)
        else:
            permanent_squad_ids = set(squad_ids)
            for pid in squad_ids:
                held_perm_gws.setdefault(pid, [])
                if gw not in held_perm_gws[pid]:
                    held_perm_gws[pid].append(gw)

        for pid in squad_ids:
            if pid in df_players.index:
                p_row = df_players.loc[pid]
                chance_val = p_row.get("chance_of_playing_next_round", 100)
                if str(p_row.get("status", "a")) != "a" or (pd.notna(chance_val) and float(chance_val) < 100):
                    if pid not in held_flagged_dict:
                        held_flagged_dict[pid] = _player_audit_info(pid, df_players, override_df, "held_flagged")
                    if gw not in held_flagged_dict[pid]["gameweeks"]:
                        held_flagged_dict[pid]["gameweeks"].append(gw)

    held_rotation_risk: list[dict[str, Any]] = []
    if held_perm_gws and weeks:
        meta = sol_data.get("meta") or {}
        audit_target_gw = int(meta.get("next_gw") or min(int(w.get("gw", 1)) for w in weeks))
        audit_horizon = int(meta.get("horizon") or len(weeks))
        candidate_pids = [pid for pid in held_perm_gws if pid not in held_flagged_dict]
        risk_entries = audit_squad_minutes(
            processed_dir,
            candidate_pids,
            audit_target_gw,
            audit_horizon,
            override_csv_path=override_csv_path,
        )
        for entry in risk_entries:
            pid = int(entry["id"])
            info = _player_audit_info(pid, df_players, override_df, "held_rotation_risk")
            info.update(entry)
            info["gameweeks"] = held_perm_gws.get(pid, [])
            held_rotation_risk.append(info)

    return {
        "transfers_in": list(buys_dict.values()),
        "transfers_out": list(sells_dict.values()),
        "free_hit_picks": list(fh_picks_dict.values()),
        "held_flagged": list(held_flagged_dict.values()),
        "held_rotation_risk": held_rotation_risk,
    }
