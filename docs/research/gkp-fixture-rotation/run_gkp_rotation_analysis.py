"""Starter GKP fixture rotation analysis (horizon-matched hybrid xP).

Scorer: ParticipationStateHybridModel over GW1–38 with forced flat starter minutes.
Pick rule: FDR-min primary; also report max(xP) upper bound.
Rates authority: expected-stats-gw1-5.csv (per90_saves, per90_goals_conceded).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from features.builder import _fixture_maps
from models.participation_state_hybrid import ParticipationStateHybridModel

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
RESEARCH_DIR = PROJECT_ROOT / "data" / "research"
OUT_DIR = RESEARCH_DIR / "gkp-fixture-rotation"
STATS_CSV = RESEARCH_DIR / "gw1-6-preseason-pipeline" / "02-expected-stats-gw1-5" / "expected-stats-gw1-5.csv"
ROLE_CSV = RESEARCH_DIR / "gw1-6-preseason-pipeline" / "01-expected-role-gw1-5" / "expected-role-gw1-5.csv"

DRAFT_ROLES = ("Nailed Starter", "Regular Starter")
PROMOTED_CLUBS = frozenset({"COV", "HUL", "IPS"})
FLAT_START_MINUTES = 90.0
GKP_POSITION_ID = 1
HORIZONS = (
    ("gw1_6", 1, 6),
    ("gw1_10", 1, 10),
    ("gw1_19", 1, 19),
    ("full_season", 1, 38),
)


def pick_rotated_xp(
    xp1: float,
    xp2: float,
    fdr1: float,
    fdr2: float,
    *,
    home1: bool = False,
    home2: bool = False,
) -> float:
    """FDR-min weekly pick; home wins FDR ties; else keep gkp1."""
    if fdr1 < fdr2:
        return float(xp1)
    if fdr2 < fdr1:
        return float(xp2)
    if home1 and not home2:
        return float(xp1)
    if home2 and not home1:
        return float(xp2)
    return float(xp1)


def summarize_rotation(
    xp1: np.ndarray,
    xp2: np.ndarray,
    fdr1: np.ndarray,
    fdr2: np.ndarray,
    home1: np.ndarray,
    home2: np.ndarray,
) -> dict[str, float | int]:
    """Horizon totals under FDR-min and max(xP) pick rules."""
    n = len(xp1)
    if not (len(xp2) == len(fdr1) == len(fdr2) == len(home1) == len(home2) == n):
        raise ValueError("rotation arrays must share length")
    if n == 0:
        raise ValueError("rotation window cannot be empty")

    fdr_picks = [
        pick_rotated_xp(
            float(xp1[i]),
            float(xp2[i]),
            float(fdr1[i]),
            float(fdr2[i]),
            home1=bool(home1[i]),
            home2=bool(home2[i]),
        )
        for i in range(n)
    ]
    max_picks = [max(float(xp1[i]), float(xp2[i])) for i in range(n)]
    rotated = np.minimum(fdr1, fdr2)
    tot_rot = float(sum(fdr_picks))
    tot_max = float(sum(max_picks))
    best_single = max(float(xp1.sum()), float(xp2.sum()))
    corr = pd.Series(fdr1).corr(pd.Series(fdr2))
    corr_v = 0.0 if pd.isna(corr) else float(corr)
    return {
        "num_gws": n,
        "tot_rot_xp": round(tot_rot, 2),
        "tot_rot_xp_maxxp": round(tot_max, 2),
        "xp_gain_vs_best_single": round(tot_rot - best_single, 2),
        "maxxp_delta": round(tot_max - tot_rot, 2),
        "rotated_avg_fdr": round(float(rotated.mean()), 4),
        "fdr_gain": round(float(min(float(fdr1.mean()), float(fdr2.mean())) - rotated.mean()), 4),
        "easy_gws": int(np.sum(rotated <= 2)),
        "easy_gw_pct": round(float(np.sum(rotated <= 2) / n * 100.0), 1),
        "fdr_corr": round(corr_v, 4),
        "avg_fdr1": round(float(fdr1.mean()), 4),
        "avg_fdr2": round(float(fdr2.mean()), 4),
    }


def compute_rqi(
    *,
    tot_rot_xp: float,
    num_gws: int,
    rot_avg_fdr: float,
    fdr_corr: float,
    easy_gw_pct: float,
    total_price: float,
) -> float:
    """Points-heavy 40/20/20/10/10 RQI; S_tot_xp from horizon-matched xP/GW."""
    rot_xp_per_gw = tot_rot_xp / num_gws
    s_tot_xp = float(np.clip((rot_xp_per_gw - 2.5) / (4.2 - 2.5) * 100.0, 0, 100))
    s_fdr = float(np.clip((5.0 - rot_avg_fdr) / (5.0 - 2.0) * 100.0, 0, 100))
    s_corr = float(np.clip((-fdr_corr + 1.0) / 2.0 * 100.0, 0, 100))
    s_cost = 100.0 if total_price <= 9.0 else 75.0
    return round(0.40 * s_tot_xp + 0.20 * s_fdr + 0.20 * s_corr + 0.10 * easy_gw_pct + 0.10 * s_cost, 2)


def _starter_gkps(df_stats: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    starters = df_stats[
        (df_stats["position"] == "GKP") & (df_stats["expected_role"].isin(DRAFT_ROLES))
    ].copy()
    cost_map = players.set_index("id")["now_cost"] / 10.0
    starters["price"] = starters["player_id"].map(cost_map)
    club_map = players.set_index("id")["club_id"]
    starters["club_id"] = starters["player_id"].map(club_map)
    return starters.dropna(subset=["price", "club_id"]).reset_index(drop=True)


def build_performance_baseline(
    stats_csv: Path = STATS_CSV,
    players_parquet: Path = DATA_DIR / "players.parquet",
) -> pd.DataFrame:
    """Scorer-aligned GKP baseline: expected-stats saves/90 and GC/90."""
    df_stats = pd.read_csv(stats_csv)
    players = pd.read_parquet(players_parquet)
    starters = _starter_gkps(df_stats, players)
    out = starters[
        [
            "player_id",
            "web_name",
            "club_short",
            "price",
            "expected_role",
            "per90_saves",
            "per90_goals_conceded",
            "rate_source",
            "usable_mins_total",
            "provenance_note",
        ]
    ].copy()
    out["has_promoted_proxy"] = out["club_short"].isin(PROMOTED_CLUBS)
    out = out.sort_values(["per90_saves", "web_name"], ascending=[False, True]).reset_index(drop=True)
    return out


def _build_club_schedule(
    fixtures: pd.DataFrame,
    clubs: pd.DataFrame,
    gameweeks: list[int],
) -> tuple[pd.DataFrame, dict[int, dict[int, float]], dict[int, dict[int, bool]]]:
    fmap = _fixture_maps(fixtures, clubs, gameweeks)
    club_fdr: dict[int, dict[int, float]] = {int(c): {} for c in clubs["id"]}
    club_home: dict[int, dict[int, bool]] = {int(c): {} for c in clubs["id"]}
    for _, f in fixtures.iterrows():
        gw = int(f["gameweek_id"])
        if gw not in gameweeks:
            continue
        h_club, a_club = int(f["home_club_id"]), int(f["away_club_id"])
        h_diff, a_diff = float(f["team_h_difficulty"]), float(f["team_a_difficulty"])
        club_fdr[h_club][gw] = min(club_fdr[h_club].get(gw, 99.0), h_diff)
        club_fdr[a_club][gw] = min(club_fdr[a_club].get(gw, 99.0), a_diff)
        club_home[h_club][gw] = True
        club_home[a_club][gw] = False
    return fmap, club_fdr, club_home


def project_starter_gkp_grid(
    starters: pd.DataFrame,
    fmap: pd.DataFrame,
    *,
    end_gw: int = 38,
) -> pd.DataFrame:
    """Long-format fixture projections with forced flat starter minutes."""
    rows: list[dict] = []
    for _, player in starters.iterrows():
        club_id = int(player["club_id"])
        club_fixtures = fmap[fmap["club_id"] == club_id]
        for _, fx in club_fixtures.iterrows():
            rows.append(
                {
                    "player_id": int(player["player_id"]),
                    "web_name": player["web_name"],
                    "club_short": player["club_short"],
                    "club_id": club_id,
                    "position": "GKP",
                    "position_id": GKP_POSITION_ID,
                    "expected_role": player["expected_role"],
                    "price": float(player["price"]),
                    "gameweek_id": int(fx["gameweek_id"]),
                    "fixture_id": int(fx["fixture_id"]),
                    "difficulty": float(fx["difficulty"]),
                    "attack_multiplier": float(fx["attack_multiplier"]),
                    "defence_multiplier": float(fx["defence_multiplier"]),
                    "p_start": 1.0,
                    "p_sub_in": 0.0,
                    "p_dnp": 0.0,
                    "xmins_if_start": FLAT_START_MINUTES,
                    "xmins_if_sub_in": 0.0,
                    "p_60_if_start": 1.0,
                    "p_60_if_sub_in": 0.0,
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
        preds,
        on=["player_id", "gameweek_id", "fixture_id"],
        how="left",
        suffixes=("", "_pred"),
    )
    merged["projected_points"] = merged["projected_points"].fillna(0.0)
    return (
        merged.groupby(["player_id", "gameweek_id"], as_index=False)
        .agg(
            projected_points=("projected_points", "sum"),
            web_name=("web_name", "first"),
            club_short=("club_short", "first"),
            club_id=("club_id", "first"),
            expected_role=("expected_role", "first"),
            price=("price", "first"),
            per90_saves=("per90_saves", "first"),
            per90_goals_conceded=("per90_goals_conceded", "first"),
        )
    )


def run_analysis() -> pd.DataFrame:
    players = pd.read_parquet(DATA_DIR / "players.parquet")
    clubs = pd.read_parquet(DATA_DIR / "clubs.parquet")
    fixtures = pd.read_parquet(DATA_DIR / "fixtures.parquet")
    df_stats = pd.read_csv(STATS_CSV)
    # Role CSV is the starter filter authority when present; rates still from stats.
    if ROLE_CSV.exists():
        roles = pd.read_csv(ROLE_CSV)
        role_gk = roles[
            (roles["position"] == "GKP") & (roles["expected_role"].isin(DRAFT_ROLES))
        ][["player_id", "expected_role", "web_name", "club_short"]]
        df_stats = df_stats.merge(
            role_gk[["player_id"]],
            on="player_id",
            how="inner",
        )

    starters = _starter_gkps(df_stats, players)
    fmap, club_fdr, club_home = _build_club_schedule(fixtures, clubs, list(range(1, 39)))
    gw_xp = project_starter_gkp_grid(starters, fmap, end_gw=38)

    meta = {
        int(r.player_id): r
        for r in gw_xp.drop_duplicates("player_id").itertuples(index=False)
    }
    xp_lookup = {
        int(pid): grp.set_index("gameweek_id")["projected_points"].to_dict()
        for pid, grp in gw_xp.groupby("player_id")
    }

    starter_ids = sorted(meta.keys())
    all_rows: list[dict] = []
    for h_name, start_gw, end_gw in HORIZONS:
        gws = list(range(start_gw, end_gw + 1))
        for i, id1 in enumerate(starter_ids):
            for id2 in starter_ids[i + 1 :]:
                g1, g2 = meta[id1], meta[id2]
                c1, c2 = int(g1.club_id), int(g2.club_id)
                if c1 == c2:
                    continue
                tot_price = float(g1.price) + float(g2.price)
                if tot_price > 9.5:
                    continue

                xp1 = np.array([float(xp_lookup[id1].get(gw, 0.0)) for gw in gws], dtype=float)
                xp2 = np.array([float(xp_lookup[id2].get(gw, 0.0)) for gw in gws], dtype=float)
                fdr1 = np.array([float(club_fdr[c1].get(gw, 3.0)) for gw in gws], dtype=float)
                fdr2 = np.array([float(club_fdr[c2].get(gw, 3.0)) for gw in gws], dtype=float)
                home1 = np.array([bool(club_home[c1].get(gw, False)) for gw in gws])
                home2 = np.array([bool(club_home[c2].get(gw, False)) for gw in gws])

                summary = summarize_rotation(xp1, xp2, fdr1, fdr2, home1, home2)
                rqi = compute_rqi(
                    tot_rot_xp=float(summary["tot_rot_xp"]),
                    num_gws=int(summary["num_gws"]),
                    rot_avg_fdr=float(summary["rotated_avg_fdr"]),
                    fdr_corr=float(summary["fdr_corr"]),
                    easy_gw_pct=float(summary["easy_gw_pct"]),
                    total_price=tot_price,
                )
                all_rows.append(
                    {
                        "horizon": h_name,
                        "start_gw": start_gw,
                        "end_gw": end_gw,
                        "club1": g1.club_short,
                        "gkp1": g1.web_name,
                        "role1": g1.expected_role,
                        "price1": float(g1.price),
                        "per90_saves1": round(float(g1.per90_saves), 4),
                        "per90_goals_conceded1": round(float(g1.per90_goals_conceded), 4),
                        "club2": g2.club_short,
                        "gkp2": g2.web_name,
                        "role2": g2.expected_role,
                        "price2": float(g2.price),
                        "per90_saves2": round(float(g2.per90_saves), 4),
                        "per90_goals_conceded2": round(float(g2.per90_goals_conceded), 4),
                        "total_price": tot_price,
                        "fdr_corr": summary["fdr_corr"],
                        "avg_fdr1": summary["avg_fdr1"],
                        "avg_fdr2": summary["avg_fdr2"],
                        "rotated_avg_fdr": summary["rotated_avg_fdr"],
                        "fdr_gain": summary["fdr_gain"],
                        "easy_gws": summary["easy_gws"],
                        "easy_gw_pct": summary["easy_gw_pct"],
                        "tot_rot_xp": summary["tot_rot_xp"],
                        "tot_rot_xp_maxxp": summary["tot_rot_xp_maxxp"],
                        "maxxp_delta": summary["maxxp_delta"],
                        "xp_gain_vs_best_single": summary["xp_gain_vs_best_single"],
                        "has_promoted_proxy": bool(
                            g1.club_short in PROMOTED_CLUBS or g2.club_short in PROMOTED_CLUBS
                        ),
                        "rqi": rqi,
                    }
                )

    res_df = pd.DataFrame(all_rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res_df.to_csv(OUT_DIR / "gkp_rotation_matrix.csv", index=False)
    baseline = build_performance_baseline()
    baseline.to_csv(OUT_DIR / "gkp_performance_baseline.csv", index=False)
    return res_df


if __name__ == "__main__":
    df = run_analysis()
    print(
        f"Generated {len(df)} starter GKP rotation records in "
        f"{OUT_DIR / 'gkp_rotation_matrix.csv'}"
    )
