"""Starter Defender (5 DEF) Fixture Rotation & Diversification Analysis.

Simulates 5 DEF diversification and fixture rotation across:
1. Long-term horizons: GW1-3, GW4-19, GW1-19, and full season.
2. Flexible Budget Spectrum (at most £26.0m):
   - Band 1: Budget (£20.5m–£22.5m)
   - Band 2: Mid-Value (£23.0m–£24.0m)
   - Band 3: Single Anchor (£24.5m–£25.0m)
   - Band 4: Premium / Dual Anchor (£25.5m–£26.0m)
3. Specialized Pre-Wildcard Scenario: GW1 Bench Boost (BB1) + GW4 Wildcard (WC4).
   - GW1: All 5 defenders start on Bench Boost (Zero Head-to-Head Clashes, max FDR <= 3.0).
   - GW2 & GW3: Best 3 defenders rotate by lowest FDR / highest xP.
   - GW4: Full Wildcard reset.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from features.builder import _fixture_maps
from models.participation_state_hybrid import ParticipationStateHybridModel

DATA_DIR = PROJECT_ROOT / "data" / "processed"
RESEARCH_DIR = PROJECT_ROOT / "data" / "research"
OUT_DIR = RESEARCH_DIR / "def-fixture-rotation"
STATS_CSV = RESEARCH_DIR / "gw1-6-preseason-pipeline" / "02-expected-stats-gw1-5" / "expected-stats-gw1-5.csv"
ROLE_CSV = RESEARCH_DIR / "gw1-6-preseason-pipeline" / "01-expected-role-gw1-5" / "expected-role-gw1-5.csv"

DRAFT_ROLES = ("Nailed Starter", "Regular Starter")
FLAT_START_MINUTES = 90.0
DEF_POSITION_ID = 2
MAX_TOTAL_PRICE = 26.0

HORIZONS = (
    ("gw1_3", 1, 3),
    ("gw4_19", 4, 19),
    ("gw1_19", 1, 19),
    ("full_season", 1, 38),
)


def compute_def_rqi(
    *,
    tot_rot_xp: float,
    num_gws: int,
    rot_avg_fdr: float,
    no_diff_pct: float,
    fdr_corr: float,
    total_price: float,
) -> float:
    """DEF Rotation Quality Index (0-100 scale)."""
    rot_xp_per_gw = tot_rot_xp / num_gws
    s_xp = float(np.clip((rot_xp_per_gw - 9.0) / (16.5 - 9.0) * 100.0, 0, 100))
    s_fdr = float(np.clip((3.5 - rot_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100))
    s_no_diff = float(np.clip(no_diff_pct, 0, 100))
    s_corr = float(np.clip((-fdr_corr + 1.0) / 2.0 * 100.0, 0, 100))
    s_cost = float(np.clip((28.0 - total_price) / (28.0 - 20.0) * 100.0, 0, 100))

    score = 0.35 * s_xp + 0.25 * s_fdr + 0.15 * s_no_diff + 0.15 * s_corr + 0.10 * s_cost
    return round(score, 2)


def compute_bb_rqi(
    *,
    tot_effective_xp: float,
    gw1_avg_fdr: float,
    gw2_3_rot_fdr: float,
    effective_avg_fdr: float,
    avg_corr: float,
    total_price: float,
) -> float:
    """Bench Boost Rotation Quality Index (BB-RQI, 0-100 scale) for 11 starter-matches."""
    s_xp = float(np.clip((tot_effective_xp - 38.0) / (60.0 - 38.0) * 100.0, 0, 100))
    s_fdr1 = float(np.clip((3.5 - gw1_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100))
    s_fdr23 = float(np.clip((3.5 - gw2_3_rot_fdr) / (3.5 - 2.0) * 100.0, 0, 100))
    s_eff_fdr = float(np.clip((3.5 - effective_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100))
    s_corr = float(np.clip((-avg_corr + 1.0) / 2.0 * 100.0, 0, 100))
    s_cost = float(np.clip((28.0 - total_price) / (28.0 - 20.0) * 100.0, 0, 100))

    score = 0.40 * s_xp + 0.15 * s_fdr1 + 0.10 * s_fdr23 + 0.10 * s_eff_fdr + 0.10 * s_corr + 0.15 * s_cost
    return round(score, 2)


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
    corr_mat = np.zeros((n_clubs, n_clubs), dtype=float)
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


def run_5club_combinatorial_analysis(fdr_mat: np.ndarray, idx_to_short: dict[int, str]) -> pd.DataFrame:
    """Evaluate all 15,504 5-club combinations across standard horizons."""
    combos = list(itertools.combinations(range(20), 5))
    pair_indices = list(itertools.combinations(range(5), 2))
    all_rows: list[dict] = []

    for h_name, start_gw, end_gw in HORIZONS:
        gw_indices = list(range(start_gw - 1, end_gw))
        n_gws = len(gw_indices)
        h_fdr = fdr_mat[:, gw_indices]
        corr_mat = precompute_pairwise_corr(h_fdr)

        for c in combos:
            sub = h_fdr[list(c), :]
            sorted_sub = np.sort(sub, axis=0)
            top3 = sorted_sub[:3, :]
            rot_avg_fdr = float(top3.mean())
            worst_starter_each_gw = sorted_sub[2, :]
            max_worst_starter = float(worst_starter_each_gw.max())
            no_diff_gws = int(np.sum(worst_starter_each_gw <= 3.0))
            all_easy_gws = int(np.sum(worst_starter_each_gw <= 2.0))

            corrs = [corr_mat[c[i], c[j]] for i, j in pair_indices]
            avg_corr = float(np.mean(corrs)) if corrs else 0.0

            club_shorts = [idx_to_short[x] for x in c]

            all_rows.append(
                {
                    "horizon": h_name,
                    "start_gw": start_gw,
                    "end_gw": end_gw,
                    "num_gws": n_gws,
                    "clubs": "-".join(club_shorts),
                    "club1": club_shorts[0],
                    "club2": club_shorts[1],
                    "club3": club_shorts[2],
                    "club4": club_shorts[3],
                    "club5": club_shorts[4],
                    "rot_avg_fdr": round(rot_avg_fdr, 4),
                    "max_worst_starter": round(max_worst_starter, 1),
                    "no_diff_gws": no_diff_gws,
                    "no_diff_pct": round(no_diff_gws / n_gws * 100.0, 1),
                    "all_easy_gws": all_easy_gws,
                    "all_easy_pct": round(all_easy_gws / n_gws * 100.0, 1),
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

    combos = list(itertools.combinations(range(20), 5))
    pair_indices = list(itertools.combinations(range(5), 2))
    corr_mat = precompute_pairwise_corr(fdr_mat[:, 0:3])

    rows: list[dict] = []
    for c in combos:
        has_clash = any(frozenset([c[i], c[j]]) in clash_pairs for i in range(5) for j in range(i + 1, 5))
        if has_clash:
            continue

        # GW1: all 5 start
        gw1_fdrs = fdr_mat[list(c), 0]
        gw1_max_fdr = float(gw1_fdrs.max())
        if gw1_max_fdr > 3.0:  # Strict ceiling rule
            continue
        gw1_avg_fdr = float(gw1_fdrs.mean())

        # GW2 and GW3: top 3 start
        gw2_fdrs = np.sort(fdr_mat[list(c), 1])[:3]
        gw3_fdrs = np.sort(fdr_mat[list(c), 2])[:3]
        gw2_avg_fdr = float(gw2_fdrs.mean())
        gw3_avg_fdr = float(gw3_fdrs.mean())
        gw2_3_rot_fdr = float((gw2_fdrs.sum() + gw3_fdrs.sum()) / 6.0)

        tot_effective_fdr = float(gw1_fdrs.sum() + gw2_fdrs.sum() + gw3_fdrs.sum())
        effective_avg_fdr = tot_effective_fdr / 11.0

        corrs = [corr_mat[c[i], c[j]] for i, j in pair_indices]
        avg_corr = float(np.mean(corrs)) if corrs else 0.0

        club_shorts = [idx_to_short[x] for x in c]

        rows.append(
            {
                "clubs": "-".join(club_shorts),
                "club1": club_shorts[0],
                "club2": club_shorts[1],
                "club3": club_shorts[2],
                "club4": club_shorts[3],
                "club5": club_shorts[4],
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

    distinct_mask = np.array([len(set(combo_cids[i])) == 5 for i in range(len(all_5combos))], dtype=bool)
    price_mask = combo_prices <= MAX_TOTAL_PRICE
    valid_mask = distinct_mask & price_mask
    valid_5combos = all_5combos[valid_mask]
    valid_prices = combo_prices[valid_mask]
    valid_cids = combo_cids[valid_mask]

    all_tier_rows: list[dict] = []
    pair_indices = list(itertools.combinations(range(5), 2))

    for h_name, start_gw, end_gw in HORIZONS:
        gw_indices = list(range(start_gw - 1, end_gw))
        n_gws = len(gw_indices)
        h_fdr = fdr_mat[:, gw_indices]
        corr_mat = precompute_pairwise_corr(h_fdr)

        combo_fdr = p_all_fdrs[valid_5combos][:, :, gw_indices]
        combo_xp = p_all_xps[valid_5combos][:, :, gw_indices]

        sort_key = combo_fdr - combo_xp * 1e-4
        top3_idx = np.argsort(sort_key, axis=1)[:, :3, :]
        top3_fdr = np.take_along_axis(combo_fdr, top3_idx, axis=1)
        top3_xp = np.take_along_axis(combo_xp, top3_idx, axis=1)

        tot_rot_xp = top3_xp.sum(axis=(1, 2))
        rot_avg_fdr = top3_fdr.mean(axis=(1, 2))
        worst_starter = top3_fdr.max(axis=1)
        no_diff_gws = (worst_starter <= 3.0).sum(axis=1)
        no_diff_pct = no_diff_gws / float(n_gws) * 100.0
        max_worst_starter = worst_starter.max(axis=1)

        top3_xp_order = np.argsort(-combo_xp, axis=1)[:, :3, :]
        tot_max_xp = np.take_along_axis(combo_xp, top3_xp_order, axis=1).sum(axis=(1, 2))

        # Vectorized RQI
        s_xp = np.clip((tot_rot_xp / float(n_gws) - 9.0) / (16.5 - 9.0) * 100.0, 0, 100)
        s_fdr = np.clip((3.5 - rot_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100)
        s_no_diff = np.clip(no_diff_pct, 0, 100)
        s_cost = np.clip((28.0 - valid_prices) / (28.0 - 20.0) * 100.0, 0, 100)
        rqi_arr = np.round(0.35 * s_xp + 0.25 * s_fdr + 0.15 * s_no_diff + 0.10 * s_cost, 2)

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
            avg_corr = float(np.mean([corr_mat[valid_cids[i, a], valid_cids[i, b]] for a, b in pair_indices]))

            p_objs = [player_meta[pids[idx]] for idx in valid_5combos[i]]
            all_tier_rows.append(
                {
                    "tier": band_name,
                    "tier_id": band_id,
                    "horizon": h_name,
                    "start_gw": start_gw,
                    "end_gw": end_gw,
                    "num_gws": n_gws,
                    "lineup_summary": " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs),
                    "clubs": "-".join(p["club_short"] for p in p_objs),
                    "total_price": round(tot_p, 1),
                    "rqi": float(rqi_arr[i]),
                    "tot_rot_xp": round(float(tot_rot_xp[i]), 2),
                    "tot_rot_xp_maxxp": round(float(tot_max_xp[i]), 2),
                    "maxxp_delta": round(float(tot_max_xp[i] - tot_rot_xp[i]), 2),
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

    distinct_mask = np.array([len(set(combo_cids[i])) == 5 for i in range(len(all_5combos))], dtype=bool)
    price_mask = combo_prices <= MAX_TOTAL_PRICE

    no_clash_mask = np.array([
        not any(frozenset([combo_cids[i, j], combo_cids[i, k]]) in clash_pairs for j in range(5) for k in range(j + 1, 5))
        for i in range(len(all_5combos))
    ], dtype=bool)

    gw1_max_fdr_mask = np.array([
        p_all_fdrs[all_5combos[i], 0].max() <= 3.0
        for i in range(len(all_5combos))
    ], dtype=bool)

    valid_bb1_mask = distinct_mask & price_mask & no_clash_mask & gw1_max_fdr_mask
    valid_bb1_combos = all_5combos[valid_bb1_mask]
    valid_bb1_prices = combo_prices[valid_bb1_mask]
    valid_cids = combo_cids[valid_bb1_mask]

    corr_mat = precompute_pairwise_corr(fdr_mat[:, 0:3])
    pair_indices = list(itertools.combinations(range(5), 2))

    gw1_xps = p_all_xps[valid_bb1_combos, 0].sum(axis=1)
    gw1_fdrs = p_all_fdrs[valid_bb1_combos, 0].mean(axis=1)

    gw2_combo_fdr = p_all_fdrs[valid_bb1_combos, 1]
    gw2_combo_xp = p_all_xps[valid_bb1_combos, 1]
    gw2_order = np.argsort(gw2_combo_fdr - gw2_combo_xp * 1e-4, axis=1)[:, :3]
    gw2_top3_xp = np.take_along_axis(gw2_combo_xp, gw2_order, axis=1).sum(axis=1)
    gw2_top3_fdr = np.take_along_axis(gw2_combo_fdr, gw2_order, axis=1).sum(axis=1)

    gw3_combo_fdr = p_all_fdrs[valid_bb1_combos, 2]
    gw3_combo_xp = p_all_xps[valid_bb1_combos, 2]
    gw3_order = np.argsort(gw3_combo_fdr - gw3_combo_xp * 1e-4, axis=1)[:, :3]
    gw3_top3_xp = np.take_along_axis(gw3_combo_xp, gw3_order, axis=1).sum(axis=1)
    gw3_top3_fdr = np.take_along_axis(gw3_combo_fdr, gw3_order, axis=1).sum(axis=1)

    tot_effective_xp = gw1_xps + gw2_top3_xp + gw3_top3_xp
    gw2_3_rot_fdr = (gw2_top3_fdr + gw3_top3_fdr) / 6.0
    effective_avg_fdr = (p_all_fdrs[valid_bb1_combos, 0].sum(axis=1) + gw2_top3_fdr + gw3_top3_fdr) / 11.0

    s_xp = np.clip((tot_effective_xp - 38.0) / (60.0 - 38.0) * 100.0, 0, 100)
    s_fdr1 = np.clip((3.5 - gw1_fdrs) / (3.5 - 2.0) * 100.0, 0, 100)
    s_eff_fdr = np.clip((3.5 - effective_avg_fdr) / (3.5 - 2.0) * 100.0, 0, 100)
    s_cost = np.clip((28.0 - valid_bb1_prices) / (28.0 - 20.0) * 100.0, 0, 100)
    bb_rqi_arr = np.round(0.40 * s_xp + 0.15 * s_fdr1 + 0.20 * s_eff_fdr + 0.15 * s_cost, 2)

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
        avg_corr = float(np.mean([corr_mat[valid_cids[i, a], valid_cids[i, b]] for a, b in pair_indices]))

        p_objs = [player_meta[pids[idx]] for idx in valid_bb1_combos[i]]
        rows.append(
            {
                "tier": band_name,
                "tier_id": band_id,
                "lineup_summary": " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs),
                "clubs": "-".join(p["club_short"] for p in p_objs),
                "total_price": round(tot_p, 1),
                "bb_rqi": float(bb_rqi_arr[i]),
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


def run_def_rotation_pipeline() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
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
    print("Running 5-club combinatorial analysis across 15,504 combinations...")
    df_club_5way = run_5club_combinatorial_analysis(fdr_mat, idx_to_short)

    print("Projecting weekly hybrid xP for all starting defenders...")
    gw_xp = project_starter_def_grid(starters, fmap, end_gw=38)

    print("Simulating flexible 5-DEF player combinations (up to £26.0m)...")
    df_tiers = simulate_player_tier_combinations(starters, gw_xp, fdr_mat, id_to_idx)

    print("Simulating specialized GW1 BB + GW4 WC pre-wildcard scenario (up to £26.0m)...")
    df_bb1_clubs = run_bb1_wc4_club_combinatorial_analysis(fdr_mat, idx_to_short, fixtures, id_to_idx)
    df_bb1_tiers = simulate_bb1_wc4_player_tier_combinations(starters, gw_xp, fdr_mat, id_to_idx, fixtures)

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
    df_club_5way.to_csv(OUT_DIR / "def_club_5way_rotation_matrix.csv", index=False)
    df_tiers.to_csv(OUT_DIR / "def_tier_player_rotations.csv", index=False)
    df_bb1_clubs.to_csv(OUT_DIR / "def_bb1_wc4_club_matrix.csv", index=False)
    df_bb1_tiers.to_csv(OUT_DIR / "def_bb1_wc4_tier_lineups.csv", index=False)
    baseline.to_csv(OUT_DIR / "def_performance_baseline.csv", index=False)

    print(f"Analysis complete. Outputs written to {OUT_DIR}:")
    print(f" - def_club_5way_rotation_matrix.csv ({len(df_club_5way)} rows)")
    print(f" - def_tier_player_rotations.csv ({len(df_tiers)} rows)")
    print(f" - def_bb1_wc4_club_matrix.csv ({len(df_bb1_clubs)} rows)")
    print(f" - def_bb1_wc4_tier_lineups.csv ({len(df_bb1_tiers)} rows)")
    print(f" - def_performance_baseline.csv ({len(baseline)} rows)")

    return df_club_5way, df_tiers, df_bb1_clubs, df_bb1_tiers, baseline


if __name__ == "__main__":
    run_def_rotation_pipeline()
