"""GW1–5 Expected Points via ParticipationStateHybridModel.predict.

Builds a Feature-Contract-like frame from expected-stats rates + club strength
attack/defence multipliers (ADR 0005), runs production hybrid scoring + Softmax
bonus over the XI Contention Set, exports Draft-eligible rows to projections CSV.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, ".")

import pandas as pd

from features.builder import _fixture_maps
from models.participation_state_hybrid import ParticipationStateHybridModel

_POS_TO_ID = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
DRAFT_ROLES = ("Nailed Starter", "Regular Starter")


def _build_feature_frame(
    df_stats: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_clubs: pd.DataFrame,
    df_players: pd.DataFrame,
) -> pd.DataFrame:
    club_short_to_id = dict(zip(df_clubs["short_name"], df_clubs["id"], strict=False))
    fixture_map = _fixture_maps(df_fixtures, df_clubs, list(range(1, 6)))

    rows: list[dict] = []
    for _, player in df_stats.iterrows():
        club_id = club_short_to_id.get(player["club_short"])
        if club_id is None:
            continue
        club_fixtures = fixture_map[fixture_map["club_id"] == club_id]
        draft_avail = str(player.get("draft_availability", "eligible"))
        avail_override = str(player.get("availability_override", "") or "")
        exclude_all = draft_avail == "exclude_gw1-5" or "out_gw1-5" in avail_override
        exclude_gw1 = draft_avail == "exclude_gw1" or "unavailable_gw1" in avail_override

        p_start = float(player["p_start"])
        p_sub = float(player["p_sub_in"])
        p_dnp = float(player["p_dnp"])
        xmins_start = float(player["xmins_if_start"])
        xmins_sub = float(player["xmins_if_sub_in"])

        for _, fx in club_fixtures.iterrows():
            gw = int(fx["gameweek_id"])
            if exclude_all or (exclude_gw1 and gw == 1):
                row_p_start, row_p_sub, row_p_dnp = 0.0, 0.0, 1.0
            else:
                row_p_start, row_p_sub, row_p_dnp = p_start, p_sub, p_dnp

            rows.append({
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
                "rate_source": player.get("rate_source", ""),
                "provenance_note": player.get("provenance_note", ""),
            })

    return pd.DataFrame(rows)


def project_gw1_5_points(
    stats_csv_path: str = "data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv",
    fixtures_parquet_path: str = "data/processed/fixtures.parquet",
    clubs_parquet_path: str = "data/processed/clubs.parquet",
    players_parquet_path: str = "data/processed/players.parquet",
    output_csv_path: str = "data/research/expected-stats-gw1-5/gw1-5_projections.csv",
    export_draft_only: bool = True,
) -> pd.DataFrame:
    df_stats = pd.read_csv(stats_csv_path)
    df_fixtures = pd.read_parquet(fixtures_parquet_path)
    df_clubs = pd.read_parquet(clubs_parquet_path)
    df_players = pd.read_parquet(players_parquet_path)

    features = _build_feature_frame(df_stats, df_fixtures, df_clubs, df_players)
    if features.empty:
        raise RuntimeError("No feature rows built for GW1–5 projection")

    preds = ParticipationStateHybridModel().predict(features, horizon=5)
    merged = features.merge(
        preds,
        on=["player_id", "gameweek_id", "fixture_id"],
        how="left",
        suffixes=("", "_pred"),
    )
    merged["projected_points"] = merged["projected_points"].fillna(0.0)
    merged["projected_minutes"] = merged["projected_minutes"].fillna(0.0)

    # One row per player/GW (DGW would already be separate fixture rows — sum if needed)
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
            rate_source=("rate_source", "first"),
            provenance_note=("provenance_note", "first"),
        )
    )

    final_rows = []
    for pid, grp in gw_agg.groupby("player_id"):
        grp = grp.sort_values("gameweek_id")
        meta = grp.iloc[0]
        row: dict = {
            "player_id": int(pid),
            "web_name": meta["web_name"],
            "club_short": meta["club_short"],
            "position": meta["position"],
            "expected_role": meta["expected_role"],
            "draft_availability": meta["draft_availability"],
            "rate_source": meta["rate_source"],
            "provenance_note": meta["provenance_note"],
        }
        total_xp = 0.0
        total_mins = 0.0
        for gw in range(1, 6):
            hit = grp[grp["gameweek_id"] == gw]
            xp = float(hit["projected_points"].sum()) if len(hit) else 0.0
            mins = float(hit["projected_minutes"].sum()) if len(hit) else 0.0
            row[f"gw{gw}_xp"] = round(xp, 2)
            row[f"gw{gw}_xmins"] = round(mins, 1)
            total_xp += xp
            total_mins += mins
        row["total_5gw_xp"] = round(total_xp, 2)
        row["avg_gw_xp"] = round(total_xp / 5.0, 2)
        row["total_5gw_xmins"] = round(total_mins, 1)
        final_rows.append(row)

    out_df = pd.DataFrame(final_rows).sort_values("total_5gw_xp", ascending=False)
    if export_draft_only:
        out_df = out_df[out_df["expected_role"].isin(DRAFT_ROLES)].copy()

    Path(output_csv_path).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_csv_path, index=False)
    print(
        f"Exported GW1-5 projections ({len(out_df)} players; "
        f"bonus Softmax over {df_stats['player_id'].nunique()} XI Contention) "
        f"to {output_csv_path}"
    )
    print(out_df.head(15)[["web_name", "club_short", "position", "total_5gw_xp", "gw1_xp", "gw3_xp"]].to_string(index=False))
    return out_df


if __name__ == "__main__":
    project_gw1_5_points()
