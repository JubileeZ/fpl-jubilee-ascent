"""Injury triage, return date parsing, Broad Pool Shield, and override synthesis."""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping

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


def build_broad_pool_shield(
    processed_dir: Path,
    target_gw: int,
    horizon: int,
    reference_date: date | None = None,
) -> dict[tuple[int, int], float]:
    """
    Construct Tier A Broad Pool Shield.
    
    Parses all flagged players in the pool and enforces 0.0 xMins for gameweeks prior
    to their club fixture return date, populating a non-linear recovery ramp upon return.
    """
    players_path = processed_dir / "players.parquet"
    fixtures_path = processed_dir / "fixtures.parquet"
    if not players_path.exists() or not fixtures_path.exists():
        return {}

    df_players = pd.read_parquet(players_path)
    df_fixtures = pd.read_parquet(fixtures_path)
    perfs_path = processed_dir / "player_performances.parquet"
    df_perfs = pd.read_parquet(perfs_path) if perfs_path.exists() else None

    healthy_baselines = compute_healthy_baseline_xmins(df_players, df_perfs)
    flagged = get_flagged_players(df_players)

    planning_gws = list(range(target_gw, target_gw + horizon))
    fixture_sub = df_fixtures[df_fixtures["gameweek_id"].isin(planning_gws)].copy()
    fixture_sub["kickoff_date"] = pd.to_datetime(fixture_sub["kickoff_time"], utc=True, errors="coerce").dt.date

    club_gw_dates: dict[tuple[int, int], date] = {}
    for _, fix_row in fixture_sub.iterrows():
        gw = int(fix_row["gameweek_id"])
        k_date = fix_row["kickoff_date"]
        if pd.isna(k_date):
            continue
        for cid_col in ("home_club_id", "away_club_id"):
            cid = int(fix_row[cid_col])
            key = (cid, gw)
            if key not in club_gw_dates or k_date < club_gw_dates[key]:
                club_gw_dates[key] = k_date

    ref = reference_date or resolve_gw_reference_date(processed_dir, target_gw)
    shield: dict[tuple[int, int], float] = {}

    for _, player in flagged.iterrows():
        pid = int(player["id"])
        cid = int(player["club_id"])
        status = str(player.get("status", "")).lower()
        chance = float(player.get("chance_of_playing_next_round") or 100.0)
        news = str(player.get("news") or "")
        ret_date = parse_fpl_return_date(news, ref)

        # Immediate target GW Hard DNP (ADR 0056)
        if status in {"i", "s", "u", "n"} or chance <= 0.0:
            shield[(pid, target_gw)] = 0.0

        # Find return gameweek if known
        return_gw: int | None = None
        if ret_date is not None:
            for gw in planning_gws:
                f_date = club_gw_dates.get((cid, gw))
                if f_date is not None and f_date >= ret_date:
                    return_gw = gw
                    break

        for gw in planning_gws:
            if gw == target_gw:
                continue

            if return_gw is not None:
                if gw < return_gw:
                    shield[(pid, gw)] = 0.0
                elif gw == return_gw:
                    shield[(pid, gw)] = 20.0  # Cameo appearance
                elif gw == return_gw + 1:
                    shield[(pid, gw)] = 65.0  # Managed start
                else:
                    # Full recovery: use healthy baseline (overcoming DNP depression)
                    shield[(pid, gw)] = healthy_baselines.get(pid, 80.0)
            elif status in {"i", "s", "u", "n"}:
                # Red-flagged with unknown or unparsed return date -> zeroed out
                shield[(pid, gw)] = 0.0

    return shield


def select_scouting_targets(
    processed_dir: Path,
    user_squad_ids: set[int] | None = None,
    top_per_tier: int = 2,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """
    Selects flagged User Squad members and top non-squad transfer candidates segmented
    by Position x Price Bracket for agentic deep-dive web intel.
    """
    players_path = processed_dir / "players.parquet"
    if not players_path.exists():
        return {"squad_flagged": [], "market_flagged_by_tier": {}}

    df_players = pd.read_parquet(players_path)
    flagged = get_flagged_players(df_players).copy()
    flagged = flagged[flagged["status"] != "u"]
    flagged["price"] = flagged["now_cost"] / 10.0
    flagged["selected_by_percent"] = pd.to_numeric(flagged["selected_by_percent"], errors="coerce").fillna(0.0)

    squad_ids = user_squad_ids or set()
    ref = reference_date or date.today()

    def format_player(r: pd.Series) -> dict[str, Any]:
        return {
            "id": int(r["id"]),
            "web_name": str(r["web_name"]),
            "club_id": int(r["club_id"]),
            "position_id": int(r["position_id"]),
            "price": float(r["price"]),
            "selected_by_percent": float(r["selected_by_percent"]),
            "status": str(r.get("status", "")),
            "chance": float(r.get("chance_of_playing_next_round") or 100.0),
            "news": str(r.get("news") or ""),
            "parsed_return_date": parse_fpl_return_date(str(r.get("news") or ""), ref),
        }

    squad_flagged = [
        format_player(r) for _, r in flagged[flagged["id"].isin(squad_ids)].iterrows()
    ]

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
) -> Path:
    """
    Synthesize consolidated 3-tier xMins override CSV.
    
    Precedence:
    Layer 3 (Top Guard): Targeted Overrides (user curves / web research)
    Layer 3 (Top Guard): Broad Pool Shield (automated FPL return date zeros & ramps)
    Layer 2 (Middle): Base External CSV (if provided)
    Layer 1 (Base Foundation): Blank cells fall back to Native In-House Champion.
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

    shield_map: dict[tuple[int, int], float] = {}
    if include_broad_pool_shield:
        ref = reference_date or resolve_gw_reference_date(processed_dir, target_gw)
        shield_map = build_broad_pool_shield(processed_dir, target_gw, horizon, reference_date=ref)

    target_map = dict(targeted_overrides or {})

    for gw in planning_gws:
        col_name = f"{gw}_xMins"
        vals: list[Any] = []
        for pid in out_df["ID"]:
            key = (int(pid), int(gw))
            if key in target_map:
                vals.append(float(target_map[key]))
            elif key in shield_map:
                vals.append(float(shield_map[key]))
            elif key in base_map:
                vals.append(float(base_map[key]))
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
