"""Full-season (GW1–38) player projections for ownership value explorer.

Uses Stage 2 expected-stats event rates + Draft Availability priors +
ParticipationStateHybridModel over the full fixture list.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, ".")

import pandas as pd

from features.builder import _fixture_maps
from models.participation_state_hybrid import ParticipationStateHybridModel

ROOT = Path(__file__).resolve().parents[3]
STATS_CSV = ROOT / "data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv"
OUT_DIR = ROOT / "data/research/ownership-value-explorer"
OUT_CSV = OUT_DIR / "season_projections.csv"
PRIOR_PATH = ROOT / "docs/research/gw1-6-preseason-pipeline/availability_priors.py"

_POS_TO_ID = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
SEASON_END_GW = 38
EARLY_END_GW = 6

_PRIOR_SPEC = importlib.util.spec_from_file_location("availability_priors", PRIOR_PATH)
_PRIOR_MOD = importlib.util.module_from_spec(_PRIOR_SPEC)
assert _PRIOR_SPEC.loader is not None
_PRIOR_SPEC.loader.exec_module(_PRIOR_MOD)
apply_availability_priors = _PRIOR_MOD.apply_availability_priors


def project_season_points(
    stats_path: Path = STATS_CSV,
    out_csv: Path = OUT_CSV,
    end_gw: int = SEASON_END_GW,
) -> pd.DataFrame:
    """Project GW1–end_gw xP/xMins and write player-level season summary CSV."""
    if not stats_path.exists():
        raise FileNotFoundError(
            f"missing expected-stats CSV (run Stage 2 first): {stats_path}"
        )

    df_stats = pd.read_csv(stats_path)
    df_fixtures = pd.read_parquet("data/processed/fixtures.parquet")
    df_clubs = pd.read_parquet("data/processed/clubs.parquet")
    df_players = pd.read_parquet("data/processed/players.parquet")

    club_short_to_id = dict(zip(df_clubs["short_name"], df_clubs["id"], strict=False))
    fixture_map = _fixture_maps(df_fixtures, df_clubs, list(range(1, end_gw + 1)))

    rows: list[dict] = []
    for _, player in df_stats.iterrows():
        club_id = club_short_to_id.get(player["club_short"])
        if club_id is None:
            continue
        club_fixtures = fixture_map[fixture_map["club_id"] == club_id]
        draft_avail = str(player.get("draft_availability", "eligible"))
        avail_override = str(player.get("availability_override", "") or "")
        p_start = float(player["p_start"])
        p_sub = float(player["p_sub_in"])
        p_dnp = float(player["p_dnp"])
        xmins_start = float(player["xmins_if_start"])
        xmins_sub = float(player["xmins_if_sub_in"])

        for _, fx in club_fixtures.iterrows():
            gw = int(fx["gameweek_id"])
            row_p_start, row_p_sub, row_p_dnp = apply_availability_priors(
                p_start, p_sub, p_dnp, draft_avail, avail_override, gw
            )
            rows.append(
                {
                    "player_id": int(player["player_id"]),
                    "web_name": player["web_name"],
                    "club_short": player["club_short"],
                    "club_id": int(club_id),
                    "position": player["position"],
                    "position_id": _POS_TO_ID.get(str(player["position"]), 3),
                    "expected_role": player["expected_role"],
                    "draft_availability": draft_avail,
                    "gameweek_id": gw,
                    "fixture_id": int(fx["fixture_id"]),
                    "difficulty": float(fx["difficulty"]),
                    "attack_multiplier": float(fx["attack_multiplier"]),
                    "defence_multiplier": float(fx["defence_multiplier"]),
                    "p_start": row_p_start,
                    "p_sub_in": row_p_sub,
                    "p_dnp": row_p_dnp,
                    "xmins_if_start": xmins_start,
                    "xmins_if_sub_in": xmins_sub,
                    "p_60_if_start": min(1.0, max(0.0, (xmins_start - 45.0) / 30.0)),
                    "p_60_if_sub_in": min(1.0, max(0.0, (xmins_sub - 45.0) / 30.0)),
                    "per90_xg": float(player["per90_xg"]),
                    "per90_xa": float(player["per90_xa"]),
                    "per90_defensive_contribution": float(
                        player.get("per90_defensive_contribution", player["per90_defcon"])
                    ),
                    "per90_saves": float(player["per90_saves"]),
                    "per90_goals_conceded": float(player["per90_goals_conceded"]),
                    "per90_threat": 0.0,
                    "per90_creativity": 0.0,
                    "per90_goals": 0.0,
                    "per90_assists": 0.0,
                    "per90_yellow_cards": 0.0,
                    "per90_red_cards": 0.0,
                    "per90_penalties_saved": 0.0,
                    "per90_penalties_missed": 0.0,
                    "per90_own_goals": 0.0,
                    "is_immediate_next_gw": False,
                    "has_availability_snapshot": False,
                    "chance_of_playing": 100.0,
                }
            )

    features = pd.DataFrame(rows)
    preds = ParticipationStateHybridModel().predict(features, horizon=end_gw)
    merged = features.merge(
        preds, on=["player_id", "gameweek_id", "fixture_id"], how="left", suffixes=("", "_pred")
    )
    merged["projected_points"] = merged["projected_points"].fillna(0.0)
    merged["projected_minutes"] = merged["projected_minutes"].fillna(0.0)

    gw_agg = (
        merged.groupby(["player_id", "gameweek_id"], as_index=False)
        .agg(
            projected_points=("projected_points", "sum"),
            projected_minutes=("projected_minutes", "sum"),
            web_name=("web_name", "first"),
            club_short=("club_short", "first"),
            position=("position", "first"),
            expected_role=("expected_role", "first"),
            draft_availability=("draft_availability", "first"),
        )
    )

    df_p = df_players[["id", "now_cost", "selected_by_percent"]].copy()
    df_p["ownership_pct"] = pd.to_numeric(df_p["selected_by_percent"], errors="coerce")
    df_p["cost"] = df_p["now_cost"] / 10.0

    out_rows: list[dict] = []
    for pid, grp in gw_agg.groupby("player_id"):
        meta = grp.iloc[0]
        own = df_p.loc[df_p["id"] == pid]
        cost = float(own["cost"].iloc[0]) if len(own) else 0.0
        ownership = float(own["ownership_pct"].iloc[0]) if len(own) and pd.notna(own["ownership_pct"].iloc[0]) else float("nan")

        season = grp[grp["gameweek_id"] <= end_gw]
        early = grp[grp["gameweek_id"] <= EARLY_END_GW]
        total_xp = float(season["projected_points"].sum())
        total_xmins = float(season["projected_minutes"].sum())
        early_xp = float(early["projected_points"].sum())
        early_xmins = float(early["projected_minutes"].sum())
        n_gw_season = max(1, int(season["gameweek_id"].nunique()))
        n_gw_early = max(1, int(early["gameweek_id"].nunique()))

        out_rows.append(
            {
                "player_id": int(pid),
                "web_name": meta["web_name"],
                "club_short": meta["club_short"],
                "position": meta["position"],
                "expected_role": meta["expected_role"],
                "draft_availability": meta["draft_availability"],
                "cost": cost,
                "ownership_pct": ownership,
                "total_season_xp": round(total_xp, 2),
                "total_season_xmins": round(total_xmins, 1),
                "avg_xmins_season": round(total_xmins / n_gw_season, 1),
                "xp_per_90_season": round(total_xp / (total_xmins / 90.0), 4) if total_xmins > 0 else float("nan"),
                "total_gw1_6_xp": round(early_xp, 2),
                "total_gw1_6_xmins": round(early_xmins, 1),
                "avg_xmins_gw1_6": round(early_xmins / n_gw_early, 1),
                "xp_per_90_gw1_6": round(early_xp / (early_xmins / 90.0), 4) if early_xmins > 0 else float("nan"),
                "n_gameweeks": n_gw_season,
            }
        )

    frame = pd.DataFrame(out_rows).sort_values("total_season_xp", ascending=False).reset_index(drop=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_csv, index=False)
    print(f"Season projections: {len(frame)} players (GW1–{end_gw}) → {out_csv}")
    return frame


def main() -> None:
    project_season_points()


if __name__ == "__main__":
    main()
