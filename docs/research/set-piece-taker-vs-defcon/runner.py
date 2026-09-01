"""Set-piece taker vs Defcon xP comparison.

Writes companions beside this runner. 2024-25 from archive processed parquet.
2025-26 from vaastav CSVs (archive vaastav dir, else .tmp/agent download).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = OUTPUT_DIR.parents[2]
ARCHIVE_2024 = PROJECT_ROOT / "data" / "archive" / "2024-25" / "processed"
VAASTAV_2025 = PROJECT_ROOT / "data" / "archive" / "2025-26" / "vaastav"
TMP_DIR = PROJECT_ROOT / ".tmp" / "agent"
VAASTAV_PLAYERS_URL = (
    "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/"
    "master/data/2025-26/players_raw.csv"
)
VAASTAV_GW_URL = (
    "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/"
    "master/data/2025-26/gws/merged_gw.csv"
)

POS_FROM_ID = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
GOAL_PTS = {"GKP": 10.0, "GK": 10.0, "DEF": 6.0, "MID": 5.0, "FWD": 4.0}
CS_PTS = {"GKP": 4.0, "GK": 4.0, "DEF": 4.0, "MID": 1.0, "FWD": 0.0}
DEFCON_THRESH = {"DEF": 10, "MID": 12, "FWD": 12, "GKP": 10**9, "GK": 10**9}
MIN_SEASON_MINUTES = 900
MIN_STARTS = 10
POS_MAP_STR = {"GK": "GKP", "GKP": "GKP", "DEF": "DEF", "MID": "MID", "FWD": "FWD"}


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    with urllib.request.urlopen(url, timeout=120) as resp:
        dest.write_bytes(resp.read())
    return dest


def _resolve_2025_vaastav() -> tuple[Path, Path]:
    archive_players = VAASTAV_2025 / "players_raw.csv"
    archive_gw = VAASTAV_2025 / "gws" / "merged_gw.csv"
    if archive_players.exists() and archive_gw.exists():
        return archive_players, archive_gw
    players = _download(VAASTAV_PLAYERS_URL, TMP_DIR / "players_raw_2025-26.csv")
    gw = _download(VAASTAV_GW_URL, TMP_DIR / "merged_gw_2025-26.csv")
    return players, gw


def _sp_role(pen: float | None, corner: float | None, fk: float | None) -> str:
    is_pen = pen == 1.0
    is_cor = corner == 1.0
    is_fk = fk == 1.0
    if is_pen and is_cor:
        return "pen_and_corner"
    if is_pen:
        return "pen_primary"
    if is_cor:
        return "corner_primary"
    if is_fk:
        return "fk_primary"
    if pd.notna(pen) or pd.notna(corner) or pd.notna(fk):
        return "backup_sp"
    return "no_sp"


def _normalize_position(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return POS_FROM_ID.get(int(value))
    mapped = POS_MAP_STR.get(str(value).strip().upper())
    return mapped


def _player_metrics(perf: pd.DataFrame, players: pd.DataFrame, season: str) -> pd.DataFrame:
    merged = perf.merge(players, left_on="player_id", right_on="player_id", how="inner")
    merged["position"] = merged["position"].map(_normalize_position)
    merged = merged[merged["position"].isin(["DEF", "MID", "FWD"])].copy()
    thresh = merged["position"].map(DEFCON_THRESH)
    start_mask = merged["minutes"] >= 60
    merged["is_start"] = start_mask.astype(int)
    merged["xp_goals"] = merged["goals_scored"] * merged["position"].map(GOAL_PTS)
    merged["xp_assists"] = merged["assists"] * 3.0
    merged["xp_attack"] = merged["xp_goals"] + merged["xp_assists"]
    merged["xp_cs"] = merged["clean_sheets"] * merged["position"].map(CS_PTS)
    if "defensive_contribution" in merged.columns:
        merged["defcon_hit"] = (
            (merged["defensive_contribution"].fillna(0) >= thresh) & start_mask
        ).astype(int)
        merged["xp_defcon"] = merged["defcon_hit"] * 2.0
    else:
        merged["defcon_hit"] = 0
        merged["xp_defcon"] = 0.0
        merged["defensive_contribution"] = pd.NA
    grouped = merged.groupby(["player_id", "web_name", "position", "club_id", "sp_role"], dropna=False)
    out = grouped.agg(
        n_rows=("minutes", "size"),
        minutes=("minutes", "sum"),
        n_starts=("is_start", "sum"),
        goals=("goals_scored", "sum"),
        assists=("assists", "sum"),
        xg=("expected_goals", "sum"),
        xa=("expected_assists", "sum"),
        cs=("clean_sheets", "sum"),
        total_points=("total_points", "sum"),
        xp_attack=("xp_attack", "sum"),
        xp_cs=("xp_cs", "sum"),
        xp_defcon=("xp_defcon", "sum"),
        defcon_hits=("defcon_hit", "sum"),
        defcon_sum=("defensive_contribution", "sum"),
        penalties_missed=("penalties_missed", "sum"),
    ).reset_index()
    out["season"] = season
    out["has_defcon"] = season == "2025-26"
    per90 = out["minutes"].clip(lower=1) / 90.0
    starts = out["n_starts"].clip(lower=1)
    out["goals_per90"] = out["goals"] / per90
    out["assists_per90"] = out["assists"] / per90
    out["xg_per90"] = out["xg"] / per90
    out["xa_per90"] = out["xa"] / per90
    out["xp_attack_per90"] = out["xp_attack"] / per90
    out["xp_defcon_per90"] = out["xp_defcon"] / per90
    out["xp_cs_per90"] = out["xp_cs"] / per90
    out["pts_per90"] = out["total_points"] / per90
    out["xp_attack_per_start"] = out["xp_attack"] / starts
    out["xp_defcon_per_start"] = out["xp_defcon"] / starts
    out["xp_cs_per_start"] = out["xp_cs"] / starts
    out["pts_per_start"] = out["total_points"] / starts
    out["defcon_hit_rate"] = out["defcon_hits"] / starts
    out["regular"] = (out["minutes"] >= MIN_SEASON_MINUTES) & (out["n_starts"] >= MIN_STARTS)
    return out


def _load_2024() -> tuple[pd.DataFrame, dict[str, object]]:
    players = pd.read_parquet(ARCHIVE_2024 / "players.parquet")
    perf = pd.read_parquet(ARCHIVE_2024 / "player_performances.parquet")
    quality: dict[str, object] = {
        "season": "2024-25",
        "players_rows": int(len(players)),
        "perf_rows": int(len(perf)),
        "dup_player_fixture": int(perf.duplicated(["player_id", "fixture_id"]).sum()),
        "dup_player_gw": int(perf.duplicated(["player_id", "gameweek_id"]).sum()),
        "gw_min": int(perf["gameweek_id"].min()),
        "gw_max": int(perf["gameweek_id"].max()),
        "has_defcon": bool("defensive_contribution" in perf.columns),
        "pen_order_1": int((players["penalties_order"] == 1).sum()),
        "corner_order_1": int((players["corners_and_indirect_freekicks_order"] == 1).sum()),
        "fk_order_1": int((players["direct_freekicks_order"] == 1).sum()),
        "managers_excluded": int((players["position_id"] == 5).sum()),
    }
    players = players[players["position_id"].isin([1, 2, 3, 4])].copy()
    players["player_id"] = players["id"]
    players["position"] = players["position_id"]
    players["sp_role"] = [
        _sp_role(p, c, f)
        for p, c, f in zip(
            players["penalties_order"],
            players["corners_and_indirect_freekicks_order"],
            players["direct_freekicks_order"],
            strict=True,
        )
    ]
    keep_player = players[
        ["player_id", "web_name", "position", "club_id", "sp_role", "penalties_order",
         "corners_and_indirect_freekicks_order", "direct_freekicks_order"]
    ]
    return _player_metrics(perf, keep_player, "2024-25"), quality


def _load_2025() -> tuple[pd.DataFrame, dict[str, object]]:
    players_path, gw_path = _resolve_2025_vaastav()
    raw = pd.read_csv(players_path)
    gw = pd.read_csv(gw_path)
    before = len(gw)
    gw = gw.drop_duplicates(["element", "fixture"], keep="first")
    quality: dict[str, object] = {
        "season": "2025-26",
        "players_rows": int(len(raw)),
        "perf_rows": int(before),
        "dup_player_fixture_dropped": int(before - len(gw)),
        "dup_player_gw": int(gw.duplicated(["element", "GW"]).sum()),
        "gw_min": int(gw["GW"].min()),
        "gw_max": int(gw["GW"].max()),
        "has_defcon": True,
        "defcon_nulls": int(gw["defensive_contribution"].isna().sum()),
        "pen_order_1": int((raw["penalties_order"] == 1).sum()),
        "corner_order_1": int((raw["corners_and_indirect_freekicks_order"] == 1).sum()),
        "fk_order_1": int((raw["direct_freekicks_order"] == 1).sum()),
        "xp_column_unused": True,
    }
    raw["player_id"] = raw["id"]
    raw["position"] = raw["element_type"]
    raw["sp_role"] = [
        _sp_role(p, c, f)
        for p, c, f in zip(
            raw["penalties_order"],
            raw["corners_and_indirect_freekicks_order"],
            raw["direct_freekicks_order"],
            strict=True,
        )
    ]
    keep_player = raw[
        ["player_id", "web_name", "position", "club_id" if "club_id" in raw.columns else "team",
         "sp_role", "penalties_order", "corners_and_indirect_freekicks_order",
         "direct_freekicks_order"]
    ].copy()
    if "team" in keep_player.columns and "club_id" not in keep_player.columns:
        keep_player = keep_player.rename(columns={"team": "club_id"})
    perf = gw.rename(columns={
        "element": "player_id",
        "GW": "gameweek_id",
        "name": "gw_name",
    })
    perf = perf.drop(columns=["position"], errors="ignore")
    return _player_metrics(perf, keep_player, "2025-26"), quality


def _group_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    regular = metrics[metrics["regular"]].copy()
    rows: list[dict[str, object]] = []
    for (season, position, role), part in regular.groupby(["season", "position", "sp_role"]):
        rows.append({
            "season": season,
            "position": position,
            "sp_role": role,
            "n_players": int(len(part)),
            "mean_minutes": round(float(part["minutes"].mean()), 1),
            "mean_starts": round(float(part["n_starts"].mean()), 2),
            "mean_goals": round(float(part["goals"].mean()), 3),
            "mean_assists": round(float(part["assists"].mean()), 3),
            "mean_xg": round(float(part["xg"].mean()), 3),
            "mean_xa": round(float(part["xa"].mean()), 3),
            "mean_xp_attack_per_start": round(float(part["xp_attack_per_start"].mean()), 3),
            "mean_xp_defcon_per_start": round(float(part["xp_defcon_per_start"].mean()), 3),
            "mean_xp_cs_per_start": round(float(part["xp_cs_per_start"].mean()), 3),
            "mean_pts_per_start": round(float(part["pts_per_start"].mean()), 3),
            "mean_defcon_hit_rate": round(float(part["defcon_hit_rate"].mean()), 3),
            "mean_xg_per90": round(float(part["xg_per90"].mean()), 3),
            "mean_xa_per90": round(float(part["xa_per90"].mean()), 3),
            "mean_attack_plus_defcon_per_start": round(
                float((part["xp_attack_per_start"] + part["xp_defcon_per_start"]).mean()), 3
            ),
        })
    return pd.DataFrame(rows).sort_values(["season", "position", "sp_role"])


def _cohort_means(label: str, part: pd.DataFrame) -> dict[str, object]:
    if part.empty:
        return {"cohort": label, "n_players": 0}
    return {
        "cohort": label,
        "n_players": int(len(part)),
        "mean_defcon_hit_rate": round(float(part["defcon_hit_rate"].mean()), 3),
        "mean_xp_defcon_per_start": round(float(part["xp_defcon_per_start"].mean()), 3),
        "mean_xp_attack_per_start": round(float(part["xp_attack_per_start"].mean()), 3),
        "mean_xp_cs_per_start": round(float(part["xp_cs_per_start"].mean()), 3),
        "mean_attack_plus_defcon_per_start": round(
            float((part["xp_attack_per_start"] + part["xp_defcon_per_start"]).mean()), 3
        ),
        "mean_pts_per_start": round(float(part["pts_per_start"].mean()), 3),
    }


def _attach_gap(
    summary: pd.DataFrame,
    attack_gap: float,
    defcon_gap: float,
) -> pd.DataFrame:
    summary["attack_gap_sp_minus_high_defcon"] = round(attack_gap, 3)
    summary["defcon_gap_high_minus_sp"] = round(defcon_gap, 3)
    summary["net_sp_vs_high_defcon"] = round(attack_gap - defcon_gap, 3)
    summary["breakeven_hit_rate_gap"] = round(attack_gap / 2.0, 3)
    return summary


def _def_breakeven(metrics: pd.DataFrame) -> pd.DataFrame:
    def_ = metrics[(metrics["season"] == "2025-26") & (metrics["position"] == "DEF") & metrics["regular"]].copy()
    no_sp = def_[def_["sp_role"] == "no_sp"]
    corner = def_[def_["sp_role"].isin(["corner_primary", "pen_and_corner"])]
    any_sp = def_[def_["sp_role"] != "no_sp"]
    high_defcon = no_sp[no_sp["defcon_hit_rate"] >= no_sp["defcon_hit_rate"].quantile(0.75)]
    rows = [
        _cohort_means("DEF_no_sp_all_regular", no_sp),
        _cohort_means("DEF_no_sp_high_defcon_p75", high_defcon),
        _cohort_means("DEF_corner_primary", corner),
        _cohort_means("DEF_any_setpiece_order", any_sp),
    ]
    summary = pd.DataFrame(rows)
    attack_gap = float(corner["xp_attack_per_start"].mean()) - float(high_defcon["xp_attack_per_start"].mean())
    defcon_gap = float(high_defcon["xp_defcon_per_start"].mean()) - float(corner["xp_defcon_per_start"].mean())
    return _attach_gap(summary, attack_gap, defcon_gap)


def _mid_breakeven(metrics: pd.DataFrame) -> pd.DataFrame:
    mid = metrics[(metrics["season"] == "2025-26") & (metrics["position"] == "MID") & metrics["regular"]].copy()
    no_sp = mid[mid["sp_role"] == "no_sp"]
    corner = mid[mid["sp_role"].isin(["corner_primary", "pen_and_corner"])]
    pen = mid[mid["sp_role"].isin(["pen_primary", "pen_and_corner"])]
    high_defcon = no_sp[no_sp["defcon_hit_rate"] >= no_sp["defcon_hit_rate"].quantile(0.75)]
    rows = [
        _cohort_means("MID_no_sp_all_regular", no_sp),
        _cohort_means("MID_no_sp_high_defcon_p75", high_defcon),
        _cohort_means("MID_corner_or_pen_and_corner", corner),
        _cohort_means("MID_pen_or_pen_and_corner", pen),
    ]
    summary = pd.DataFrame(rows)
    attack_gap = float(corner["xp_attack_per_start"].mean()) - float(high_defcon["xp_attack_per_start"].mean())
    defcon_gap = float(high_defcon["xp_defcon_per_start"].mean()) - float(corner["xp_defcon_per_start"].mean())
    return _attach_gap(summary, attack_gap, defcon_gap)


def _def_examples(metrics: pd.DataFrame) -> pd.DataFrame:
    def_ = metrics[(metrics["season"] == "2025-26") & (metrics["position"] == "DEF") & metrics["regular"]].copy()
    def_["attack_plus_defcon"] = def_["xp_attack_per_start"] + def_["xp_defcon_per_start"]
    no_sp = def_[def_["sp_role"] == "no_sp"].sort_values("defcon_hit_rate", ascending=False)
    any_sp = def_[def_["sp_role"] != "no_sp"].sort_values("pts_per_start", ascending=False)
    cols = [
        "season", "web_name", "sp_role", "minutes", "n_starts", "goals", "assists",
        "xg", "xa", "defcon_hits", "defcon_hit_rate", "xp_attack_per_start",
        "xp_defcon_per_start", "xp_cs_per_start", "attack_plus_defcon", "pts_per_start",
        "total_points",
    ]
    top_defcon = no_sp.head(12).assign(example_set="high_defcon_no_sp")
    top_sp = any_sp.head(16).assign(example_set="any_setpiece_order")
    return pd.concat([top_defcon[cols + ["example_set"]], top_sp[cols + ["example_set"]]], ignore_index=True)


def _mid_examples(metrics: pd.DataFrame) -> pd.DataFrame:
    mid = metrics[(metrics["season"] == "2025-26") & (metrics["position"] == "MID") & metrics["regular"]].copy()
    mid["attack_plus_defcon"] = mid["xp_attack_per_start"] + mid["xp_defcon_per_start"]
    no_sp = mid[mid["sp_role"] == "no_sp"].sort_values("defcon_hit_rate", ascending=False)
    sp = mid[mid["sp_role"] != "no_sp"].sort_values("pts_per_start", ascending=False)
    cols = [
        "season", "web_name", "sp_role", "minutes", "n_starts", "goals", "assists",
        "xg", "xa", "defcon_hits", "defcon_hit_rate", "xp_attack_per_start",
        "xp_defcon_per_start", "xp_cs_per_start", "attack_plus_defcon", "pts_per_start",
        "total_points",
    ]
    top_defcon = no_sp.head(12).assign(example_set="high_defcon_no_sp")
    top_sp = sp.head(16).assign(example_set="any_setpiece_order")
    return pd.concat([top_defcon[cols + ["example_set"]], top_sp[cols + ["example_set"]]], ignore_index=True)


def _model_implied() -> pd.DataFrame:
    """Engine and league-implied set-piece xP. Not from player rows."""
    pen_xg = 0.79
    league_pens_per_team = 0.125
    league_pen_xg90 = league_pens_per_team * pen_xg
    model_pen_xg90 = 0.15
    corner_goals_per_team = 0.175
    taker_assist_credit = 0.60
    corner_xa90 = corner_goals_per_team * taker_assist_credit
    rows = []
    for pos, gpts in (("DEF", 6.0), ("MID", 5.0), ("FWD", 4.0)):
        rows.append({
            "source": "engine_penalty_isolation",
            "position": pos,
            "assumption": "penalties_order==1 and expected_goals_per90>0.15; 0.15 xG/90 unscaled by attack_multiplier",
            "xg_or_xa_per90": model_pen_xg90,
            "xp_per90": round(model_pen_xg90 * gpts, 3),
            "defcon_hits_equivalent_per90": round((model_pen_xg90 * gpts) / 2.0, 3),
        })
        rows.append({
            "source": "league_penalty_taker",
            "position": pos,
            "assumption": "0.125 pens/team/match * Opta 0.79 xG; exclusive taker plays 90",
            "xg_or_xa_per90": round(league_pen_xg90, 3),
            "xp_per90": round(league_pen_xg90 * gpts, 3),
            "defcon_hits_equivalent_per90": round((league_pen_xg90 * gpts) / 2.0, 3),
        })
        rows.append({
            "source": "corner_taker_assist_credit",
            "position": pos,
            "assumption": "0.35 corner-goals/match both teams (2024-25 Opta); 60% credit taker; 3pt assist",
            "xg_or_xa_per90": round(corner_xa90, 3),
            "xp_per90": round(corner_xa90 * 3.0, 3),
            "defcon_hits_equivalent_per90": round((corner_xa90 * 3.0) / 2.0, 3),
        })
    return pd.DataFrame(rows)


def main() -> None:
    metrics_2024, q24 = _load_2024()
    metrics_2025, q25 = _load_2025()
    metrics = pd.concat([metrics_2024, metrics_2025], ignore_index=True)
    quality = pd.DataFrame([q24, q25])
    groups = _group_summary(metrics)
    breakeven = _def_breakeven(metrics)
    examples = _def_examples(metrics)
    mid_break = _mid_breakeven(metrics)
    mid_examples = _mid_examples(metrics)
    implied = _model_implied()
    metrics.to_csv(OUTPUT_DIR / "player_metrics.csv", index=False)
    quality.to_csv(OUTPUT_DIR / "data_quality.csv", index=False)
    groups.to_csv(OUTPUT_DIR / "group_summary.csv", index=False)
    breakeven.to_csv(OUTPUT_DIR / "def_breakeven.csv", index=False)
    examples.to_csv(OUTPUT_DIR / "def_examples.csv", index=False)
    mid_break.to_csv(OUTPUT_DIR / "mid_breakeven.csv", index=False)
    mid_examples.to_csv(OUTPUT_DIR / "mid_examples.csv", index=False)
    implied.to_csv(OUTPUT_DIR / "implied_setpiece_xp.csv", index=False)
    counts = {
        f"{season}|{position}": int(n)
        for (season, position), n in metrics.groupby(["season", "position"])["regular"].sum().items()
    }
    stamp = {
        "min_season_minutes": MIN_SEASON_MINUTES,
        "min_starts": MIN_STARTS,
        "regular_counts": counts,
    }
    (OUTPUT_DIR / "run_meta.json").write_text(json.dumps(stamp, indent=2), encoding="utf-8")
    print(quality.to_string(index=False))
    print(groups.to_string(index=False))
    print(breakeven.to_string(index=False))
    print(mid_break.to_string(index=False))


if __name__ == "__main__":
    main()
