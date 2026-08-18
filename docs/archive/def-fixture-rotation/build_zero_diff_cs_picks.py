"""Build unordered 5-club zero-diff all-easy + CS-gate pick CSVs.

Horizons: gw1_3 (3-start), bb2 (11-start sprint), gw4_19.
Filter 100% zero-diff, 5 unique clubs. Sort all_easy desc, avg_fdr_corr asc.
CS gate: n_cs_plus >= 2 and n_prom <= 1.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "archive" / "def-fixture-rotation"
MATRIX = OUT / "def_club_5way_rotation_matrix.csv"
BB2_MATRIX = OUT / "def_bb2_wc4_club_matrix.csv"
PRIORS = OUT / "def_club_cs_priors.csv"

ELITE = {"ARS", "MCI"}
STRONG = {"LIV", "BHA", "MUN", "AVL"}
WEAK = {"CRY", "NEW", "BOU", "CHE", "LEE"}
PROMOTED = {"COV", "HUL", "IPS"}
CS_CORE = ELITE | STRONG


def xcs(lam: float) -> float:
    return float(np.exp(-float(lam)))


def canon(s: str) -> str:
    return "-".join(sorted(str(s).split("-")))


def load_priors() -> tuple[dict[str, float], dict[str, float]]:
    priors = pd.read_csv(PRIORS)
    return (
        dict(zip(priors["club_short"], priors["gkp_per90_goals_conceded"])),
        dict(zip(priors["club_short"], priors["def_median_per90_goals_conceded"])),
    )


def score_combo(combo: str, gkp_l: dict[str, float], def_l: dict[str, float]) -> dict:
    clubs = combo.split("-")
    n_elite = sum(c in ELITE for c in clubs)
    n_strong = sum(c in STRONG for c in clubs)
    n_prom = sum(c in PROMOTED for c in clubs)
    n_weak = sum(c in WEAK for c in clubs)
    n_cs_plus = n_elite + n_strong
    fail: list[str] = []
    if n_cs_plus < 2:
        fail.append("thin CS core")
    if n_prom >= 2:
        fail.append("2+ promoted")
    if n_cs_plus >= 3 or (n_elite >= 1 and n_cs_plus >= 2 and n_prom == 0):
        verd = "PICK"
    elif n_prom == 0 and n_cs_plus >= 2:
        verd = "SOLID"
    else:
        verd = "CAUTION"
    return {
        "mean_gkp_xcs": round(float(np.mean([xcs(gkp_l[c]) for c in clubs])), 4),
        "mean_def_xcs": round(float(np.mean([xcs(def_l[c]) for c in clubs])), 4),
        "n_elite": n_elite,
        "n_strong": n_strong,
        "n_cs_plus": n_cs_plus,
        "n_prom": n_prom,
        "n_weak": n_weak,
        "cs_core": "-".join(c for c in clubs if c in CS_CORE),
        "leaks": "-".join(c for c in clubs if c in WEAK | PROMOTED),
        "cs_gate_pass": n_cs_plus >= 2 and n_prom <= 1,
        "fail": "; ".join(fail),
        "verdict": verd,
    }


def rank_and_write(
    df: pd.DataFrame,
    *,
    horizon: str,
    n_gws: int,
    rot_col: str,
    head_min_easy: int | None,
    out_name: str,
    gkp_l: dict[str, float],
    def_l: dict[str, float],
) -> None:
    g = df.copy()
    g["combo"] = g["clubs"].map(canon)
    if g["combo"].nunique() != len(g):
        raise ValueError(f"{horizon}: duplicate unordered sets")
    sc = g["combo"].apply(lambda c: pd.Series(score_combo(c, gkp_l, def_l)))
    g = pd.concat([g.reset_index(drop=True), sc.reset_index(drop=True)], axis=1)
    g = g.sort_values(["all_easy_gws", "avg_fdr_corr"], ascending=[False, True]).reset_index(drop=True)
    g["fix_rank"] = np.arange(1, len(g) + 1)
    g["all_easy_gws"] = g["all_easy_gws"].astype(int)
    g["no_diff_gws"] = g["no_diff_gws"].astype(int)
    g["all_easy_pct"] = (g["all_easy_gws"] / float(n_gws) * 100.0).round(1)
    if head_min_easy is None:
        head = g[g["all_easy_gws"] == int(g["all_easy_gws"].max())].copy()
    else:
        head = g[g["all_easy_gws"] >= head_min_easy].copy()
    head["list"] = f"{horizon}_fixture_head"
    head["pick"] = ""
    head["gate"] = np.where(head["cs_gate_pass"], "pass", "cut")
    passed = g[g["cs_gate_pass"]].head(20).copy()
    passed["pick"] = [str(i) for i in range(1, len(passed) + 1)]
    passed["list"] = f"{horizon}_final20"
    passed["gate"] = "pass"
    if rot_col != "rot_avg_fdr":
        head = head.rename(columns={rot_col: "rot_avg_fdr"})
        passed = passed.rename(columns={rot_col: "rot_avg_fdr"})
    cols = [
        "list", "pick", "fix_rank", "combo", "allocation_pattern", "all_easy_gws", "all_easy_pct",
        "avg_fdr_corr", "rot_avg_fdr", "no_diff_gws", "mean_gkp_xcs", "mean_def_xcs",
        "n_elite", "n_strong", "n_cs_plus", "n_prom", "n_weak", "cs_core", "leaks", "gate", "fail", "verdict",
    ]
    pd.concat([head[cols], passed[cols]], ignore_index=True).to_csv(OUT / out_name, index=False)


def annotate_bb2(bb2: pd.DataFrame) -> pd.DataFrame:
    fixtures = pd.read_parquet(ROOT / "data" / "processed" / "fixtures.parquet")
    clubs = pd.read_parquet(ROOT / "data" / "processed" / "clubs.parquet")
    club_ids = sorted(list(clubs["id"]))
    id_to_idx = {cid: idx for idx, cid in enumerate(club_ids)}
    idx_to_short = {idx: clubs.loc[clubs["id"] == cid, "short_name"].values[0] for cid, idx in id_to_idx.items()}
    short_to_idx = {v: k for k, v in idx_to_short.items()}
    fdr_mat = np.full((len(club_ids), 38), 3.0, dtype=float)
    for _, f in fixtures.iterrows():
        gw = int(f["gameweek_id"]) - 1
        fdr_mat[id_to_idx[int(f["home_club_id"])], gw] = float(f["team_h_difficulty"])
        fdr_mat[id_to_idx[int(f["away_club_id"])], gw] = float(f["team_a_difficulty"])

    def flags(combo: str) -> pd.Series:
        idxs = [short_to_idx[c] for c in combo.split("-")]
        gw2 = fdr_mat[idxs, 1]
        gw1_top3 = np.sort(fdr_mat[idxs, 0])[:3]
        gw3_top3 = np.sort(fdr_mat[idxs, 2])[:3]
        worst = np.array([gw1_top3[-1], gw2.max(), gw3_top3[-1]])
        return pd.Series({"no_diff_gws": int((worst <= 3.0).sum()), "all_easy_gws": int((worst <= 2.0).sum())})

    bb2 = bb2.copy()
    bb2["combo"] = bb2["clubs"].map(canon)
    fl = bb2["combo"].apply(flags)
    return pd.concat([bb2.reset_index(drop=True), fl.reset_index(drop=True)], axis=1)


def main() -> None:
    gkp_l, def_l = load_priors()
    mat = pd.read_csv(MATRIX)
    rank_and_write(
        mat[(mat["horizon"] == "gw1_3") & (mat["num_unique_clubs"] == 5) & (mat["no_diff_gws"] == 3)],
        horizon="gw1_3", n_gws=3, rot_col="rot_avg_fdr", head_min_easy=2,
        out_name="def_gw1_3_zero_diff_cs_picks.csv", gkp_l=gkp_l, def_l=def_l,
    )
    rank_and_write(
        mat[(mat["horizon"] == "gw4_19") & (mat["num_unique_clubs"] == 5) & (mat["no_diff_gws"] == 16)],
        horizon="gw4_19", n_gws=16, rot_col="rot_avg_fdr", head_min_easy=5,
        out_name="def_gw4_19_zero_diff_cs_picks.csv", gkp_l=gkp_l, def_l=def_l,
    )
    bb2 = annotate_bb2(pd.read_csv(BB2_MATRIX))
    bb2 = bb2[(bb2["num_unique_clubs"] == 5) & (bb2["no_diff_gws"] == 3)].assign(clubs=lambda d: d["combo"])
    rank_and_write(
        bb2, horizon="bb2", n_gws=3, rot_col="effective_avg_fdr", head_min_easy=None,
        out_name="def_bb2_zero_diff_cs_picks.csv", gkp_l=gkp_l, def_l=def_l,
    )


if __name__ == "__main__":
    main()
