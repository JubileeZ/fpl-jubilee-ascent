"""Starter Defender (5 DEF) Fixture Rotation & Diversification Analysis.

Simulates 5 DEF diversification and fixture rotation across:
1. Multi-horizon analysis: GW1-3 (Early sprint), GW4-19 (Post-Wildcard), GW1-19 (First half), GW1-38 (Full season).
2. Combinatorial club partitions (2 to 5 unique clubs, max 2 for top-4 attack clubs MCI/ARS/LIV/CHE, max 3 others):
   - 5 unique clubs (1+1+1+1+1)
   - 4 clubs (2+1+1+1)
   - 3 clubs (2+2+1 and 3+1+1)
   - 2 clubs (3+2)
3. Flexible Budget Spectrum (at most £26.0m):
   - Band 1: Budget (£20.5m–£22.5m)
   - Band 2: Mid-Value (£23.0m–£24.0m)
   - Band 3: Single Anchor (£24.5m–£25.0m)
   - Band 4: Premium / Dual Anchor (£25.5m–£26.0m)
4. Specialized Pre-Wildcard Scenario: GW1 Bench Boost (BB1) + GW4 Wildcard (WC4).
   - GW1: All 5 defenders start on Bench Boost (Zero Head-to-Head Opponent Clashes, max FDR <= 3.0).
   - GW2 & GW3: Best 3 defenders rotate by lowest FDR / highest xP.
   - GW4: Full Wildcard reset.
"""

from __future__ import annotations

import itertools
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from features.builder import _fixture_maps
from models.participation_state_hybrid import ParticipationStateHybridModel

DATA_DIR = PROJECT_ROOT / "data" / "processed"
RESEARCH_DIR = PROJECT_ROOT / "docs" / "archive"
OUT_DIR = PROJECT_ROOT / "docs" / "archive" / "def-fixture-rotation"
STATS_CSV = RESEARCH_DIR / "gw1-6-preseason-pipeline" / "02-expected-stats-gw1-5" / "expected-stats-gw1-5.csv"
ROLE_CSV = RESEARCH_DIR / "gw1-6-preseason-pipeline" / "01-expected-role-gw1-5" / "expected-role-gw1-5.csv"

DRAFT_ROLES = ("Nailed Starter", "Regular Starter")
FLAT_START_MINUTES = 90.0
DEF_POSITION_ID = 2
MAX_TOTAL_PRICE = 26.0

TOP_ATTACK_CLUBS = {"MCI", "ARS", "LIV", "CHE"}
MAX_DEF_PER_TOP_CLUB = 2
MAX_DEF_PER_OTHER_CLUB = 3

HORIZONS = (
    ("gw1_3", 1, 3),
    ("gw4_19", 4, 19),
    ("gw1_19", 1, 19),
    ("full_season", 1, 38),
)

# Ranking lenses — more negative avg_fdr_corr is better (schedules diversify).
# GW4-19 / GW1-19 club tables: min rot FDR, then 100% zero-diff, then corr-first.
CLUB_5WAY_SORT_COLS = ["horizon", "rot_avg_fdr", "no_diff_pct", "avg_fdr_corr", "all_easy_pct"]
CLUB_5WAY_SORT_ASC = [True, True, False, True, False]
# BB1 club tables: 11-start eff FDR, then GW1, then GW2-3, then corr-first.
BB1_CLUB_SORT_COLS = ["effective_avg_fdr", "gw1_avg_fdr", "gw2_3_rot_fdr", "avg_fdr_corr"]
BB1_CLUB_SORT_ASC = [True, True, True, True]
# BB2 club tables: 11-start eff FDR, then GW2, then GW1+GW3, then corr-first.
BB2_CLUB_SORT_COLS = ["effective_avg_fdr", "gw2_avg_fdr", "gw1_3_rot_fdr", "avg_fdr_corr"]
BB2_CLUB_SORT_ASC = [True, True, True, True]
# Published WC4 bridge Top 10 among eligible rows.
BRIDGE_RANK_SORT_COLS = ["path_eff_fdr", "gw1_avg_fdr", "n_swaps", "pre_corr", "pre_clubs"]
BRIDGE_RANK_SORT_ASC = [True, True, True, True, True]


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
    defcon = outfield.get("per90_defensive_contribution", outfield["per90_defcon"]).fillna(0.0)
    p_start = outfield["p_start"].fillna(0.75)
    est_gw_xp = p_start * (xg * 4.5 + xa * 3.0 + defcon * 0.15 + 2.0)
    slope, _ = np.polyfit(outfield["price"], est_gw_xp, 1)
    return float(max(0.15, min(0.60, slope)))


