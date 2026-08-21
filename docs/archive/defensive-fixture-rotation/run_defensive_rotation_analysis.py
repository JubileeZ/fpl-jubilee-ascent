"""Unified Defensive Architecture, Strategy & Fixture Rotation Analysis.

Consolidates Goalkeeper (GKP) and Defender (DEF) fixture diversification and strategy:
1. Two-Factor Scoring Model:
   - Factor 1: Score (Rotated xP & Opportunity-Cost Adjusted Net Score / OC-Score)
   - Factor 2: Combination Risk Management (Zero-Difficult %, Rotated FDR, Schedule Correlation)
   - Composite Metric: Defensive Composite Score (DCS = 0.60 * Score + 0.40 * Risk)
2. Stage 1: Goalkeeper Strategy Proof (Active 2-GKP Rotation vs Budget S&F vs Premium S&F)
3. Stage 2: Multi-Club (2 to 5 unique clubs) 5-DEF Combinations (Enforcing Max 2 DEF per club)
4. Stage 3: Full Backline (2 GKP + 5 DEF) Simulation across GW1-3 (BB1), GW4-19 (WC4), and GW1-19.
"""

from __future__ import annotations

import importlib.util
import itertools
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from clients.env_loader import configure_utf8_stdio
from features.builder import _fixture_maps
from models.participation_state_hybrid import ParticipationStateHybridModel

_SEED_SPEC = importlib.util.spec_from_file_location(
    "dual_vector_seed_dcs",
    PROJECT_ROOT / "docs/archive/gw1-19-first-half-chip-path/build_dual_vector_seed.py",
)
_SEED_MOD = importlib.util.module_from_spec(_SEED_SPEC)
assert _SEED_SPEC.loader is not None
_SEED_SPEC.loader.exec_module(_SEED_MOD)

DATA_DIR = PROJECT_ROOT / "data" / "processed"
RESEARCH_DIR = PROJECT_ROOT / "docs" / "archive"
OUT_DIR = RESEARCH_DIR / "defensive-fixture-rotation"
STATS_CSV = RESEARCH_DIR / "gw1-6-preseason-pipeline" / "02-expected-stats-gw1-5" / "expected-stats-gw1-5.csv"
ROLE_CSV = RESEARCH_DIR / "gw1-6-preseason-pipeline" / "01-expected-role-gw1-5" / "expected-role-gw1-5.csv"

DRAFT_ROLES = ("Nailed Starter", "Regular Starter")
PROMOTED_CLUBS = frozenset({"COV", "HUL", "IPS"})
FLAT_START_MINUTES = 90.0
GKP_POSITION_ID = 1
DEF_POSITION_ID = 2

# Global rule: Max 2 DEF per club across all 20 clubs
MAX_DEF_PER_CLUB = 2
MAX_DEF_TOTAL_PRICE = 26.0
MAX_BACKLINE_TOTAL_PRICE = 36.0

HORIZONS = (
    ("gw1_3", 1, 3),
    ("gw4_19", 4, 19),
    ("gw1_19", 1, 19),
    ("full_season", 1, 38),
)


def compute_outfield_capital_slope(
    stats_csv: Path = STATS_CSV,
    players_parquet: Path = DATA_DIR / "players.parquet",
) -> float:
    """Compute empirical marginal xP per £1.0m per GW across drafted MID/FWD assets."""
    if not stats_csv.exists() or not players_parquet.exists():
        return 0.25
    df_stats = pd.read_csv(stats_csv)
    players = pd.read_parquet(players_parquet)
    cost_map = players.set_index("id")["now_cost"] / 10.0
    df_stats["price"] = df_stats["player_id"].map(cost_map)
    outfield = df_stats[
        df_stats["position"].isin(["MID", "FWD"])
        & (df_stats["expected_role"].isin(DRAFT_ROLES))
        & (df_stats["price"] >= 4.5)
        & (df_stats["price"] <= 15.5)
    ].dropna(subset=["price"])
    if len(outfield) < 10:
        return 0.25
    xg = outfield["per90_xg"].fillna(0.0)
    xa = outfield["per90_xa"].fillna(0.0)
    defcon = outfield.get("per90_defensive_contribution", outfield.get("per90_defcon", 7.0)).fillna(0.0)
    p_start = outfield["p_start"].fillna(0.75)
    est_gw_xp = p_start * (xg * 4.5 + xa * 3.0 + defcon * 0.15 + 2.0)
    slope, _ = np.polyfit(outfield["price"], est_gw_xp, 1)
    return float(max(0.15, min(0.60, slope)))


