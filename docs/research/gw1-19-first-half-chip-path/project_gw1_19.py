"""GW1–19 Fixture Projections with Prior-Season Dual-Vector Seed multipliers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")

from features.builder import _fixture_maps
from models.participation_state_hybrid import ParticipationStateHybridModel

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
STATS_CSV = ROOT / "data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv"
OUT_CSV = ROOT / "data/research/gw1-19-first-half-chip-path/gw1-19_projections.csv"
SEED_CSV = ROOT / "data/research/gw1-19-first-half-chip-path/prior_season_dual_vector_seed.csv"
PRIOR_PATH = ROOT / "docs/research/gw1-6-preseason-pipeline/availability_priors.py"
END_GW = 19
_POS_TO_ID = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
DRAFT_ROLES = ("Nailed Starter", "Regular Starter")

_PRIOR_SPEC = importlib.util.spec_from_file_location("availability_priors_fh", PRIOR_PATH)
_PRIOR_MOD = importlib.util.module_from_spec(_PRIOR_SPEC)
assert _PRIOR_SPEC.loader is not None
_PRIOR_SPEC.loader.exec_module(_PRIOR_MOD)
apply_availability_priors = _PRIOR_MOD.apply_availability_priors

_SEED_SPEC = importlib.util.spec_from_file_location("dual_vector_seed", HERE / "build_dual_vector_seed.py")
_SEED_MOD = importlib.util.module_from_spec(_SEED_SPEC)
assert _SEED_SPEC.loader is not None
_SEED_SPEC.loader.exec_module(_SEED_MOD)


def project_gw1_19(
    stats_path: Path = STATS_CSV,
    out_csv: Path = OUT_CSV,
    end_gw: int = END_GW,
    draft_only: bool = True,
) -> pd.DataFrame:
    df_stats = pd.read_csv(stats_path)
    df_fixtures = pd.read_parquet("data/processed/fixtures.parquet")
    df_clubs = pd.read_parquet("data/processed/clubs.parquet")
    df_players = pd.read_parquet("data/processed/players.parquet")
    seed_path = SEED_CSV
    if not seed_path.exists():
        _SEED_MOD.build_dual_vector_seed(out_csv=seed_path)
    seed = pd.read_csv(seed_path)
    df_clubs = _SEED_MOD.apply_seed_to_clubs(df_clubs, seed)

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
            })

    features = pd.DataFrame(rows)
    preds = ParticipationStateHybridModel().predict(features, horizon=end_gw)
    merged = features.merge(
        preds, on=["player_id", "gameweek_id", "fixture_id"], how="left", suffixes=("", "_pred")
    )
    merged["projected_points"] = merged["projected_points"].fillna(0.0)
    merged["projected_minutes"] = merged["projected_minutes"].fillna(0.0)
    cost_map = dict(zip(df_players["id"], df_players["now_cost"] / 10.0, strict=False))
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
    gw_agg["cost"] = gw_agg["player_id"].map(cost_map).fillna(4.5)

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
            "cost": float(meta["cost"]),
        }
        total_xp = 0.0
        for gw in range(1, end_gw + 1):
            hit = grp[grp["gameweek_id"] == gw]
            xp = float(hit["projected_points"].sum()) if len(hit) else 0.0
            mins = float(hit["projected_minutes"].sum()) if len(hit) else 0.0
            row[f"gw{gw}_xp"] = round(xp, 2)
            row[f"gw{gw}_xmins"] = round(mins, 1)
            total_xp += xp
        row["total_19gw_xp"] = round(total_xp, 2)
        final_rows.append(row)

    out_df = pd.DataFrame(final_rows).sort_values("total_19gw_xp", ascending=False)
    if draft_only:
        out_df = out_df[out_df["expected_role"].isin(DRAFT_ROLES)].copy()
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_csv, index=False)
    print(f"Exported GW1-{end_gw} Dual-Vector projections ({len(out_df)} draft) to {out_csv}")
    return out_df


if __name__ == "__main__":
    project_gw1_19()
