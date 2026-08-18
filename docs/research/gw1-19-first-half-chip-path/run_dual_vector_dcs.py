"""Dual-Vector DCS ranking for GW1–19. Writes under this topic only — live DCS CSVs untouched."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")

from features.builder import _fixture_maps

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT_DIR = ROOT / "data/research/gw1-19-first-half-chip-path"
DCS_DIR = OUT_DIR / "dcs"
DATA_DIR = ROOT / "data/processed"
STATS_CSV = ROOT / "data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv"

_SEED_SPEC = importlib.util.spec_from_file_location("dv_seed", HERE / "build_dual_vector_seed.py")
_SEED = importlib.util.module_from_spec(_SEED_SPEC)
assert _SEED_SPEC.loader is not None
_SEED_SPEC.loader.exec_module(_SEED)

_DCS_SPEC = importlib.util.spec_from_file_location(
    "dcs_runner",
    ROOT / "docs/research/defensive-fixture-rotation/run_defensive_rotation_analysis.py",
)
_DCS = importlib.util.module_from_spec(_DCS_SPEC)
assert _DCS_SPEC.loader is not None
_DCS_SPEC.loader.exec_module(_DCS)
_DCS.HORIZONS = (("gw1_19", 1, 19),)


def effective_fdr_matrix(fmap: pd.DataFrame, clubs: pd.DataFrame) -> tuple[np.ndarray, dict[int, str], dict[int, int]]:
    club_ids = sorted(clubs["id"].tolist())
    id_to_idx = {cid: i for i, cid in enumerate(club_ids)}
    idx_to_short = {i: str(clubs.loc[clubs["id"] == cid, "short_name"].iloc[0]) for cid, i in id_to_idx.items()}
    fdr = np.full((len(club_ids), 38), 3.0)
    for _, row in fmap.iterrows():
        gw = int(row["gameweek_id"])
        if gw < 1 or gw > 19:
            continue
        idx = id_to_idx[int(row["club_id"])]
        fdr[idx, gw - 1] = float(np.clip(float(row["defence_multiplier"]) * 3.0, 1.2, 5.4))
    return fdr, idx_to_short, id_to_idx


def run_dual_vector_dcs() -> None:
    DCS_DIR.mkdir(parents=True, exist_ok=True)
    players = pd.read_parquet(DATA_DIR / "players.parquet")
    clubs = pd.read_parquet(DATA_DIR / "clubs.parquet")
    fixtures = pd.read_parquet(DATA_DIR / "fixtures.parquet")
    seed = pd.read_csv(OUT_DIR / "prior_season_dual_vector_seed.csv")
    clubs = _SEED.apply_seed_to_clubs(clubs, seed)
    fmap = _fixture_maps(fixtures, clubs, list(range(1, 20)))
    fdr_mat, idx_to_short, id_to_idx = effective_fdr_matrix(fmap, clubs)
    pd.DataFrame(fdr_mat[:, :19], index=[idx_to_short[i] for i in range(20)], columns=[f"gw{g}" for g in range(1, 20)]).to_csv(
        DCS_DIR / "club_effective_fdr_gw1_19.csv"
    )

    df_stats = pd.read_csv(STATS_CSV)
    cost_map = players.set_index("id")["now_cost"] / 10.0
    club_map = players.set_index("id")["club_id"]
    df_stats["price"] = df_stats["player_id"].map(cost_map)
    df_stats["club_id"] = df_stats["player_id"].map(club_map)
    starters_gkp = df_stats[
        (df_stats["position"] == "GKP") & (df_stats["expected_role"].isin(_DCS.DRAFT_ROLES))
    ].dropna(subset=["price", "club_id"]).reset_index(drop=True)
    starters_def = df_stats[
        (df_stats["position"] == "DEF") & (df_stats["expected_role"].isin(_DCS.DRAFT_ROLES))
    ].dropna(subset=["price", "club_id"]).reset_index(drop=True)
    gamma = _DCS.compute_outfield_capital_slope(STATS_CSV, DATA_DIR / "players.parquet")
    gw_xp_gkp = _DCS.project_starter_grid(starters_gkp, fmap, "GKP", _DCS.GKP_POSITION_ID, end_gw=19)
    gw_xp_def = _DCS.project_starter_grid(starters_def, fmap, "DEF", _DCS.DEF_POSITION_ID, end_gw=19)
    df_gkp_strat, df_gkp_pairs = _DCS.run_gkp_strategy_analysis(starters_gkp, gw_xp_gkp, fdr_mat, id_to_idx, gamma=gamma)
    df_gkp_strat.to_csv(DCS_DIR / "gkp_strategy_comparison.csv", index=False)
    df_gkp_pairs.to_csv(DCS_DIR / "gkp_rotation_matrix.csv", index=False)
    df_def_clubs = _DCS.run_def_club_combinatorial_analysis(fdr_mat, idx_to_short)
    df_def_clubs.to_csv(DCS_DIR / "def_club_partitions_matrix.csv", index=False)
    _, df_def_top_tier = _DCS.simulate_def_tier_player_rotations(starters_def, gw_xp_def, fdr_mat, id_to_idx, gamma=gamma)
    df_def_top_tier.to_csv(DCS_DIR / "def_tier_player_rotations.csv", index=False)

    top_gkps = df_gkp_strat[df_gkp_strat["horizon"] == "gw1_19"].sort_values("dcs", ascending=False).head(15)
    top_defs = df_def_top_tier[df_def_top_tier["horizon"] == "gw1_19"].sort_values("dcs", ascending=False).head(30)
    rows = []
    for _, gkp in top_gkps.iterrows():
        for _, d in top_defs.iterrows():
            tot_price = gkp["total_price"] + d["total_price"]
            if tot_price > _DCS.MAX_BACKLINE_TOTAL_PRICE:
                continue
            tot_rot_xp = gkp["tot_rot_xp"] + d["tot_rot_xp"]
            dcs, oc_score, s_risk = _DCS.compute_two_factor_dcs(
                rot_xp_per_gw=tot_rot_xp / 19.0,
                total_price=tot_price,
                floor_price=28.5,
                rot_avg_fdr=(gkp["rot_avg_fdr"] + 3.0 * d["rot_avg_fdr"]) / 4.0,
                no_diff_pct=(gkp["no_diff_pct"] + d["no_diff_pct"]) / 2.0,
                fdr_corr=(gkp["fdr_corr"] + d["avg_fdr_corr"]) / 2.0,
                min_xp_bound=12.0,
                max_xp_bound=27.0,
                gamma=gamma,
            )
            rows.append({
                "horizon": "gw1_19",
                "dcs": dcs,
                "oc_score": oc_score,
                "s_risk": s_risk,
                "tot_rot_xp": round(tot_rot_xp, 2),
                "rot_avg_fdr": round((gkp["rot_avg_fdr"] + 3.0 * d["rot_avg_fdr"]) / 4.0, 2),
                "gkp_pairing": gkp["pairing"],
                "def_lineup": d["lineup"],
                "total_price": tot_price,
            })
    pd.DataFrame(rows).sort_values("dcs", ascending=False).drop_duplicates(subset=["gkp_pairing", "def_lineup"]).head(100).to_csv(
        DCS_DIR / "backline_gw1_19_lineups.csv", index=False
    )
    print(f"Dual-Vector DCS written to {DCS_DIR}")
    print(df_gkp_strat[df_gkp_strat["horizon"] == "gw1_19"].sort_values("dcs", ascending=False).head(5)[["pairing", "dcs", "tot_rot_xp", "rot_avg_fdr"]].to_string(index=False))


if __name__ == "__main__":
    run_dual_vector_dcs()