def compute_two_factor_dcs(
    *,
    rot_xp_per_gw: float,
    total_price: float,
    floor_price: float,
    rot_avg_fdr: float,
    no_diff_pct: float,
    fdr_corr: float,
    min_xp_bound: float,
    max_xp_bound: float,
    gamma: float = 0.25,
) -> tuple[float, float, float]:
    """Compute Two-Factor Defensive Composite Score (DCS), Opportunity-Cost Score, and Risk Score."""
    oc_score = rot_xp_per_gw - gamma * (total_price - floor_price)
    s_score = float(np.clip((oc_score - min_xp_bound) / (max_xp_bound - min_xp_bound) * 100.0, 0, 100))

    s_no_diff = float(np.clip(no_diff_pct, 0, 100))
    s_rot_fdr = float(np.clip((3.5 - rot_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100))
    s_corr = float(np.clip((-fdr_corr + 1.0) / 2.0 * 100.0, 0, 100))
    s_risk = 0.50 * s_no_diff + 0.35 * s_rot_fdr + 0.15 * s_corr

    dcs = round(0.60 * s_score + 0.40 * s_risk, 2)
    return dcs, round(oc_score, 3), round(s_risk, 2)


def build_club_fdr_matrix(fixtures: pd.DataFrame, clubs: pd.DataFrame) -> tuple[np.ndarray, dict[int, str], dict[int, int]]:
    """Build (20, 38) FDR matrix and mappings."""
    club_ids = sorted(list(clubs["id"]))
    id_to_idx = {cid: idx for idx, cid in enumerate(club_ids)}
    idx_to_short = {idx: clubs.loc[clubs["id"] == cid, "short_name"].values[0] for cid, idx in id_to_idx.items()}

    fdr_mat = np.full((len(club_ids), 38), 3.0, dtype=float)

    for _, f in fixtures.iterrows():
        gw = int(f["gameweek_id"]) - 1
        h_id, a_id = int(f["home_club_id"]), int(f["away_club_id"])
        h_idx, a_idx = id_to_idx[h_id], id_to_idx[a_id]
        fdr_mat[h_idx, gw] = float(f["team_h_difficulty"])
        fdr_mat[a_idx, gw] = float(f["team_a_difficulty"])

    return fdr_mat, idx_to_short, id_to_idx


def build_seed_fdr_matrix(
    fmap: pd.DataFrame, clubs: pd.DataFrame, n_gw: int = 38
) -> tuple[np.ndarray, dict[int, str], dict[int, int]]:
    """Effective FDR = defence_multiplier × 3 on Prior-Season Dual-Vector Seed clubs."""
    club_ids = sorted(clubs["id"].tolist())
    id_to_idx = {cid: i for i, cid in enumerate(club_ids)}
    idx_to_short = {
        i: str(clubs.loc[clubs["id"] == cid, "short_name"].iloc[0]) for cid, i in id_to_idx.items()
    }
    fdr_mat = np.full((len(club_ids), n_gw), 3.0, dtype=float)
    for _, row in fmap.iterrows():
        gw = int(row["gameweek_id"])
        if gw < 1 or gw > n_gw:
            continue
        idx = id_to_idx[int(row["club_id"])]
        fdr_mat[idx, gw - 1] = float(np.clip(float(row["defence_multiplier"]) * 3.0, 1.2, 5.4))
    return fdr_mat, idx_to_short, id_to_idx


def precompute_pairwise_corr(fdr_mat_sub: np.ndarray) -> np.ndarray:
    """Precompute 20x20 pairwise correlation matrix for a given gameweek slice."""
    n_clubs = fdr_mat_sub.shape[0]
    corr_mat = np.eye(n_clubs, dtype=float)
    for i in range(n_clubs):
        for j in range(i + 1, n_clubs):
            s1, s2 = fdr_mat_sub[i], fdr_mat_sub[j]
            std1, std2 = np.std(s1), np.std(s2)
            if std1 > 1e-6 and std2 > 1e-6:
                r = np.corrcoef(s1, s2)[0, 1]
                if not np.isnan(r):
                    corr_mat[i, j] = r
                    corr_mat[j, i] = r
    return corr_mat


def project_starter_grid(
    starters: pd.DataFrame,
    fmap: pd.DataFrame,
    pos_str: str,
    pos_id: int,
    end_gw: int = 38,
) -> pd.DataFrame:
    """Project weekly xP via ParticipationStateHybridModel with flat starter minutes."""
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
                    "position": pos_str,
                    "position_id": pos_id,
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
                    "per90_xg": float(player.get("per90_xg", 0.0)),
                    "per90_xa": float(player.get("per90_xa", 0.0)),
                    "per90_defensive_contribution": float(
                        player.get("per90_defensive_contribution", player.get("per90_defcon", 7.0 if pos_str == "DEF" else 0.0))
                    ),
                    "per90_saves": float(player.get("per90_saves", 0.0)),
                    "per90_goals_conceded": float(player.get("per90_goals_conceded", 1.30)),
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

    agg_dict = {
        "projected_points": ("projected_points", "sum"),
        "web_name": ("web_name", "first"),
        "club_short": ("club_short", "first"),
        "club_id": ("club_id", "first"),
        "expected_role": ("expected_role", "first"),
        "price": ("price", "first"),
        "per90_goals_conceded": ("per90_goals_conceded", "first"),
    }
    if pos_str == "GKP":
        agg_dict["per90_saves"] = ("per90_saves", "first")
    else:
        agg_dict["per90_xg"] = ("per90_xg", "first")
        agg_dict["per90_xa"] = ("per90_xa", "first")
        agg_dict["per90_defcon"] = ("per90_defensive_contribution", "first")

    return merged.groupby(["player_id", "gameweek_id"], as_index=False).agg(**agg_dict)


# =============================================================================
# STAGE 1: GKP STRATEGY EVALUATION & PAIRS ROTATION
# =============================================================================

def run_gkp_strategy_analysis(
    starters: pd.DataFrame,
    gw_xp: pd.DataFrame,
    fdr_mat: np.ndarray,
    id_to_idx: dict[int, int],
    gamma: float = 0.25,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate GKP strategy archetypes and pairwise rotations."""
    xp_lookup = {
        int(pid): grp.set_index("gameweek_id")["projected_points"].to_dict()
        for pid, grp in gw_xp.groupby("player_id")
    }
    gc_lookup = starters.set_index("player_id")["per90_goals_conceded"].to_dict()

    pids = list(starters["player_id"])
    n_gk = len(pids)

    # 1. Evaluate all single starter set-and-forget options (paired with £4.0m fodder -> Total Spend = price + 4.0)
    single_rows: list[dict] = []
    for pid in pids:
        p_row = starters[starters["player_id"] == pid].iloc[0]
        cid = id_to_idx[int(p_row["club_id"])]
        price = float(p_row["price"])
        tot_price = price + 4.0
        gc = float(gc_lookup[pid])
        name = p_row["web_name"]
        club = p_row["club_short"]

        strategy_cat = "Premium Set & Forget" if price >= 5.5 else ("Mid-Value Set & Forget" if price == 5.0 else "Budget Set & Forget")

        for h_name, start_gw, end_gw in HORIZONS:
            gws = list(range(start_gw, end_gw + 1))
            n_gws = len(gws)
            p_xp = np.array([xp_lookup[pid][gw] for gw in gws])
            p_fdr = np.array([fdr_mat[cid, gw - 1] for gw in gws])
            def_mult = p_fdr / 3.0
            p_cs = np.exp(-gc * def_mult)

            tot_xp = float(p_xp.sum())
            rot_xp_per_gw = tot_xp / n_gws
            rot_avg_fdr = float(p_fdr.mean())
            no_diff_pct = float(np.sum(p_fdr <= 3.0) / n_gws * 100.0)
            all_easy_pct = float(np.sum(p_fdr <= 2.0) / n_gws * 100.0)
            exp_cs = float(p_cs.sum())

            dcs, oc_score, s_risk = compute_two_factor_dcs(
                rot_xp_per_gw=rot_xp_per_gw,
                total_price=tot_price,
                floor_price=8.5,
                rot_avg_fdr=rot_avg_fdr,
                no_diff_pct=no_diff_pct,
                fdr_corr=1.0,
                min_xp_bound=3.0,
                max_xp_bound=6.5,
                gamma=gamma,
            )

            single_rows.append(
                {
                    "horizon": h_name,
                    "strategy": strategy_cat,
                    "type": "Single S&F",
                    "pairing": f"{name} ({club}) + Fodder (£4.0m)",
                    "gkp1": name,
                    "club1": club,
                    "price1": price,
                    "gkp2": "Fodder",
                    "club2": "-",
                    "price2": 4.0,
                    "total_price": tot_price,
                    "num_gws": n_gws,
                    "tot_rot_xp": round(tot_xp, 2),
                    "rot_xp_per_gw": round(rot_xp_per_gw, 2),
                    "oc_score": oc_score,
                    "dcs": dcs,
                    "s_risk": s_risk,
                    "rot_avg_fdr": round(rot_avg_fdr, 2),
                    "no_diff_pct": round(no_diff_pct, 1),
                    "all_easy_pct": round(all_easy_pct, 1),
                    "fdr_corr": 1.0,
                    "foi": round(float((1.0 - p_cs).mean()), 4),
                    "expected_cs": round(exp_cs, 2),
                }
            )

    # 2. Evaluate all pairwise active rotations
    pair_rows: list[dict] = []
    for i in range(n_gk):
        for j in range(i + 1, n_gk):
            pid1, pid2 = pids[i], pids[j]
            p1 = starters[starters["player_id"] == pid1].iloc[0]
            p2 = starters[starters["player_id"] == pid2].iloc[0]
            cid1, cid2 = id_to_idx[int(p1["club_id"])], id_to_idx[int(p2["club_id"])]
            price1, price2 = float(p1["price"]), float(p2["price"])
            tot_price = price1 + price2
            if tot_price > 10.0:  # Cap at £10.0m for realistic GKP spend
                continue
            gc1, gc2 = float(gc_lookup[pid1]), float(gc_lookup[pid2])
            name1, name2 = p1["web_name"], p2["web_name"]
            club1, club2 = p1["club_short"], p2["club_short"]

            strategy_cat = "Active 2-GKP Rotation"

            for h_name, start_gw, end_gw in HORIZONS:
                gws = list(range(start_gw, end_gw + 1))
                n_gws = len(gws)
                xp1 = np.array([xp_lookup[pid1][gw] for gw in gws])
                xp2 = np.array([xp_lookup[pid2][gw] for gw in gws])
                fdr1 = np.array([fdr_mat[cid1, gw - 1] for gw in gws])
                fdr2 = np.array([fdr_mat[cid2, gw - 1] for gw in gws])

                def_mult1 = fdr1 / 3.0
                def_mult2 = fdr2 / 3.0
                p_cs1 = np.exp(-gc1 * def_mult1)
                p_cs2 = np.exp(-gc2 * def_mult2)

                # Special GW1 Bench Boost sprint logic for GW1-3:
                # In GW1: both GKPs start (BB active); GW2-3: best 1 starts
                if h_name == "gw1_3":
                    gw1_xp_tot = xp1[0] + xp2[0]
                    gw2_xp = max(xp1[1], xp2[1])
                    gw3_xp = max(xp1[2], xp2[2])
                    tot_xp = float(gw1_xp_tot + gw2_xp + gw3_xp)
                    rot_xp_per_gw = tot_xp / 3.0
                    rot_avg_fdr = float((fdr1[0] + fdr2[0] + min(fdr1[1], fdr2[1]) + min(fdr1[2], fdr2[2])) / 4.0)
                    no_diff_pct = float(((fdr1[0] <= 3.0 and fdr2[0] <= 3.0) + (min(fdr1[1], fdr2[1]) <= 3.0) + (min(fdr1[2], fdr2[2]) <= 3.0)) / 3.0 * 100.0)
                    all_easy_pct = float(((fdr1[0] <= 2.0 and fdr2[0] <= 2.0) + (min(fdr1[1], fdr2[1]) <= 2.0) + (min(fdr1[2], fdr2[2]) <= 2.0)) / 3.0 * 100.0)
                    exp_cs = float(p_cs1[0] + p_cs2[0] + (p_cs1[1] if xp1[1] >= xp2[1] else p_cs2[1]) + (p_cs1[2] if xp1[2] >= xp2[2] else p_cs2[2]))
                else:
                    max_xp_picks = np.maximum(xp1, xp2)
                    tot_xp = float(max_xp_picks.sum())
                    rot_xp_per_gw = tot_xp / n_gws
                    rot_fdr = np.minimum(fdr1, fdr2)
                    rot_avg_fdr = float(rot_fdr.mean())
                    no_diff_pct = float(np.sum(rot_fdr <= 3.0) / n_gws * 100.0)
                    all_easy_pct = float(np.sum(rot_fdr <= 2.0) / n_gws * 100.0)
                    p_cs_rot = np.where(xp1 >= xp2, p_cs1, p_cs2)
                    exp_cs = float(p_cs_rot.sum())

                # FOI and correlation
                foi = float(((1.0 - p_cs1) * (1.0 - p_cs2)).mean())
                std1, std2 = np.std(fdr1), np.std(fdr2)
                fdr_corr = float(np.corrcoef(fdr1, fdr2)[0, 1]) if (std1 > 1e-6 and std2 > 1e-6) else 0.0
                if np.isnan(fdr_corr):
                    fdr_corr = 0.0

                dcs, oc_score, s_risk = compute_two_factor_dcs(
                    rot_xp_per_gw=rot_xp_per_gw,
                    total_price=tot_price,
                    floor_price=8.5,
                    rot_avg_fdr=rot_avg_fdr,
                    no_diff_pct=no_diff_pct,
                    fdr_corr=fdr_corr,
                    min_xp_bound=3.0,
                    max_xp_bound=6.5,
                    gamma=gamma,
                )

                row = {
                    "horizon": h_name,
                    "strategy": strategy_cat,
                    "type": "Active 2-GKP",
                    "pairing": f"{name1} ({club1}) + {name2} ({club2})",
                    "gkp1": name1,
                    "club1": club1,
                    "price1": price1,
                    "gkp2": name2,
                    "club2": club2,
                    "price2": price2,
                    "total_price": tot_price,
                    "num_gws": n_gws,
                    "tot_rot_xp": round(tot_xp, 2),
                    "rot_xp_per_gw": round(rot_xp_per_gw, 2),
                    "oc_score": oc_score,
                    "dcs": dcs,
                    "s_risk": s_risk,
                    "rot_avg_fdr": round(rot_avg_fdr, 2),
                    "no_diff_pct": round(no_diff_pct, 1),
                    "all_easy_pct": round(all_easy_pct, 1),
                    "fdr_corr": round(fdr_corr, 4),
                    "foi": round(foi, 4),
                    "expected_cs": round(exp_cs, 2),
                }
                pair_rows.append(row)
                single_rows.append(row)

    df_strategy = pd.DataFrame(single_rows)
    df_pairs = pd.DataFrame(pair_rows)
    return df_strategy, df_pairs


# =============================================================================
# STAGE 2: MULTI-CLUB (2-5 UNIQUE TEAMS) 5-DEF COMBINATORIAL ANALYSIS
# =============================================================================

def generate_valid_def_club_multisets(idx_to_short: dict[int, str]) -> tuple[np.ndarray, list[str], list[int], list[str]]:
    """Generate all valid 5-club multisets enforcing MAX 2 DEF per club across all 20 clubs."""
    all_combos = list(itertools.combinations_with_replacement(range(20), 5))
    valid_combos = []
    patterns = []
    num_uniques = []
    club_names = []
    for c in all_combos:
        counts = Counter(c)
        # Enforce max 2 from ANY club
        if max(counts.values()) <= MAX_DEF_PER_CLUB:
            valid_combos.append(c)
            p_tup = tuple(sorted(counts.values(), reverse=True))
            patterns.append("+".join(str(x) for x in p_tup))
            num_uniques.append(len(p_tup))
            club_names.append("-".join(idx_to_short[x] for x in c))
    return np.array(valid_combos, dtype=np.int32), patterns, num_uniques, club_names


def run_def_club_combinatorial_analysis(fdr_mat: np.ndarray, idx_to_short: dict[int, str]) -> pd.DataFrame:
    """Evaluate 5-DEF club multisets across horizons."""
    valid_combos, patterns, num_uniques, club_names = generate_valid_def_club_multisets(idx_to_short)
    pair_indices = list(itertools.combinations(range(5), 2))
    all_rows: list[dict] = []

    for h_name, start_gw, end_gw in HORIZONS:
        gw_indices = list(range(start_gw - 1, end_gw))
        n_gws = len(gw_indices)
        h_fdr = fdr_mat[:, gw_indices]
        corr_mat = precompute_pairwise_corr(h_fdr)

        combo_fdr = h_fdr[valid_combos]  # (N_combos, 5, n_gws)
        sorted_fdr = np.sort(combo_fdr, axis=1)
        top3_fdr = sorted_fdr[:, :3, :]  # 3 starting defenders
        rot_avg_fdr = top3_fdr.mean(axis=(1, 2))
        worst_starters = sorted_fdr[:, 2, :]
        max_worst_starter = worst_starters.max(axis=1)
        no_diff_gws = (worst_starters <= 3.0).sum(axis=1)
        no_diff_pct = no_diff_gws / float(n_gws) * 100.0
        all_easy_gws = (worst_starters <= 2.0).sum(axis=1)
        all_easy_pct = all_easy_gws / float(n_gws) * 100.0

        for i in range(len(valid_combos)):
            c = valid_combos[i]
            corrs = [corr_mat[c[a], c[b]] for a, b in pair_indices]
            avg_corr = float(np.mean(corrs)) if corrs else 0.0

            all_rows.append(
                {
                    "horizon": h_name,
                    "start_gw": start_gw,
                    "end_gw": end_gw,
                    "num_gws": n_gws,
                    "num_unique_clubs": num_uniques[i],
                    "allocation_pattern": patterns[i],
                    "clubs": club_names[i],
                    "club1": idx_to_short[c[0]],
                    "club2": idx_to_short[c[1]],
                    "club3": idx_to_short[c[2]],
                    "club4": idx_to_short[c[3]],
                    "club5": idx_to_short[c[4]],
                    "rot_avg_fdr": round(float(rot_avg_fdr[i]), 4),
                    "max_worst_starter": round(float(max_worst_starter[i]), 1),
                    "no_diff_gws": int(no_diff_gws[i]),
                    "no_diff_pct": round(float(no_diff_pct[i]), 1),
                    "all_easy_gws": int(all_easy_gws[i]),
                    "all_easy_pct": round(float(all_easy_pct[i]), 1),
                    "avg_fdr_corr": round(avg_corr, 4),
                }
            )

    return pd.DataFrame(all_rows)


def run_bb1_wc4_club_analysis(
    fdr_mat: np.ndarray,
    idx_to_short: dict[int, str],
    fixtures: pd.DataFrame,
    id_to_idx: dict[int, int],
) -> pd.DataFrame:
    """Evaluate non-clashing BB1 + WC4 5-club sets across GW1-3."""
    gw1_f = fixtures[fixtures["gameweek_id"] == 1]
    clash_pairs = set()
    for _, f in gw1_f.iterrows():
        h_idx = id_to_idx[int(f["home_club_id"])]
        a_idx = id_to_idx[int(f["away_club_id"])]
        clash_pairs.add(frozenset([h_idx, a_idx]))

    valid_combos, patterns, num_uniques, club_names = generate_valid_def_club_multisets(idx_to_short)
    pair_indices = list(itertools.combinations(range(5), 2))
    corr_mat = precompute_pairwise_corr(fdr_mat[:, 0:3])

    rows: list[dict] = []
    for i, c in enumerate(valid_combos):
        has_clash = any(frozenset([c[a], c[b]]) in clash_pairs for a in range(5) for b in range(a + 1, 5) if c[a] != c[b])
        if has_clash:
            continue

        # GW1: all 5 start on Bench Boost
        gw1_fdrs = fdr_mat[c, 0]
        gw1_max_fdr = float(gw1_fdrs.max())
        if gw1_max_fdr > 3.0:  # Strict ceiling rule
            continue
        gw1_avg_fdr = float(gw1_fdrs.mean())

        # GW2 and GW3: top 3 start
        gw2_fdrs = np.sort(fdr_mat[c, 1])[:3]
        gw3_fdrs = np.sort(fdr_mat[c, 2])[:3]
        gw2_avg_fdr = float(gw2_fdrs.mean())
        gw3_avg_fdr = float(gw3_fdrs.mean())
        gw2_3_rot_fdr = float((gw2_fdrs.sum() + gw3_fdrs.sum()) / 6.0)

        tot_effective_fdr = float(gw1_fdrs.sum() + gw2_fdrs.sum() + gw3_fdrs.sum())
        effective_avg_fdr = tot_effective_fdr / 11.0

        corrs = [corr_mat[c[a], c[b]] for a, b in pair_indices]
        avg_corr = float(np.mean(corrs)) if corrs else 0.0

        rows.append(
            {
                "num_unique_clubs": num_uniques[i],
                "allocation_pattern": patterns[i],
                "clubs": club_names[i],
                "club1": idx_to_short[c[0]],
                "club2": idx_to_short[c[1]],
                "club3": idx_to_short[c[2]],
                "club4": idx_to_short[c[3]],
                "club5": idx_to_short[c[4]],
                "gw1_avg_fdr": round(gw1_avg_fdr, 2),
                "gw1_max_fdr": round(gw1_max_fdr, 1),
                "gw2_avg_fdr": round(gw2_avg_fdr, 2),
                "gw3_avg_fdr": round(gw3_avg_fdr, 2),
                "gw2_3_rot_fdr": round(gw2_3_rot_fdr, 2),
                "effective_avg_fdr": round(effective_avg_fdr, 4),
                "avg_fdr_corr": round(avg_corr, 4),
            }
        )

    return pd.DataFrame(rows)


def simulate_def_tier_player_rotations(
    starters: pd.DataFrame,
    gw_xp: pd.DataFrame,
    fdr_mat: np.ndarray,
    id_to_idx: dict[int, int],
    gamma: float = 0.25,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate 5-DEF combinations across flexible budget spectrum up to £26.0m."""
    xp_lookup = {
        int(pid): grp.set_index("gameweek_id")["projected_points"].to_dict()
        for pid, grp in gw_xp.groupby("player_id")
    }

    # Select representative defenders per club and price point
    rep_defs_list = []
    for (_, _), grp in starters.groupby(["club_short", "price"]):
        best = grp.sort_values(["per90_xg", "per90_defcon", "per90_xa"], ascending=[False, False, False]).iloc[0]
        rep_defs_list.append(best)
    df_rep = pd.DataFrame(rep_defs_list)

    player_meta = df_rep.set_index("player_id").to_dict("index")
    pids = list(player_meta.keys())
    n_players = len(pids)

    p_prices = np.array([player_meta[pid]["price"] for pid in pids], dtype=np.float32)
    p_cids = np.array([id_to_idx[int(player_meta[pid]["club_id"])] for pid in pids], dtype=np.int32)
    p_all_fdrs = np.array([fdr_mat[cid, :] for cid in p_cids], dtype=np.float32)
    p_all_xps = np.array(
        [[float(xp_lookup[pid].get(gw, 0.0)) for gw in range(1, 39)] for pid in pids],
        dtype=np.float32,
    )

    all_5combos = np.array(list(itertools.combinations(range(n_players), 5)), dtype=np.int32)
    combo_prices = p_prices[all_5combos].sum(axis=1)
    combo_cids = p_cids[all_5combos]

    valid_indices = []
    patterns = []
    num_uniques = []
    for i in range(len(all_5combos)):
        if combo_prices[i] > MAX_DEF_TOTAL_PRICE:
            continue
        c_counts = Counter(combo_cids[i])
        if max(c_counts.values()) <= MAX_DEF_PER_CLUB:
            valid_indices.append(i)
            p_tup = tuple(sorted(c_counts.values(), reverse=True))
            patterns.append("+".join(str(x) for x in p_tup))
            num_uniques.append(len(p_tup))

    valid_indices = np.array(valid_indices, dtype=np.int32)
    valid_5combos = all_5combos[valid_indices]
    valid_prices = combo_prices[valid_indices]
    valid_cids = combo_cids[valid_indices]
    patterns_arr = np.array(patterns)
    num_uniques_arr = np.array(num_uniques, dtype=np.int32)

    n_valid = len(valid_5combos)
    tier_rows: list[dict] = []
    pair_indices = list(itertools.combinations(range(5), 2))

    for h_name, start_gw, end_gw in HORIZONS:
        gw_indices = list(range(start_gw - 1, end_gw))
        n_gws = len(gw_indices)
        corr_mat = precompute_pairwise_corr(fdr_mat[:, gw_indices])

        h_fdrs = p_all_fdrs[:, gw_indices]  # (n_players, n_gws)
        h_xps = p_all_xps[:, gw_indices]    # (n_players, n_gws)

        c_fdrs = h_fdrs[valid_5combos]  # (n_valid, 5, n_gws)
        c_xps = h_xps[valid_5combos]    # (n_valid, 5, n_gws)

        # 3 starting defenders: sort xP descending per GW
        sorted_xps = np.sort(c_xps, axis=1)[:, ::-1, :]
        top3_xps = sorted_xps[:, :3, :]
        tot_rot_xp = top3_xps.sum(axis=(1, 2))  # (n_valid,)

        # Add auto-sub expected value (12% Def4 + 3% Def5)
        def4_xps = sorted_xps[:, 3, :].sum(axis=1)
        def5_xps = sorted_xps[:, 4, :].sum(axis=1)
        auto_sub_ev = 0.12 * def4_xps + 0.03 * def5_xps

        # FDR of starters
        sorted_fdr = np.sort(c_fdrs, axis=1)
        top3_fdr = sorted_fdr[:, :3, :]
        rot_avg_fdr = top3_fdr.mean(axis=(1, 2))
        worst_starters = sorted_fdr[:, 2, :]
        no_diff_pct = (worst_starters <= 3.0).sum(axis=1) / float(n_gws) * 100.0
        all_easy_pct = (worst_starters <= 2.0).sum(axis=1) / float(n_gws) * 100.0

        # Calculate DCS for all valid combos
        for i in range(n_valid):
            c_idx = valid_5combos[i]
            c_clist = valid_cids[i]
            corrs = [corr_mat[c_clist[a], c_clist[b]] for a, b in pair_indices]
            avg_corr = float(np.mean(corrs)) if corrs else 0.0

            tot_xp_val = float(tot_rot_xp[i])
            auto_sub_val = float(auto_sub_ev[i])
            effective_tot_xp = tot_xp_val + auto_sub_val
            tot_price = float(valid_prices[i])

            dcs, oc_score, s_risk = compute_two_factor_dcs(
                rot_xp_per_gw=effective_tot_xp / float(n_gws),
                total_price=tot_price,
                floor_price=20.0,
                rot_avg_fdr=float(rot_avg_fdr[i]),
                no_diff_pct=float(no_diff_pct[i]),
                fdr_corr=avg_corr,
                min_xp_bound=9.0,
                max_xp_bound=20.0,
                gamma=gamma,
            )

            p_objs = [player_meta[pids[idx]] for idx in c_idx]
            lineup_str = " + ".join(f"{p['web_name']} ({p['club_short']})" for p in p_objs)
            budget_band = (
                "Band 1: Budget (£20.5m-£22.5m)" if tot_price <= 22.5
                else ("Band 2: Mid-Value (£23.0m-£24.0m)" if tot_price <= 24.0
                else ("Band 3: Single Anchor (£24.5m-£25.0m)" if tot_price <= 25.0
                else "Band 4: Premium / Dual Anchor (£25.5m-£26.0m)"))
            )

            tier_rows.append(
                {
                    "horizon": h_name,
                    "budget_band": budget_band,
                    "total_price": tot_price,
                    "dcs": dcs,
                    "oc_score": oc_score,
                    "s_risk": s_risk,
                    "tot_rot_xp": round(effective_tot_xp, 2),
                    "raw_rot_xp": round(tot_xp_val, 2),
                    "auto_sub_ev": round(auto_sub_val, 2),
                    "rot_xp_per_gw": round(effective_tot_xp / float(n_gws), 2),
                    "rot_avg_fdr": round(float(rot_avg_fdr[i]), 2),
                    "no_diff_pct": round(float(no_diff_pct[i]), 1),
                    "all_easy_pct": round(float(all_easy_pct[i]), 1),
                    "avg_fdr_corr": round(avg_corr, 4),
                    "num_unique_clubs": int(num_uniques_arr[i]),
                    "allocation_pattern": patterns_arr[i],
                    "lineup": lineup_str,
                    "def1": p_objs[0]["web_name"],
                    "def2": p_objs[1]["web_name"],
                    "def3": p_objs[2]["web_name"],
                    "def4": p_objs[3]["web_name"],
                    "def5": p_objs[4]["web_name"],
                }
            )

    df_tier = pd.DataFrame(tier_rows)

    # Filter top 200 per horizon for clean companion storage
    top_tier_list = []
    for _, grp in df_tier.groupby(["horizon", "budget_band"]):
        top_tier_list.append(grp.sort_values("dcs", ascending=False).head(50))
    df_top_tier = pd.concat(top_tier_list, ignore_index=True)

    return df_tier, df_top_tier


# =============================================================================
# STAGE 3: FULL BACKLINE (2 GKP + 5 DEF) SIMULATION
# =============================================================================

def run_full_backline_simulation(
    df_gkp_strat: pd.DataFrame,
    df_def_tier: pd.DataFrame,
    starters_gkp: pd.DataFrame,
    starters_def: pd.DataFrame,
    gw_xp_gkp: pd.DataFrame,
    gw_xp_def: pd.DataFrame,
    fdr_mat: np.ndarray,
    id_to_idx: dict[int, int],
    fixtures: pd.DataFrame,
    gamma: float = 0.25,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Simulate full backline (2 GKP + 5 DEF) across GW1-3 (BB1), GW4-19 (WC4), and GW1-19."""
    # Top GKP candidate pairings across strategies
    top_gkps = df_gkp_strat[df_gkp_strat["horizon"] == "gw1_19"].sort_values("dcs", ascending=False).head(15)

    # Top DEF candidate 5-sets across budget bands
    top_defs = df_def_tier[df_def_tier["horizon"] == "gw1_19"].sort_values("dcs", ascending=False).head(30)

    # 1. GW1-3 BB1 Simulation
    gw1_f = fixtures[fixtures["gameweek_id"] == 1]
    clash_pairs = set()
    for _, f in gw1_f.iterrows():
        h_idx = id_to_idx[int(f["home_club_id"])]
        a_idx = id_to_idx[int(f["away_club_id"])]
        clash_pairs.add(frozenset([h_idx, a_idx]))

    bb1_rows: list[dict] = []
    for _, gkp in df_gkp_strat[df_gkp_strat["horizon"] == "gw1_3"].sort_values("dcs", ascending=False).head(12).iterrows():
        for _, d in df_def_tier[df_def_tier["horizon"] == "gw1_3"].sort_values("dcs", ascending=False).head(25).iterrows():
            tot_price = gkp["total_price"] + d["total_price"]
            if tot_price > MAX_BACKLINE_TOTAL_PRICE:
                continue

            # Combined stats for GW1-3 (BB1 active in GW1: 7 starters; GW2-3: 1 GKP + 3 DEF)
            tot_rot_xp = gkp["tot_rot_xp"] + d["tot_rot_xp"]
            rot_xp_per_gw = tot_rot_xp / 3.0
            comb_fdr = (gkp["rot_avg_fdr"] + 3.0 * d["rot_avg_fdr"]) / 4.0
            comb_no_diff = min(gkp["no_diff_pct"], d["no_diff_pct"])
            comb_corr = (gkp["fdr_corr"] + d["avg_fdr_corr"]) / 2.0

            dcs, oc_score, s_risk = compute_two_factor_dcs(
                rot_xp_per_gw=rot_xp_per_gw,
                total_price=tot_price,
                floor_price=28.5,
                rot_avg_fdr=comb_fdr,
                no_diff_pct=comb_no_diff,
                fdr_corr=comb_corr,
                min_xp_bound=12.0,
                max_xp_bound=27.0,
                gamma=gamma,
            )

            budget_band = (
                "Band 1: Budget (£29.0m-£31.0m)" if tot_price <= 31.0
                else ("Band 2: Mid-Value (£31.5m-£33.0m)" if tot_price <= 33.0
                else ("Band 3: Single Anchor (£33.5m-£34.5m)" if tot_price <= 34.5
                else "Band 4: Premium / Dual Anchor (£35.0m-£36.0m)"))
            )

            bb1_rows.append(
                {
                    "horizon": "gw1_3_bb1",
                    "budget_band": budget_band,
                    "total_price": tot_price,
                    "dcs": dcs,
                    "oc_score": oc_score,
                    "s_risk": s_risk,
                    "tot_rot_xp": round(tot_rot_xp, 2),
                    "rot_xp_per_gw": round(rot_xp_per_gw, 2),
                    "rot_avg_fdr": round(comb_fdr, 2),
                    "no_diff_pct": round(comb_no_diff, 1),
                    "avg_fdr_corr": round(comb_corr, 4),
                    "gkp_strategy": gkp["strategy"],
                    "gkp_pairing": gkp["pairing"],
                    "def_lineup": d["lineup"],
                }
            )

    df_bb1 = pd.DataFrame(bb1_rows).sort_values("dcs", ascending=False).drop_duplicates(subset=["gkp_pairing", "def_lineup"]).head(100)

    # 2. GW4-19 WC4 Simulation (1 GKP + 3 DEF starters)
    wc4_rows: list[dict] = []
    for _, gkp in df_gkp_strat[df_gkp_strat["horizon"] == "gw4_19"].sort_values("dcs", ascending=False).head(12).iterrows():
        for _, d in df_def_tier[df_def_tier["horizon"] == "gw4_19"].sort_values("dcs", ascending=False).head(25).iterrows():
            tot_price = gkp["total_price"] + d["total_price"]
            if tot_price > MAX_BACKLINE_TOTAL_PRICE:
                continue

            tot_rot_xp = gkp["tot_rot_xp"] + d["tot_rot_xp"]
            rot_xp_per_gw = tot_rot_xp / 16.0
            comb_fdr = (gkp["rot_avg_fdr"] + 3.0 * d["rot_avg_fdr"]) / 4.0
            comb_no_diff = (gkp["no_diff_pct"] + d["no_diff_pct"]) / 2.0
            comb_corr = (gkp["fdr_corr"] + d["avg_fdr_corr"]) / 2.0

            dcs, oc_score, s_risk = compute_two_factor_dcs(
                rot_xp_per_gw=rot_xp_per_gw,
                total_price=tot_price,
                floor_price=28.5,
                rot_avg_fdr=comb_fdr,
                no_diff_pct=comb_no_diff,
                fdr_corr=comb_corr,
                min_xp_bound=12.0,
                max_xp_bound=27.0,
                gamma=gamma,
            )

            budget_band = (
                "Band 1: Budget (£29.0m-£31.0m)" if tot_price <= 31.0
                else ("Band 2: Mid-Value (£31.5m-£33.0m)" if tot_price <= 33.0
                else ("Band 3: Single Anchor (£33.5m-£34.5m)" if tot_price <= 34.5
                else "Band 4: Premium / Dual Anchor (£35.0m-£36.0m)"))
            )

            wc4_rows.append(
                {
                    "horizon": "gw4_19_wc4",
                    "budget_band": budget_band,
                    "total_price": tot_price,
                    "dcs": dcs,
                    "oc_score": oc_score,
                    "s_risk": s_risk,
                    "tot_rot_xp": round(tot_rot_xp, 2),
                    "rot_xp_per_gw": round(rot_xp_per_gw, 2),
                    "rot_avg_fdr": round(comb_fdr, 2),
                    "no_diff_pct": round(comb_no_diff, 1),
                    "avg_fdr_corr": round(comb_corr, 4),
                    "gkp_strategy": gkp["strategy"],
                    "gkp_pairing": gkp["pairing"],
                    "def_lineup": d["lineup"],
                }
            )

    df_wc4 = pd.DataFrame(wc4_rows).sort_values("dcs", ascending=False).drop_duplicates(subset=["gkp_pairing", "def_lineup"]).head(100)

    # 3. GW1-19 Full First-Half Benchmark
    gw1_19_rows: list[dict] = []
    for _, gkp in top_gkps.iterrows():
        for _, d in top_defs.iterrows():
            tot_price = gkp["total_price"] + d["total_price"]
            if tot_price > MAX_BACKLINE_TOTAL_PRICE:
                continue

            tot_rot_xp = gkp["tot_rot_xp"] + d["tot_rot_xp"]
            rot_xp_per_gw = tot_rot_xp / 19.0
            comb_fdr = (gkp["rot_avg_fdr"] + 3.0 * d["rot_avg_fdr"]) / 4.0
            comb_no_diff = (gkp["no_diff_pct"] + d["no_diff_pct"]) / 2.0
            comb_corr = (gkp["fdr_corr"] + d["avg_fdr_corr"]) / 2.0

            dcs, oc_score, s_risk = compute_two_factor_dcs(
                rot_xp_per_gw=rot_xp_per_gw,
                total_price=tot_price,
                floor_price=28.5,
                rot_avg_fdr=comb_fdr,
                no_diff_pct=comb_no_diff,
                fdr_corr=comb_corr,
                min_xp_bound=12.0,
                max_xp_bound=27.0,
                gamma=gamma,
            )

            budget_band = (
                "Band 1: Budget (£29.0m-£31.0m)" if tot_price <= 31.0
                else ("Band 2: Mid-Value (£31.5m-£33.0m)" if tot_price <= 33.0
                else ("Band 3: Single Anchor (£33.5m-£34.5m)" if tot_price <= 34.5
                else "Band 4: Premium / Dual Anchor (£35.0m-£36.0m)"))
            )

            gw1_19_rows.append(
                {
                    "horizon": "gw1_19",
                    "budget_band": budget_band,
                    "total_price": tot_price,
                    "dcs": dcs,
                    "oc_score": oc_score,
                    "s_risk": s_risk,
                    "tot_rot_xp": round(tot_rot_xp, 2),
                    "rot_xp_per_gw": round(rot_xp_per_gw, 2),
                    "rot_avg_fdr": round(comb_fdr, 2),
                    "no_diff_pct": round(comb_no_diff, 1),
                    "avg_fdr_corr": round(comb_corr, 4),
                    "gkp_strategy": gkp["strategy"],
                    "gkp_pairing": gkp["pairing"],
                    "def_lineup": d["lineup"],
                }
            )

    df_gw1_19 = pd.DataFrame(gw1_19_rows).sort_values("dcs", ascending=False).drop_duplicates(subset=["gkp_pairing", "def_lineup"]).head(100)

    return df_bb1, df_wc4, df_gw1_19


# =============================================================================
# MASTER RUNNER
# =============================================================================

def run_defensive_rotation_pipeline() -> None:
    """Execute complete defensive fixture rotation, strategy proof, and combinatorial simulation."""
    configure_utf8_stdio()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=== DEFENSIVE ARCHITECTURE & FIXTURE ROTATION ANALYSIS ===")

    players = pd.read_parquet(DATA_DIR / "players.parquet")
    clubs = _SEED_MOD.load_seeded_clubs()
    fixtures = pd.read_parquet(DATA_DIR / "fixtures.parquet")
    df_stats = pd.read_csv(STATS_CSV)

    cost_map = players.set_index("id")["now_cost"] / 10.0
    club_map = players.set_index("id")["club_id"]

    df_stats["price"] = df_stats["player_id"].map(cost_map)
    df_stats["club_id"] = df_stats["player_id"].map(club_map)

    # Filter starters by role authority
    starters_gkp = df_stats[
        (df_stats["position"] == "GKP") & (df_stats["expected_role"].isin(DRAFT_ROLES))
    ].dropna(subset=["price", "club_id"]).reset_index(drop=True)

    starters_def = df_stats[
        (df_stats["position"] == "DEF") & (df_stats["expected_role"].isin(DRAFT_ROLES))
    ].dropna(subset=["price", "club_id"]).reset_index(drop=True)

    print(f"Loaded {len(starters_gkp)} starter GKPs and {len(starters_def)} starter DEFs.")

    fmap = _fixture_maps(fixtures, clubs, list(range(1, 39)))
    fdr_mat, idx_to_short, id_to_idx = build_seed_fdr_matrix(fmap, clubs, n_gw=38)
    gamma = compute_outfield_capital_slope(STATS_CSV, DATA_DIR / "players.parquet")
    print(f"Empirical outfield capital slope gamma = {gamma:.4f} xP/£1.0m/GW")

    # Project weekly points
    print("\n--- Projecting Hybrid Points Grid (GW1-38) ---")
    gw_xp_gkp = project_starter_grid(starters_gkp, fmap, "GKP", GKP_POSITION_ID, end_gw=38)
    gw_xp_def = project_starter_grid(starters_def, fmap, "DEF", DEF_POSITION_ID, end_gw=38)

    # Save performance baselines
    starters_gkp.to_csv(OUT_DIR / "gkp_performance_baseline.csv", index=False)
    starters_def.to_csv(OUT_DIR / "def_performance_baseline.csv", index=False)

    # 1. Stage 1: GKP Strategy Analysis
    print("\n--- Stage 1: Goalkeeper Strategy Proof & Pairings ---")
    df_gkp_strat, df_gkp_pairs = run_gkp_strategy_analysis(starters_gkp, gw_xp_gkp, fdr_mat, id_to_idx, gamma=gamma)
    df_gkp_strat.to_csv(OUT_DIR / "gkp_strategy_comparison.csv", index=False)
    df_gkp_pairs.to_csv(OUT_DIR / "gkp_rotation_matrix.csv", index=False)
    print(f"Generated {len(df_gkp_strat)} strategy evaluations and {len(df_gkp_pairs)} active pair combinations.")

    # 2. Stage 2: 5-DEF Combinatorial Analysis
    print("\n--- Stage 2: 5-DEF Club Combinations (Max 2 per club) ---")
    df_def_clubs = run_def_club_combinatorial_analysis(fdr_mat, idx_to_short)
    df_def_clubs.to_csv(OUT_DIR / "def_club_partitions_matrix.csv", index=False)
    print(f"Evaluated {len(df_def_clubs)} club multiset horizons.")

    df_bb1_clubs = run_bb1_wc4_club_analysis(fdr_mat, idx_to_short, fixtures, id_to_idx)
    df_bb1_clubs.to_csv(OUT_DIR / "def_bb1_wc4_club_matrix.csv", index=False)
    print(f"Evaluated {len(df_bb1_clubs)} non-clashing BB1 5-club sets.")

    print("Simulating 5-DEF player tier combinations...")
    df_def_tier, df_def_top_tier = simulate_def_tier_player_rotations(starters_def, gw_xp_def, fdr_mat, id_to_idx, gamma=gamma)
    df_def_top_tier.to_csv(OUT_DIR / "def_tier_player_rotations.csv", index=False)
    print(f"Generated {len(df_def_top_tier)} top-tier 5-DEF player rotations.")

    # 3. Stage 3: Full Backline Simulation
    print("\n--- Stage 3: Full Backline Simulation (2 GKP + 5 DEF) ---")
    df_bb1_backline, df_wc4_backline, df_gw1_19_backline = run_full_backline_simulation(
        df_gkp_strat,
        df_def_tier,
        starters_gkp,
        starters_def,
        gw_xp_gkp,
        gw_xp_def,
        fdr_mat,
        id_to_idx,
        fixtures,
        gamma=gamma,
    )
    df_bb1_backline.to_csv(OUT_DIR / "backline_bb1_wc4_lineups.csv", index=False)
    df_wc4_backline.to_csv(OUT_DIR / "backline_gw4_19_lineups.csv", index=False)
    df_gw1_19_backline.to_csv(OUT_DIR / "backline_gw1_19_lineups.csv", index=False)
    print(f"Generated {len(df_bb1_backline)} BB1 lineups, {len(df_wc4_backline)} WC4 lineups, and {len(df_gw1_19_backline)} GW1-19 benchmark lineups.")

    sync_spec = importlib.util.spec_from_file_location(
        "sync_live_research_figures",
        PROJECT_ROOT / "docs/archive/sync_live_research_figures.py",
    )
    sync_mod = importlib.util.module_from_spec(sync_spec)
    assert sync_spec.loader is not None
    sync_spec.loader.exec_module(sync_mod)
    sync_mod.sync_all()

    print("\n=== UNIFIED DEFENSIVE ROTATION PIPELINE COMPLETE ===")


if __name__ == "__main__":
    run_defensive_rotation_pipeline()