def compute_def_rqi(
    *,
    tot_rot_xp: float,
    num_gws: int,
    rot_avg_fdr: float,
    no_diff_pct: float,
    fdr_corr: float,
    total_price: float,
    gamma: float = 0.25,
) -> tuple[float, float]:
    """DEF Rotation Quality Index (0-100 scale) and Opportunity-Cost Adjusted RQI (OC-RQI)."""
    rot_xp_per_gw = tot_rot_xp / num_gws
    s_xp = float(np.clip((rot_xp_per_gw - 10.0) / (22.0 - 10.0) * 100.0, 0, 100))
    s_fdr = float(np.clip((3.5 - rot_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100))
    s_no_diff = float(np.clip(no_diff_pct, 0, 100))
    s_corr = float(np.clip((-fdr_corr + 1.0) / 2.0 * 100.0, 0, 100))
    s_cost = float(np.clip((26.0 - total_price) / (26.0 - 20.0) * 100.0, 0, 100))

    score = round(0.40 * s_xp + 0.20 * s_fdr + 0.15 * s_no_diff + 0.10 * s_corr + 0.15 * s_cost, 2)
    oc_rqi = round(rot_xp_per_gw - gamma * (total_price - 20.0), 3)
    return score, oc_rqi


def compute_bb_rqi(
    *,
    tot_effective_xp: float,
    gw1_avg_fdr: float,
    gw2_3_rot_fdr: float,
    effective_avg_fdr: float,
    avg_corr: float,
    total_price: float,
    gamma: float = 0.25,
) -> tuple[float, float]:
    """Bench Boost Rotation Quality Index (BB-RQI, 0-100 scale) and BB OC-RQI."""
    s_xp = float(np.clip((tot_effective_xp - 40.0) / (75.0 - 40.0) * 100.0, 0, 100))
    s_fdr1 = float(np.clip((3.5 - gw1_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100))
    s_fdr23 = float(np.clip((3.5 - gw2_3_rot_fdr) / (3.5 - 2.0) * 100.0, 0, 100))
    s_eff_fdr = float(np.clip((3.5 - effective_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100))
    s_corr = float(np.clip((-avg_corr + 1.0) / 2.0 * 100.0, 0, 100))
    s_cost = float(np.clip((26.0 - total_price) / (26.0 - 20.0) * 100.0, 0, 100))

    score = round(0.40 * s_xp + 0.15 * s_fdr1 + 0.10 * s_fdr23 + 0.10 * s_eff_fdr + 0.10 * s_corr + 0.15 * s_cost, 2)
    bb_oc_rqi = round(tot_effective_xp - gamma * (total_price - 20.0) * 3, 3)
    return score, bb_oc_rqi


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


def precompute_pairwise_corr(fdr_mat_sub: np.ndarray) -> np.ndarray:
    """Precompute 20x20 pairwise correlation matrix for a given gameweek slice."""
    n_clubs = fdr_mat_sub.shape[0]
    corr_mat = np.eye(n_clubs, dtype=float)  # Intra-club diagonal correlation is 1.0
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


def generate_valid_club_multisets(idx_to_short: dict[int, str]) -> tuple[np.ndarray, list[str], list[int], list[str]]:
    """Generate all valid 5-club multisets satisfying top-attack quota rules (max 2 for MCI/ARS/LIV/CHE, max 3 others)."""
    all_combos = list(itertools.combinations_with_replacement(range(20), 5))
    valid_combos = []
    patterns = []
    num_uniques = []
    club_names = []
    for c in all_combos:
        counts = Counter(c)
        valid = True
        for c_idx, cnt in counts.items():
            c_short = idx_to_short[c_idx]
            if c_short in TOP_ATTACK_CLUBS and cnt > MAX_DEF_PER_TOP_CLUB:
                valid = False
                break
            elif cnt > MAX_DEF_PER_OTHER_CLUB:
                valid = False
                break
        if valid:
            valid_combos.append(c)
            p_tup = tuple(sorted(counts.values(), reverse=True))
            patterns.append("+".join(str(x) for x in p_tup))
            num_uniques.append(len(p_tup))
            club_names.append("-".join(idx_to_short[x] for x in c))
    return np.array(valid_combos, dtype=np.int32), patterns, num_uniques, club_names


def run_5club_combinatorial_analysis(fdr_mat: np.ndarray, idx_to_short: dict[int, str]) -> pd.DataFrame:
    """Evaluate all valid 41,344 5-club combinations (2 to 5 unique clubs) across standard horizons."""
    valid_combos, patterns, num_uniques, club_names = generate_valid_club_multisets(idx_to_short)
    pair_indices = list(itertools.combinations(range(5), 2))
    all_rows: list[dict] = []

    for h_name, start_gw, end_gw in HORIZONS:
        gw_indices = list(range(start_gw - 1, end_gw))
        n_gws = len(gw_indices)
        h_fdr = fdr_mat[:, gw_indices]
        corr_mat = precompute_pairwise_corr(h_fdr)

        combo_fdr = h_fdr[valid_combos]
        sorted_fdr = np.sort(combo_fdr, axis=1)
        top3_fdr = sorted_fdr[:, :3, :]
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


def run_bb1_wc4_club_combinatorial_analysis(
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

    valid_combos, patterns, num_uniques, club_names = generate_valid_club_multisets(idx_to_short)
    pair_indices = list(itertools.combinations(range(5), 2))
    corr_mat = precompute_pairwise_corr(fdr_mat[:, 0:3])

    rows: list[dict] = []
    for i, c in enumerate(valid_combos):
        has_clash = any(frozenset([c[a], c[b]]) in clash_pairs for a in range(5) for b in range(a + 1, 5) if c[a] != c[b])
        if has_clash:
            continue

        # GW1: all 5 start
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


def run_bb2_wc4_club_combinatorial_analysis(
    fdr_mat: np.ndarray,
    idx_to_short: dict[int, str],
    fixtures: pd.DataFrame,
    id_to_idx: dict[int, int],
) -> pd.DataFrame:
    """Evaluate non-clashing BB2 + WC4 5-club sets across GW1-3."""
    gw2_f = fixtures[fixtures["gameweek_id"] == 2]
    clash_pairs = set()
    for _, f in gw2_f.iterrows():
        h_idx = id_to_idx[int(f["home_club_id"])]
        a_idx = id_to_idx[int(f["away_club_id"])]
        clash_pairs.add(frozenset([h_idx, a_idx]))

    valid_combos, patterns, num_uniques, club_names = generate_valid_club_multisets(idx_to_short)
    pair_indices = list(itertools.combinations(range(5), 2))
    corr_mat = precompute_pairwise_corr(fdr_mat[:, 0:3])

    rows: list[dict] = []
    for i, c in enumerate(valid_combos):
        has_clash = any(frozenset([c[a], c[b]]) in clash_pairs for a in range(5) for b in range(a + 1, 5) if c[a] != c[b])
        if has_clash:
            continue

        # GW2: all 5 start on Bench Boost
        gw2_fdrs = fdr_mat[c, 1]
        gw2_max_fdr = float(gw2_fdrs.max())
        if gw2_max_fdr > 3.0:  # Strict ceiling rule
            continue
        gw2_avg_fdr = float(gw2_fdrs.mean())

        # GW1 and GW3: top 3 start
        gw1_fdrs = np.sort(fdr_mat[c, 0])[:3]
        gw3_fdrs = np.sort(fdr_mat[c, 2])[:3]
        gw1_avg_fdr = float(gw1_fdrs.mean())
        gw3_avg_fdr = float(gw3_fdrs.mean())
        gw1_3_rot_fdr = float((gw1_fdrs.sum() + gw3_fdrs.sum()) / 6.0)

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
                "gw2_avg_fdr": round(gw2_avg_fdr, 2),
                "gw2_max_fdr": round(gw2_max_fdr, 1),
                "gw3_avg_fdr": round(gw3_avg_fdr, 2),
                "gw1_3_rot_fdr": round(gw1_3_rot_fdr, 2),
                "effective_avg_fdr": round(effective_avg_fdr, 4),
                "avg_fdr_corr": round(avg_corr, 4),
            }
        )

    return pd.DataFrame(rows)


def project_starter_def_grid(starters: pd.DataFrame, fmap: pd.DataFrame, end_gw: int = 38) -> pd.DataFrame:
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
                    "position": "DEF",
                    "position_id": DEF_POSITION_ID,
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
                        player.get("per90_defensive_contribution", player.get("per90_defcon", 7.0))
                    ),
                    "per90_saves": 0.0,
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
            per90_xg=("per90_xg", "first"),
            per90_xa=("per90_xa", "first"),
            per90_defcon=("per90_defensive_contribution", "first"),
            per90_goals_conceded=("per90_goals_conceded", "first"),
        )
    )


def classify_budget_band(price: float) -> tuple[str, int]:
    """Classify total 5 DEF spend into natural budget band."""
    if price <= 22.5:
        return "Band 1: Budget (£20.5m-£22.5m)", 1
    elif price <= 24.0:
        return "Band 2: Mid-Value (£23.0m-£24.0m)", 2
    elif price <= 25.0:
        return "Band 3: Single Anchor (£24.5m-£25.0m)", 3
    else:
        return "Band 4: Premium / Dual Anchor (£25.5m-£26.0m)", 4


def simulate_player_tier_combinations(
    starters: pd.DataFrame,
    gw_xp: pd.DataFrame,
    fdr_mat: np.ndarray,
    id_to_idx: dict[int, int],
    idx_to_short: dict[int, str],
) -> pd.DataFrame:
    """Simulate 5-DEF combinations across flexible budget spectrum up to £26.0m with vectorized ranking."""
    xp_lookup = {
        int(pid): grp.set_index("gameweek_id")["projected_points"].to_dict()
        for pid, grp in gw_xp.groupby("player_id")
    }

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
        if combo_prices[i] > MAX_TOTAL_PRICE:
            continue
        c_counts = Counter(combo_cids[i])
        valid = True
        for cid, cnt in c_counts.items():
            c_short = idx_to_short[cid]
            if c_short in TOP_ATTACK_CLUBS and cnt > MAX_DEF_PER_TOP_CLUB:
                valid = False
                break
            elif cnt > MAX_DEF_PER_OTHER_CLUB:
                valid = False
                break
        if valid:
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

    all_tier_rows: list[dict] = []
    pair_indices = list(itertools.combinations(range(5), 2))

    for h_name, start_gw, end_gw in HORIZONS:
        gw_indices = list(range(start_gw - 1, end_gw))
        n_gws = len(gw_indices)
        h_fdr = fdr_mat[:, gw_indices]
        corr_mat = precompute_pairwise_corr(h_fdr)

        combo_fdr = p_all_fdrs[valid_5combos][:, :, gw_indices]
        combo_xp = p_all_xps[valid_5combos][:, :, gw_indices]

        # Pure max(xP) weekly selection:
        top3_xp_order = np.argsort(-combo_xp, axis=1)
        top3_idx = top3_xp_order[:, :3, :]
        top3_fdr = np.take_along_axis(combo_fdr, top3_idx, axis=1)
        top3_xp = np.take_along_axis(combo_xp, top3_idx, axis=1)

        # Auto-sub EV: 4th defender has 12% entry probability, 5th defender has 3%
        bench_idx = top3_xp_order[:, 3:, :]
        bench_xp = np.take_along_axis(combo_xp, bench_idx, axis=1)
        bench_eff_xp = (0.12 * bench_xp[:, 0, :] + 0.03 * bench_xp[:, 1, :]).sum(axis=1)

        tot_rot_xp = top3_xp.sum(axis=(1, 2)) + bench_eff_xp
        rot_avg_fdr = top3_fdr.mean(axis=(1, 2))
        worst_starter = top3_fdr.max(axis=1)
        no_diff_gws = (worst_starter <= 3.0).sum(axis=1)
        no_diff_pct = no_diff_gws / float(n_gws) * 100.0
        max_worst_starter = worst_starter.max(axis=1)

        pair_corrs = np.array([[corr_mat[valid_cids[i, a], valid_cids[i, b]] for a, b in pair_indices] for i in range(len(valid_5combos))])
        avg_corrs = pair_corrs.mean(axis=1)

        # Vectorized RQI & OC-RQI
        gamma = compute_outfield_capital_slope(STATS_CSV, DATA_DIR / "players.parquet")
        s_xp = np.clip((tot_rot_xp / float(n_gws) - 10.0) / (22.0 - 10.0) * 100.0, 0, 100)
        s_fdr = np.clip((3.5 - rot_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100)
        s_no_diff = np.clip(no_diff_pct, 0, 100)
        s_corr = np.clip((-avg_corrs + 1.0) / 2.0 * 100.0, 0, 100)
        s_cost = np.clip((26.0 - valid_prices) / (26.0 - 20.0) * 100.0, 0, 100)
        rqi_arr = np.round(0.40 * s_xp + 0.20 * s_fdr + 0.15 * s_no_diff + 0.10 * s_corr + 0.15 * s_cost, 2)
        oc_rqi_arr = np.round((tot_rot_xp / float(n_gws)) - gamma * (valid_prices - 20.0), 3)

        # Select top candidates per band to write
        band_indices: dict[int, list[int]] = {1: [], 2: [], 3: [], 4: []}
        for i in range(len(valid_5combos)):
            _, b_id = classify_budget_band(float(valid_prices[i]))
            band_indices[b_id].append(i)

        selected_indices = set()
        for b_id, idx_list in band_indices.items():
            if not idx_list:
                continue
            sub_rqi = rqi_arr[idx_list]
            sub_xp = tot_rot_xp[idx_list]
            # Top 1000 by RQI + top 200 by XP
            top_rqi_idx = [idx_list[k] for k in np.argsort(-sub_rqi)[:1000]]
            top_xp_idx = [idx_list[k] for k in np.argsort(-sub_xp)[:200]]
            selected_indices.update(top_rqi_idx)
            selected_indices.update(top_xp_idx)

        for i in selected_indices:
            tot_p = float(valid_prices[i])
            band_name, band_id = classify_budget_band(tot_p)
            avg_corr = float(avg_corrs[i])

            p_objs = [player_meta[pids[idx]] for idx in valid_5combos[i]]
            all_tier_rows.append(
                {
                    "tier": band_name,
                    "tier_id": band_id,
                    "horizon": h_name,
                    "start_gw": start_gw,
                    "end_gw": end_gw,
                    "num_gws": n_gws,
                    "num_unique_clubs": int(num_uniques_arr[i]),
                    "allocation_pattern": str(patterns_arr[i]),
                    "lineup_summary": " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs),
                    "clubs": "-".join(p["club_short"] for p in p_objs),
                    "total_price": round(tot_p, 1),
                    "rqi": float(rqi_arr[i]),
                    "oc_rqi": float(oc_rqi_arr[i]),
                    "tot_rot_xp": round(float(tot_rot_xp[i]), 2),
                    "rot_avg_fdr": round(float(rot_avg_fdr[i]), 4),
                    "max_worst_starter": round(float(max_worst_starter[i]), 1),
                    "no_diff_gws": int(no_diff_gws[i]),
                    "no_diff_pct": round(float(no_diff_pct[i]), 1),
                    "avg_fdr_corr": round(avg_corr, 4),
                }
            )

    return pd.DataFrame(all_tier_rows)


def simulate_bb1_wc4_player_tier_combinations(
    starters: pd.DataFrame,
    gw_xp: pd.DataFrame,
    fdr_mat: np.ndarray,
    id_to_idx: dict[int, int],
    idx_to_short: dict[int, str],
    fixtures: pd.DataFrame,
) -> pd.DataFrame:
    """Simulate player lineups specifically for GW1 BB (5 starters) + GW2-3 rotation (3 starters) up to £26.0m."""
    xp_lookup = {
        int(pid): grp.set_index("gameweek_id")["projected_points"].to_dict()
        for pid, grp in gw_xp.groupby("player_id")
    }

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

    gw1_f = fixtures[fixtures["gameweek_id"] == 1]
    clash_pairs = set()
    for _, f in gw1_f.iterrows():
        h_idx = id_to_idx[int(f["home_club_id"])]
        a_idx = id_to_idx[int(f["away_club_id"])]
        clash_pairs.add(frozenset([h_idx, a_idx]))

    valid_indices = []
    patterns = []
    num_uniques = []
    for i in range(len(all_5combos)):
        if combo_prices[i] > MAX_TOTAL_PRICE:
            continue
        c_counts = Counter(combo_cids[i])
        valid = True
        for cid, cnt in c_counts.items():
            c_short = idx_to_short[cid]
            if c_short in TOP_ATTACK_CLUBS and cnt > MAX_DEF_PER_TOP_CLUB:
                valid = False
                break
            elif cnt > MAX_DEF_PER_OTHER_CLUB:
                valid = False
                break
        if not valid:
            continue

        has_clash = any(
            frozenset([combo_cids[i, j], combo_cids[i, k]]) in clash_pairs
            for j in range(5)
            for k in range(j + 1, 5)
            if combo_cids[i, j] != combo_cids[i, k]
        )
        if has_clash:
            continue

        if p_all_fdrs[all_5combos[i], 0].max() > 3.0:
            continue

        valid_indices.append(i)
        p_tup = tuple(sorted(c_counts.values(), reverse=True))
        patterns.append("+".join(str(x) for x in p_tup))
        num_uniques.append(len(p_tup))

    valid_indices = np.array(valid_indices, dtype=np.int32)
    valid_bb1_combos = all_5combos[valid_indices]
    valid_bb1_prices = combo_prices[valid_indices]
    valid_cids = combo_cids[valid_indices]
    patterns_arr = np.array(patterns)
    num_uniques_arr = np.array(num_uniques, dtype=np.int32)

    corr_mat = precompute_pairwise_corr(fdr_mat[:, 0:3])
    pair_indices = list(itertools.combinations(range(5), 2))

    gw1_xps = p_all_xps[valid_bb1_combos, 0].sum(axis=1)
    gw1_fdrs = p_all_fdrs[valid_bb1_combos, 0].mean(axis=1)

    gw2_combo_fdr = p_all_fdrs[valid_bb1_combos, 1]
    gw2_combo_xp = p_all_xps[valid_bb1_combos, 1]
    gw2_order = np.argsort(-gw2_combo_xp, axis=1)
    gw2_top3_xp = np.take_along_axis(gw2_combo_xp, gw2_order[:, :3], axis=1).sum(axis=1)
    gw2_bench_xp = (0.12 * np.take_along_axis(gw2_combo_xp, gw2_order[:, 3:4], axis=1) + 0.03 * np.take_along_axis(gw2_combo_xp, gw2_order[:, 4:5], axis=1)).sum(axis=1)
    gw2_top3_fdr = np.take_along_axis(gw2_combo_fdr, gw2_order[:, :3], axis=1).sum(axis=1)

    gw3_combo_fdr = p_all_fdrs[valid_bb1_combos, 2]
    gw3_combo_xp = p_all_xps[valid_bb1_combos, 2]
    gw3_order = np.argsort(-gw3_combo_xp, axis=1)
    gw3_top3_xp = np.take_along_axis(gw3_combo_xp, gw3_order[:, :3], axis=1).sum(axis=1)
    gw3_bench_xp = (0.12 * np.take_along_axis(gw3_combo_xp, gw3_order[:, 3:4], axis=1) + 0.03 * np.take_along_axis(gw3_combo_xp, gw3_order[:, 4:5], axis=1)).sum(axis=1)
    gw3_top3_fdr = np.take_along_axis(gw3_combo_fdr, gw3_order[:, :3], axis=1).sum(axis=1)

    tot_effective_xp = gw1_xps + (gw2_top3_xp + gw2_bench_xp) + (gw3_top3_xp + gw3_bench_xp)
    gw2_3_rot_fdr = (gw2_top3_fdr + gw3_top3_fdr) / 6.0
    effective_avg_fdr = (p_all_fdrs[valid_bb1_combos, 0].sum(axis=1) + gw2_top3_fdr + gw3_top3_fdr) / 11.0

    pair_corrs = np.array([[corr_mat[valid_cids[i, a], valid_cids[i, b]] for a, b in pair_indices] for i in range(len(valid_bb1_combos))])
    avg_corrs = pair_corrs.mean(axis=1)

    gamma = compute_outfield_capital_slope(STATS_CSV, DATA_DIR / "players.parquet")
    s_xp = np.clip((tot_effective_xp - 40.0) / (75.0 - 40.0) * 100.0, 0, 100)
    s_fdr1 = np.clip((3.5 - gw1_fdrs) / (3.5 - 2.0) * 100.0, 0, 100)
    s_fdr23 = np.clip((3.5 - gw2_3_rot_fdr) / (3.5 - 2.0) * 100.0, 0, 100)
    s_eff_fdr = np.clip((3.5 - effective_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100)
    s_corr = np.clip((-avg_corrs + 1.0) / 2.0 * 100.0, 0, 100)
    s_cost = np.clip((26.0 - valid_bb1_prices) / (26.0 - 20.0) * 100.0, 0, 100)
    bb_rqi_arr = np.round(0.40 * s_xp + 0.15 * s_fdr1 + 0.10 * s_fdr23 + 0.10 * s_eff_fdr + 0.10 * s_corr + 0.15 * s_cost, 2)
    bb_oc_rqi_arr = np.round(tot_effective_xp - gamma * (valid_bb1_prices - 20.0) * 3, 3)

    band_indices: dict[int, list[int]] = {1: [], 2: [], 3: [], 4: []}
    for i in range(len(valid_bb1_combos)):
        _, b_id = classify_budget_band(float(valid_bb1_prices[i]))
        band_indices[b_id].append(i)

    selected_indices = set()
    for b_id, idx_list in band_indices.items():
        if not idx_list:
            continue
        sub_rqi = bb_rqi_arr[idx_list]
        sub_xp = tot_effective_xp[idx_list]
        top_rqi_idx = [idx_list[k] for k in np.argsort(-sub_rqi)[:1000]]
        top_xp_idx = [idx_list[k] for k in np.argsort(-sub_xp)[:200]]
        selected_indices.update(top_rqi_idx)
        selected_indices.update(top_xp_idx)

    rows: list[dict] = []
    for i in selected_indices:
        tot_p = float(valid_bb1_prices[i])
        band_name, band_id = classify_budget_band(tot_p)
        avg_corr = float(avg_corrs[i])

        p_objs = [player_meta[pids[idx]] for idx in valid_bb1_combos[i]]
        rows.append(
            {
                "tier": band_name,
                "tier_id": band_id,
                "num_unique_clubs": int(num_uniques_arr[i]),
                "allocation_pattern": str(patterns_arr[i]),
                "lineup_summary": " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs),
                "clubs": "-".join(p["club_short"] for p in p_objs),
                "total_price": round(tot_p, 1),
                "bb_rqi": float(bb_rqi_arr[i]),
                "bb_oc_rqi": float(bb_oc_rqi_arr[i]),
                "tot_effective_xp": round(float(tot_effective_xp[i]), 2),
                "gw1_xp_5def": round(float(gw1_xps[i]), 2),
                "gw2_3_xp_6def": round(float(gw2_top3_xp[i] + gw3_top3_xp[i]), 2),
                "gw1_avg_fdr": round(float(gw1_fdrs[i]), 2),
                "gw2_3_rot_fdr": round(float(gw2_3_rot_fdr[i]), 2),
                "effective_avg_fdr": round(float(effective_avg_fdr[i]), 4),
                "avg_fdr_corr": round(avg_corr, 4),
            }
        )

    return pd.DataFrame(rows)


def simulate_bb2_wc4_player_tier_combinations(
    starters: pd.DataFrame,
    gw_xp: pd.DataFrame,
    fdr_mat: np.ndarray,
    id_to_idx: dict[int, int],
    idx_to_short: dict[int, str],
    fixtures: pd.DataFrame,
) -> pd.DataFrame:
    """Simulate player lineups specifically for GW2 BB (5 starters) + GW1 & GW3 rotation (3 starters) up to £26.0m."""
    xp_lookup = {
        int(pid): grp.set_index("gameweek_id")["projected_points"].to_dict()
        for pid, grp in gw_xp.groupby("player_id")
    }

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

    gw2_f = fixtures[fixtures["gameweek_id"] == 2]
    clash_pairs = set()
    for _, f in gw2_f.iterrows():
        h_idx = id_to_idx[int(f["home_club_id"])]
        a_idx = id_to_idx[int(f["away_club_id"])]
        clash_pairs.add(frozenset([h_idx, a_idx]))

    valid_indices = []
    patterns = []
    num_uniques = []
    for i in range(len(all_5combos)):
        if combo_prices[i] > MAX_TOTAL_PRICE:
            continue
        c_counts = Counter(combo_cids[i])
        valid = True
        for cid, cnt in c_counts.items():
            c_short = idx_to_short[cid]
            if c_short in TOP_ATTACK_CLUBS and cnt > MAX_DEF_PER_TOP_CLUB:
                valid = False
                break
            elif cnt > MAX_DEF_PER_OTHER_CLUB:
                valid = False
                break
        if not valid:
            continue

        has_clash = any(
            frozenset([combo_cids[i, j], combo_cids[i, k]]) in clash_pairs
            for j in range(5)
            for k in range(j + 1, 5)
            if combo_cids[i, j] != combo_cids[i, k]
        )
        if has_clash:
            continue

        if p_all_fdrs[all_5combos[i], 1].max() > 3.0:
            continue

        valid_indices.append(i)
        p_tup = tuple(sorted(c_counts.values(), reverse=True))
        patterns.append("+".join(str(x) for x in p_tup))
        num_uniques.append(len(p_tup))

    valid_indices = np.array(valid_indices, dtype=np.int32)
    valid_bb2_combos = all_5combos[valid_indices]
    valid_bb2_prices = combo_prices[valid_indices]
    valid_cids = combo_cids[valid_indices]
    patterns_arr = np.array(patterns)
    num_uniques_arr = np.array(num_uniques, dtype=np.int32)

    corr_mat = precompute_pairwise_corr(fdr_mat[:, 0:3])
    pair_indices = list(itertools.combinations(range(5), 2))

    gw1_combo_fdr = p_all_fdrs[valid_bb2_combos, 0]
    gw1_combo_xp = p_all_xps[valid_bb2_combos, 0]
    gw1_order = np.argsort(-gw1_combo_xp, axis=1)
    gw1_top3_xp = np.take_along_axis(gw1_combo_xp, gw1_order[:, :3], axis=1).sum(axis=1)
    gw1_bench_xp = (0.12 * np.take_along_axis(gw1_combo_xp, gw1_order[:, 3:4], axis=1) + 0.03 * np.take_along_axis(gw1_combo_xp, gw1_order[:, 4:5], axis=1)).sum(axis=1)
    gw1_top3_fdr = np.take_along_axis(gw1_combo_fdr, gw1_order[:, :3], axis=1).sum(axis=1)

    gw2_xps = p_all_xps[valid_bb2_combos, 1].sum(axis=1)
    gw2_fdrs = p_all_fdrs[valid_bb2_combos, 1].mean(axis=1)

    gw3_combo_fdr = p_all_fdrs[valid_bb2_combos, 2]
    gw3_combo_xp = p_all_xps[valid_bb2_combos, 2]
    gw3_order = np.argsort(-gw3_combo_xp, axis=1)
    gw3_top3_xp = np.take_along_axis(gw3_combo_xp, gw3_order[:, :3], axis=1).sum(axis=1)
    gw3_bench_xp = (0.12 * np.take_along_axis(gw3_combo_xp, gw3_order[:, 3:4], axis=1) + 0.03 * np.take_along_axis(gw3_combo_xp, gw3_order[:, 4:5], axis=1)).sum(axis=1)
    gw3_top3_fdr = np.take_along_axis(gw3_combo_fdr, gw3_order[:, :3], axis=1).sum(axis=1)

    tot_effective_xp = (gw1_top3_xp + gw1_bench_xp) + gw2_xps + (gw3_top3_xp + gw3_bench_xp)
    gw1_3_rot_fdr = (gw1_top3_fdr + gw3_top3_fdr) / 6.0
    effective_avg_fdr = (gw1_top3_fdr + p_all_fdrs[valid_bb2_combos, 1].sum(axis=1) + gw3_top3_fdr) / 11.0

    pair_corrs = np.array([[corr_mat[valid_cids[i, a], valid_cids[i, b]] for a, b in pair_indices] for i in range(len(valid_bb2_combos))])
    avg_corrs = pair_corrs.mean(axis=1)

    gamma = compute_outfield_capital_slope(STATS_CSV, DATA_DIR / "players.parquet")
    s_xp = np.clip((tot_effective_xp - 40.0) / (75.0 - 40.0) * 100.0, 0, 100)
    s_fdr2 = np.clip((3.5 - gw2_fdrs) / (3.5 - 2.0) * 100.0, 0, 100)
    s_fdr13 = np.clip((3.5 - gw1_3_rot_fdr) / (3.5 - 2.0) * 100.0, 0, 100)
    s_eff_fdr = np.clip((3.5 - effective_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100)
    s_corr = np.clip((-avg_corrs + 1.0) / 2.0 * 100.0, 0, 100)
    s_cost = np.clip((26.0 - valid_bb2_prices) / (26.0 - 20.0) * 100.0, 0, 100)
    bb_rqi_arr = np.round(0.40 * s_xp + 0.15 * s_fdr2 + 0.10 * s_fdr13 + 0.10 * s_eff_fdr + 0.10 * s_corr + 0.15 * s_cost, 2)
    bb_oc_rqi_arr = np.round(tot_effective_xp - gamma * (valid_bb2_prices - 20.0) * 3, 3)

    band_indices: dict[int, list[int]] = {1: [], 2: [], 3: [], 4: []}
    for i in range(len(valid_bb2_combos)):
        _, b_id = classify_budget_band(float(valid_bb2_prices[i]))
        band_indices[b_id].append(i)

    selected_indices = set()
    for b_id, idx_list in band_indices.items():
        if not idx_list:
            continue
        sub_rqi = bb_rqi_arr[idx_list]
        sub_xp = tot_effective_xp[idx_list]
        top_rqi_idx = [idx_list[k] for k in np.argsort(-sub_rqi)[:1000]]
        top_xp_idx = [idx_list[k] for k in np.argsort(-sub_xp)[:200]]
        selected_indices.update(top_rqi_idx)
        selected_indices.update(top_xp_idx)

    rows: list[dict] = []
    for i in selected_indices:
        tot_p = float(valid_bb2_prices[i])
        band_name, band_id = classify_budget_band(tot_p)
        avg_corr = float(avg_corrs[i])

        p_objs = [player_meta[pids[idx]] for idx in valid_bb2_combos[i]]
        rows.append(
            {
                "tier": band_name,
                "tier_id": band_id,
                "num_unique_clubs": int(num_uniques_arr[i]),
                "allocation_pattern": str(patterns_arr[i]),
                "lineup_summary": " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs),
                "clubs": "-".join(p["club_short"] for p in p_objs),
                "total_price": round(tot_p, 1),
                "bb_rqi": float(bb_rqi_arr[i]),
                "bb_oc_rqi": float(bb_oc_rqi_arr[i]),
                "tot_effective_xp": round(float(tot_effective_xp[i]), 2),
                "gw2_xp_5def": round(float(gw2_xps[i]), 2),
                "gw1_3_xp_6def": round(float(gw1_top3_xp[i] + gw3_top3_xp[i]), 2),
                "gw2_avg_fdr": round(float(gw2_fdrs[i]), 2),
                "gw1_3_rot_fdr": round(float(gw1_3_rot_fdr[i]), 2),
                "effective_avg_fdr": round(float(effective_avg_fdr[i]), 4),
                "avg_fdr_corr": round(avg_corr, 4),
            }
        )

    return pd.DataFrame(rows)


def club_slot_hamming(pre_clubs: str, post_clubs: str) -> int:
    """Defender-slot Hamming distance: 5 minus multiset overlap of hyphenated club codes."""
    pre_counts = Counter(pre_clubs.split("-"))
    post_counts = Counter(post_clubs.split("-"))
    return 5 - sum((pre_counts & post_counts).values())


def path_effective_fdr(gw13_eff_fdr: float, gw419_rot_fdr: float) -> float:
    """Starter-weighted FDR across BB1 11 starts + GW4-19 48 rotated starts."""
    return (11.0 * gw13_eff_fdr + 48.0 * gw419_rot_fdr) / 59.0


def bridge_destination_key(
    *,
    post_no_diff_pct: float,
    path_fdr: float,
    post_rot_fdr: float,
    post_corr: float,
    post_easy_pct: float,
    gw1_avg_fdr: float,
    n_swaps: int,
    pre_eff_fdr: float,
    post_j: int,
) -> tuple[object, ...]:
    """Lower tuple wins. Correlation-first among equal path / dest FDR / zero-diff."""
    return (
        -post_no_diff_pct,
        round(path_fdr, 6),
        post_rot_fdr,
        post_corr,
        -post_easy_pct,
        gw1_avg_fdr,
        n_swaps,
        pre_eff_fdr,
        post_j,
    )


def _club_count_matrix(club_strings: pd.Series, club_index: dict[str, int]) -> np.ndarray:
    mat = np.zeros((len(club_strings), len(club_index)), dtype=np.int8)
    for i, raw in enumerate(club_strings):
        for code in str(raw).split("-"):
            mat[i, club_index[code]] += 1
    return mat


def run_wc4_bridge_analysis(
    bb1_clubs: pd.DataFrame,
    club_5way: pd.DataFrame,
    *,
    sun_counts: frozenset[int] | None = None,
) -> pd.DataFrame:
    """Best 1-2 slot WC4 destination for each 4-5 unique GW1-3 BB1 set.

    Pre-sets come from the BB1 clash-free matrix. Post-sets are GW4-19 4-5 unique
    club combinations. One destination per pre-set: 100% zero-diff first, then
    path FDR (11 GW1-3 starts + 48 GW4-19 starts), then dest rot FDR, then
    dest correlation-first (more negative wins), then easy%, GW1 FDR, fewer swaps.
    If sun_counts is set, keep only pre-sets whose SUN slot count is in that set.
    """
    pre = bb1_clubs[bb1_clubs["num_unique_clubs"].isin([4, 5])].copy()
    pre["pre_sun"] = pre["clubs"].map(lambda s: Counter(str(s).split("-"))["SUN"])
    if sun_counts is not None:
        pre = pre[pre["pre_sun"].isin(sun_counts)].reset_index(drop=True)
    else:
        pre = pre.reset_index(drop=True)
    post = club_5way[
        (club_5way["horizon"] == "gw4_19") & (club_5way["num_unique_clubs"].isin([4, 5]))
    ].reset_index(drop=True)
    if pre.empty or post.empty:
        return pd.DataFrame()

    all_codes = sorted({c for raw in list(pre["clubs"]) + list(post["clubs"]) for c in str(raw).split("-")})
    club_index = {code: i for i, code in enumerate(all_codes)}
    pre_mat = _club_count_matrix(pre["clubs"], club_index)
    post_mat = _club_count_matrix(post["clubs"], club_index)
    sun_col = club_index["SUN"]

    pre_eff = pre["effective_avg_fdr"].to_numpy()
    pre_gw1 = pre["gw1_avg_fdr"].to_numpy()
    pre_gw23 = pre["gw2_3_rot_fdr"].to_numpy()
    pre_corr = pre["avg_fdr_corr"].to_numpy()
    pre_unique = pre["num_unique_clubs"].to_numpy()
    pre_pattern = pre["allocation_pattern"].to_numpy()
    pre_sun = pre["pre_sun"].to_numpy()
    pre_names = pre["clubs"].to_numpy()

    post_fdr = post["rot_avg_fdr"].to_numpy()
    post_nd = post["no_diff_pct"].to_numpy()
    post_easy = post["all_easy_pct"].to_numpy()
    post_corr = post["avg_fdr_corr"].to_numpy()
    post_unique = post["num_unique_clubs"].to_numpy()
    post_pattern = post["allocation_pattern"].to_numpy()
    post_names = post["clubs"].to_numpy()

    n_pre = len(pre_mat)
    n_post = len(post_mat)
    best: list[tuple[object, ...] | None] = [None] * n_pre
    chunk = 4000
    for start in range(0, n_post, chunk):
        post_chunk = post_mat[start : start + chunk]
        ham = (np.abs(pre_mat[:, None, :] - post_chunk[None, :, :]).sum(axis=2) // 2).astype(np.int8)
        rows, cols = np.where((ham == 1) | (ham == 2))
        for pre_i, local_j in zip(rows.tolist(), cols.tolist()):
            post_j = start + int(local_j)
            n_swaps = int(ham[pre_i, local_j])
            path = path_effective_fdr(float(pre_eff[pre_i]), float(post_fdr[post_j]))
            key = bridge_destination_key(
                post_no_diff_pct=float(post_nd[post_j]),
                path_fdr=path,
                post_rot_fdr=float(post_fdr[post_j]),
                post_corr=float(post_corr[post_j]),
                post_easy_pct=float(post_easy[post_j]),
                gw1_avg_fdr=float(pre_gw1[pre_i]),
                n_swaps=n_swaps,
                pre_eff_fdr=float(pre_eff[pre_i]),
                post_j=post_j,
            )
            if best[pre_i] is None or key < best[pre_i]:
                best[pre_i] = key

    records: list[dict] = []
    for pre_i, key in enumerate(best):
        if key is None:
            continue
        _nd, path, _post_fdr, _corr, _easy, _gw1, n_swaps, _eff, post_j = key
        pre_set = str(pre_names[pre_i])
        post_set = str(post_names[post_j])
        out_clubs = ",".join(sorted((Counter(pre_set.split("-")) - Counter(post_set.split("-"))).elements()))
        in_clubs = ",".join(sorted((Counter(post_set.split("-")) - Counter(pre_set.split("-"))).elements()))
        records.append(
            {
                "pre_clubs": pre_set,
                "pre_unique": int(pre_unique[pre_i]),
                "pre_pattern": str(pre_pattern[pre_i]),
                "pre_sun": int(pre_sun[pre_i]),
                "gw13_eff_fdr": round(float(pre_eff[pre_i]), 4),
                "gw1_avg_fdr": round(float(pre_gw1[pre_i]), 2),
                "gw23_rot_fdr": round(float(pre_gw23[pre_i]), 2),
                "pre_corr": round(float(pre_corr[pre_i]), 4),
                "n_swaps": int(n_swaps),
                "out_clubs": out_clubs,
                "in_clubs": in_clubs,
                "post_clubs": post_set,
                "post_unique": int(post_unique[post_j]),
                "post_pattern": str(post_pattern[post_j]),
                "post_sun": int(post_mat[post_j, sun_col]),
                "gw419_rot_fdr": round(float(post_fdr[post_j]), 4),
                "gw419_no_diff_pct": round(float(post_nd[post_j]), 1),
                "gw419_all_easy_pct": round(float(post_easy[post_j]), 1),
                "post_corr": round(float(post_corr[post_j]), 4),
                "path_eff_fdr": round(float(path), 6),
            }
        )

    df = pd.DataFrame(records)
    if df.empty:
        return df

    eligible = (
        (df["gw13_eff_fdr"] <= 2.3636)
        & (df["gw1_avg_fdr"] <= 2.4)
        & (df["gw419_no_diff_pct"] >= 100.0)
    )
    df["scenario_eligible"] = eligible
    ranked = df.loc[eligible].sort_values(
        BRIDGE_RANK_SORT_COLS,
        ascending=BRIDGE_RANK_SORT_ASC,
    )
    rank_map = {idx: rank for rank, idx in enumerate(ranked.index, start=1)}
    df["scenario_rank"] = df.index.map(rank_map)
    return df.sort_values(
        ["scenario_eligible", "scenario_rank", "path_eff_fdr"],
        ascending=[False, True, True],
        na_position="last",
    ).reset_index(drop=True)


def run_wc4_sun_bridge_analysis(bb1_clubs: pd.DataFrame, club_5way: pd.DataFrame) -> pd.DataFrame:
    """GW1-3 4-5 unique sets holding 1-2 Sunderland, 1-2 WC4 slot swaps."""
    return run_wc4_bridge_analysis(bb1_clubs, club_5way, sun_counts=frozenset({1, 2}))


def run_wc4_overall_bridge_analysis(bb1_clubs: pd.DataFrame, club_5way: pd.DataFrame) -> pd.DataFrame:
    """GW1-3 4-5 unique sets, no club filter, 1-2 WC4 slot swaps."""
    return run_wc4_bridge_analysis(bb1_clubs, club_5way, sun_counts=None)


def _write_bridge_csvs(bb1_clubs: pd.DataFrame, club_5way: pd.DataFrame, *, sun: bool, overall: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if sun:
        df_sun = run_wc4_sun_bridge_analysis(bb1_clubs, club_5way)
        df_sun.to_csv(OUT_DIR / "def_wc4_sun_bridge_matrix.csv", index=False)
        print(f"Wrote {OUT_DIR / 'def_wc4_sun_bridge_matrix.csv'} ({len(df_sun)} rows)")
    if overall:
        df_all = run_wc4_overall_bridge_analysis(bb1_clubs, club_5way)
        df_all.to_csv(OUT_DIR / "def_wc4_overall_bridge_matrix.csv", index=False)
        print(f"Wrote {OUT_DIR / 'def_wc4_overall_bridge_matrix.csv'} ({len(df_all)} rows)")


def apply_ranking_sorts(
    df_club_5way: pd.DataFrame,
    df_bb1_clubs: pd.DataFrame,
    df_bb2_clubs: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame] | tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply published ranking lenses. Correlation-first after primary FDR keys."""
    club_sorted = df_club_5way.sort_values(
        CLUB_5WAY_SORT_COLS, ascending=CLUB_5WAY_SORT_ASC
    ).reset_index(drop=True)
    bb1_sorted = df_bb1_clubs.sort_values(
        BB1_CLUB_SORT_COLS, ascending=BB1_CLUB_SORT_ASC
    ).reset_index(drop=True)
    if df_bb2_clubs is not None:
        bb2_sorted = df_bb2_clubs.sort_values(
            BB2_CLUB_SORT_COLS, ascending=BB2_CLUB_SORT_ASC
        ).reset_index(drop=True)
        return club_sorted, bb1_sorted, bb2_sorted
    return club_sorted, bb1_sorted


def print_rank_tables(
    df_club_5way: pd.DataFrame,
    df_bb1_clubs: pd.DataFrame,
    df_bb2_clubs: pd.DataFrame | None = None,
) -> None:
    """Print Top-10 blocks used by the research notes (correlation-first GW4-19)."""
    def _top(frame: pd.DataFrame, n: int, cols: list[str]) -> None:
        for i, row in enumerate(frame.head(n).itertuples(), 1):
            bits = " ".join(f"{c}={getattr(row, c)}" for c in cols)
            print(f"  {i:2d} {row.clubs} {bits}")

    if df_bb2_clubs is not None:
        print("=== BB2 4 unique (eff FDR lens) ===")
        b2_4 = df_bb2_clubs[df_bb2_clubs["num_unique_clubs"] == 4]
        _top(b2_4, 10, ["effective_avg_fdr", "gw2_avg_fdr", "gw1_3_rot_fdr", "avg_fdr_corr"])
        print("=== BB2 5 unique (eff FDR lens) ===")
        b2_5 = df_bb2_clubs[df_bb2_clubs["num_unique_clubs"] == 5]
        _top(b2_5, 10, ["effective_avg_fdr", "gw2_avg_fdr", "gw1_3_rot_fdr", "avg_fdr_corr"])

    print("=== BB1 4 unique (eff FDR lens) ===")
    b4 = df_bb1_clubs[df_bb1_clubs["num_unique_clubs"] == 4]
    _top(b4, 10, ["effective_avg_fdr", "gw1_avg_fdr", "gw2_3_rot_fdr", "avg_fdr_corr"])
    print("=== GW4-19 5 unique (corr-first after rot FDR) ===")
    g = df_club_5way[
        (df_club_5way["horizon"] == "gw4_19") & (df_club_5way["num_unique_clubs"] == 5)
    ]
    _top(g, 10, ["rot_avg_fdr", "no_diff_pct", "all_easy_pct", "avg_fdr_corr"])
    print("=== GW1-19 5 unique ===")
    g19 = df_club_5way[
        (df_club_5way["horizon"] == "gw1_19") & (df_club_5way["num_unique_clubs"] == 5)
    ]
    _top(g19, 10, ["rot_avg_fdr", "no_diff_pct", "all_easy_pct", "avg_fdr_corr"])


def run_def_rotation_pipeline() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Execute complete DEF rotation analysis and write CSV artifacts."""
    print("Loading data...")
    players = pd.read_parquet(DATA_DIR / "players.parquet")
    clubs = pd.read_parquet(DATA_DIR / "clubs.parquet")
    fixtures = pd.read_parquet(DATA_DIR / "fixtures.parquet")
    df_stats = pd.read_csv(STATS_CSV)

    cost_map = players.set_index("id")["now_cost"] / 10.0
    club_map = players.set_index("id")["club_id"]

    df_stats["price"] = df_stats["player_id"].map(cost_map)
    df_stats["club_id"] = df_stats["player_id"].map(club_map)

    starters = df_stats[
        (df_stats["position"] == "DEF")
        & (df_stats["expected_role"].isin(DRAFT_ROLES))
        & (df_stats["draft_availability"] == "eligible")
    ].dropna(subset=["price", "club_id"]).copy()

    fmap = _fixture_maps(fixtures, clubs, list(range(1, 39)))
    fdr_mat, idx_to_short, id_to_idx = build_club_fdr_matrix(fixtures, clubs)

    print(f"Loaded {len(starters)} starter defenders across {starters['club_short'].nunique()} clubs.")
    print("Running multi-club combinatorial analysis across 41,344 combinations...")
    df_club_5way = run_5club_combinatorial_analysis(fdr_mat, idx_to_short)

    print("Projecting weekly hybrid xP for all starting defenders...")
    gw_xp = project_starter_def_grid(starters, fmap, end_gw=38)

    print("Simulating flexible 5-DEF player combinations (up to £26.0m across 2-5 unique clubs)...")
    df_tiers = simulate_player_tier_combinations(starters, gw_xp, fdr_mat, id_to_idx, idx_to_short)

    print("Simulating specialized GW1 BB + GW4 WC pre-wildcard scenario (up to £26.0m across 2-5 unique clubs)...")
    df_bb1_clubs = run_bb1_wc4_club_combinatorial_analysis(fdr_mat, idx_to_short, fixtures, id_to_idx)
    df_bb1_tiers = simulate_bb1_wc4_player_tier_combinations(starters, gw_xp, fdr_mat, id_to_idx, idx_to_short, fixtures)

    print("Simulating specialized GW2 BB + GW4 WC pre-wildcard scenario (up to £26.0m across 2-5 unique clubs)...")
    df_bb2_clubs = run_bb2_wc4_club_combinatorial_analysis(fdr_mat, idx_to_short, fixtures, id_to_idx)
    df_bb2_tiers = simulate_bb2_wc4_player_tier_combinations(starters, gw_xp, fdr_mat, id_to_idx, idx_to_short, fixtures)

    baseline = starters[
        [
            "player_id",
            "web_name",
            "club_short",
            "price",
            "expected_role",
            "per90_xg",
            "per90_xa",
            "per90_defcon",
            "per90_goals_conceded",
            "rate_source",
            "usable_mins_total",
        ]
    ].copy()
    baseline = baseline.sort_values(["price", "per90_defcon", "web_name"], ascending=[False, False, True]).reset_index(drop=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df_club_5way, df_bb1_clubs, df_bb2_clubs = apply_ranking_sorts(df_club_5way, df_bb1_clubs, df_bb2_clubs)
    df_tiers = df_tiers.sort_values(
        ["horizon", "tier_id", "oc_rqi", "tot_rot_xp"],
        ascending=[True, True, False, False],
    ).reset_index(drop=True)
    df_bb1_tiers = df_bb1_tiers.sort_values(
        ["tier_id", "bb_oc_rqi", "tot_effective_xp"],
        ascending=[True, False, False],
    ).reset_index(drop=True)
    df_bb2_tiers = df_bb2_tiers.sort_values(
        ["tier_id", "bb_oc_rqi", "tot_effective_xp"],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    df_club_5way.to_csv(OUT_DIR / "def_club_5way_rotation_matrix.csv", index=False)
    df_tiers.to_csv(OUT_DIR / "def_tier_player_rotations.csv", index=False)
    df_bb1_clubs.to_csv(OUT_DIR / "def_bb1_wc4_club_matrix.csv", index=False)
    df_bb1_tiers.to_csv(OUT_DIR / "def_bb1_wc4_tier_lineups.csv", index=False)
    df_bb2_clubs.to_csv(OUT_DIR / "def_bb2_wc4_club_matrix.csv", index=False)
    df_bb2_tiers.to_csv(OUT_DIR / "def_bb2_wc4_tier_lineups.csv", index=False)
    baseline.to_csv(OUT_DIR / "def_performance_baseline.csv", index=False)

    print(f"Analysis complete. Outputs written to {OUT_DIR}:")
    print(f" - def_club_5way_rotation_matrix.csv ({len(df_club_5way)} rows)")
    print(f" - def_tier_player_rotations.csv ({len(df_tiers)} rows)")
    print(f" - def_bb1_wc4_club_matrix.csv ({len(df_bb1_clubs)} rows)")
    print(f" - def_bb1_wc4_tier_lineups.csv ({len(df_bb1_tiers)} rows)")
    print(f" - def_bb2_wc4_club_matrix.csv ({len(df_bb2_clubs)} rows)")
    print(f" - def_bb2_wc4_tier_lineups.csv ({len(df_bb2_tiers)} rows)")
    print(f" - def_performance_baseline.csv ({len(baseline)} rows)")

    return df_club_5way, df_tiers, df_bb1_clubs, df_bb1_tiers, df_bb2_clubs, df_bb2_tiers, baseline


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="5-DEF fixture rotation analysis")
    parser.add_argument(
        "--sun-bridge-only",
        action="store_true",
        help="Rebuild def_wc4_sun_bridge_matrix.csv from existing club CSVs",
    )
    parser.add_argument(
        "--overall-bridge-only",
        action="store_true",
        help="Rebuild def_wc4_overall_bridge_matrix.csv from existing club CSVs",
    )
    parser.add_argument(
        "--bridges-only",
        action="store_true",
        help="Rebuild both WC4 bridge CSVs from existing club CSVs",
    )
    parser.add_argument(
        "--print-ranks",
        action="store_true",
        help="Print Top-10 ranking blocks from existing CSVs (no combinatorics)",
    )
    args = parser.parse_args()
    if args.print_ranks:
        club_5way = pd.read_csv(OUT_DIR / "def_club_5way_rotation_matrix.csv")
        bb1 = pd.read_csv(OUT_DIR / "def_bb1_wc4_club_matrix.csv")
        bb2 = pd.read_csv(OUT_DIR / "def_bb2_wc4_club_matrix.csv") if (OUT_DIR / "def_bb2_wc4_club_matrix.csv").exists() else None
        res = apply_ranking_sorts(club_5way, bb1, bb2)
        if bb2 is not None:
            c_sorted, b1_sorted, b2_sorted = res
            print_rank_tables(c_sorted, b1_sorted, b2_sorted)
        else:
            c_sorted, b1_sorted = res
            print_rank_tables(c_sorted, b1_sorted)
        raise SystemExit(0)
    bridge_only = args.sun_bridge_only or args.overall_bridge_only or args.bridges_only
    if bridge_only:
        bb1 = pd.read_csv(OUT_DIR / "def_bb1_wc4_club_matrix.csv")
        club_5way = pd.read_csv(OUT_DIR / "def_club_5way_rotation_matrix.csv")
        bb2 = pd.read_csv(OUT_DIR / "def_bb2_wc4_club_matrix.csv") if (OUT_DIR / "def_bb2_wc4_club_matrix.csv").exists() else None
        if bb2 is not None:
            club_5way, bb1, bb2 = apply_ranking_sorts(club_5way, bb1, bb2)
            bb2.to_csv(OUT_DIR / "def_bb2_wc4_club_matrix.csv", index=False)
        else:
            club_5way, bb1 = apply_ranking_sorts(club_5way, bb1)
        club_5way.to_csv(OUT_DIR / "def_club_5way_rotation_matrix.csv", index=False)
        bb1.to_csv(OUT_DIR / "def_bb1_wc4_club_matrix.csv", index=False)
        write_sun = args.sun_bridge_only or args.bridges_only
        write_overall = args.overall_bridge_only or args.bridges_only
        if args.bridges_only:
            write_sun = True
            write_overall = True
        _write_bridge_csvs(bb1, club_5way, sun=write_sun, overall=write_overall)
    else:
        run_def_rotation_pipeline()
