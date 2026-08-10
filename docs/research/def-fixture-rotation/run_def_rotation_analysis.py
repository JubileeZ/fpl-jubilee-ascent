"""Starter Defender (5 DEF) Fixture Rotation & Diversification Analysis.

Simulates 5 DEF diversification and fixture rotation across:
1. Long-term horizons: GW1-3, GW4-19, GW1-19, and full season.
2. Specialized Pre-Wildcard Scenario: GW1 Bench Boost (BB1) + GW4 Wildcard (WC4).
   - GW1: All 5 defenders start on Bench Boost (enforcing Zero Head-to-Head Clashes and max FDR <= 3.0).
   - GW2 & GW3: Best 3 defenders rotate by lowest FDR / highest xP (standard 3-DEF formation).
   - GW4: Full Wildcard reset.
3. Player-level hybrid xP simulation via ParticipationStateHybridModel across budget tiers:
   - Tier 1: Pure Budget 5-Way Rotation (5x £4.0-£4.5m DEF, £21.5m-£22.5m total).
   - Tier 2: 1 Premium Anchor (£5.5-£6.5m) + 4 Budget (£4.0-£4.5m) (£23.5m-£24.5m total).
   - Tier 3: 2 Premium Anchors (£5.5-£6.5m) + 3 Budget (£4.0-£4.5m) (£25.0m-£26.5m total).
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
PROMOTED_CLUBS = frozenset({"COV", "HUL", "SUN"})
FLAT_START_MINUTES = 90.0
DEF_POSITION_ID = 2

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
    # 11 appearances total (5 in GW1 + 3 in GW2 + 3 in GW3) -> typical range 38.0 to 60.0 xP
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
            promoted_count = sum(1 for cs in club_shorts if cs in PROMOTED_CLUBS)

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
                    "promoted_count": promoted_count,
                    "is_pl_proven": promoted_count == 0,
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
        promoted_count = sum(1 for cs in club_shorts if cs in PROMOTED_CLUBS)

        rows.append(
            {
                "clubs": "-".join(club_shorts),
                "club1": club_shorts[0],
                "club2": club_shorts[1],
                "club3": club_shorts[2],
                "club4": club_shorts[3],
                "club5": club_shorts[4],
                "promoted_count": promoted_count,
                "is_pl_proven": promoted_count == 0,
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


def simulate_player_tier_combinations(
    starters: pd.DataFrame,
    gw_xp: pd.DataFrame,
    fdr_mat: np.ndarray,
    id_to_idx: dict[int, int],
) -> pd.DataFrame:
    """Simulate 5-DEF combinations across 4 budget tiers using top representative defenders per club."""
    xp_lookup = {
        int(pid): grp.set_index("gameweek_id")["projected_points"].to_dict()
        for pid, grp in gw_xp.groupby("player_id")
    }
    player_meta = starters.set_index("player_id").to_dict("index")

    budget_defs: list[int] = []
    premium_defs: list[int] = []

    for _, grp in starters.groupby("club_short"):
        b_sub = grp[grp["price"] <= 4.5].sort_values(
            ["price", "per90_xg", "per90_defcon"], ascending=[True, False, False]
        )
        if not b_sub.empty:
            budget_defs.append(int(b_sub.iloc[0]["player_id"]))

        p_sub = grp[grp["price"] >= 5.5].sort_values(
            ["per90_xg", "per90_defcon", "price"], ascending=[False, False, True]
        )
        if not p_sub.empty:
            premium_defs.append(int(p_sub.iloc[0]["player_id"]))

    all_tier_rows: list[dict] = []
    pair_indices = list(itertools.combinations(range(5), 2))

    for h_name, start_gw, end_gw in HORIZONS:
        gws = list(range(start_gw, end_gw + 1))
        gw_indices = [gw - 1 for gw in gws]
        n_gws = len(gws)
        h_fdr = fdr_mat[:, gw_indices]
        corr_mat = precompute_pairwise_corr(h_fdr)

        # -------------------------------------------------------------
        # Tier 1: Pure Budget 5-Way Rotation (5x £4.0-£4.5m DEF)
        # -------------------------------------------------------------
        for combo in itertools.combinations(budget_defs, 5):
            p_objs = [player_meta[pid] for pid in combo]
            tot_price = sum(float(p["price"]) for p in p_objs)
            if tot_price > 22.5:
                continue

            club_idxs = [id_to_idx[int(p["club_id"])] for p in p_objs]
            c_fdrs = h_fdr[club_idxs, :]
            c_xps = np.array([[float(xp_lookup[pid].get(gw, 0.0)) for gw in gws] for pid in combo])

            fdr_picks_xp = []
            rot_fdr_picks = []
            worst_starters = []
            max_xp_picks = []

            for t in range(n_gws):
                gw_fdr = c_fdrs[:, t]
                gw_xp_t = c_xps[:, t]
                order = sorted(range(5), key=lambda idx: (gw_fdr[idx], -gw_xp_t[idx]))
                starters_idx = order[:3]
                fdr_picks_xp.append(sum(gw_xp_t[i] for i in starters_idx))
                rot_fdr_picks.append(np.mean([gw_fdr[i] for i in starters_idx]))
                worst_starters.append(max(gw_fdr[i] for i in starters_idx))

                top3_xp_idx = np.argsort(-gw_xp_t)[:3]
                max_xp_picks.append(sum(gw_xp_t[i] for i in top3_xp_idx))

            tot_rot_xp = float(sum(fdr_picks_xp))
            tot_max_xp = float(sum(max_xp_picks))
            rot_avg_fdr = float(np.mean(rot_fdr_picks))
            max_worst_starter = float(max(worst_starters))
            no_diff_gws = int(sum(1 for w in worst_starters if w <= 3.0))
            no_diff_pct = float(no_diff_gws / n_gws * 100.0)

            corrs = [corr_mat[club_idxs[i], club_idxs[j]] for i, j in pair_indices]
            avg_corr = float(np.mean(corrs)) if corrs else 0.0

            rqi = compute_def_rqi(
                tot_rot_xp=tot_rot_xp,
                num_gws=n_gws,
                rot_avg_fdr=rot_avg_fdr,
                no_diff_pct=no_diff_pct,
                fdr_corr=avg_corr,
                total_price=tot_price,
            )

            has_promoted = any(p["club_short"] in PROMOTED_CLUBS for p in p_objs)
            all_tier_rows.append(
                {
                    "tier": "Tier 1: Pure Budget Rotation (£21.5m-£22.5m)",
                    "tier_id": 1,
                    "horizon": h_name,
                    "start_gw": start_gw,
                    "end_gw": end_gw,
                    "num_gws": n_gws,
                    "lineup_summary": " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs),
                    "clubs": "-".join(p["club_short"] for p in p_objs),
                    "total_price": round(tot_price, 1),
                    "rqi": rqi,
                    "tot_rot_xp": round(tot_rot_xp, 2),
                    "tot_rot_xp_maxxp": round(tot_max_xp, 2),
                    "maxxp_delta": round(tot_max_xp - tot_rot_xp, 2),
                    "rot_avg_fdr": round(rot_avg_fdr, 4),
                    "max_worst_starter": round(max_worst_starter, 1),
                    "no_diff_gws": no_diff_gws,
                    "no_diff_pct": round(no_diff_pct, 1),
                    "avg_fdr_corr": round(avg_corr, 4),
                    "has_promoted_proxy": has_promoted,
                }
            )

        # -------------------------------------------------------------
        # Tier 2: 1 Premium Anchor (£5.5-£6.5m) + 4 Budget (£4.0-£4.5m)
        # -------------------------------------------------------------
        for prem in premium_defs:
            prem_obj = player_meta[prem]
            prem_club = prem_obj["club_short"]
            prem_cid = id_to_idx[int(prem_obj["club_id"])]
            prem_fdr = h_fdr[prem_cid, :]
            prem_xp = np.array([float(xp_lookup[prem].get(gw, 0.0)) for gw in gws])

            valid_b = [b for b in budget_defs if player_meta[b]["club_short"] != prem_club]
            for b_combo in itertools.combinations(valid_b, 4):
                p_objs = [prem_obj] + [player_meta[pid] for pid in b_combo]
                tot_price = sum(float(p["price"]) for p in p_objs)
                if tot_price > 24.5 or tot_price < 23.5:
                    continue

                b_cids = [id_to_idx[int(p["club_id"])] for p in p_objs[1:]]
                b_fdrs = h_fdr[b_cids, :]
                b_xps = np.array([[float(xp_lookup[pid].get(gw, 0.0)) for gw in gws] for pid in b_combo])

                fdr_picks_xp = []
                rot_fdr_picks = []
                worst_starters = []
                max_xp_picks = []

                for t in range(n_gws):
                    b_fdr_t = b_fdrs[:, t]
                    b_xp_t = b_xps[:, t]
                    order = sorted(range(4), key=lambda idx: (b_fdr_t[idx], -b_xp_t[idx]))
                    b_starters_idx = order[:2]

                    wk_xp = prem_xp[t] + sum(b_xp_t[i] for i in b_starters_idx)
                    fdr_picks_xp.append(wk_xp)
                    wk_fdr = np.mean([prem_fdr[t], *(b_fdr_t[i] for i in b_starters_idx)])
                    rot_fdr_picks.append(wk_fdr)
                    worst_starters.append(max(prem_fdr[t], *(b_fdr_t[i] for i in b_starters_idx)))

                    top2_b_xp = np.argsort(-b_xp_t)[:2]
                    max_xp_picks.append(prem_xp[t] + sum(b_xp_t[i] for i in top2_b_xp))

                tot_rot_xp = float(sum(fdr_picks_xp))
                tot_max_xp = float(sum(max_xp_picks))
                rot_avg_fdr = float(np.mean(rot_fdr_picks))
                max_worst_starter = float(max(worst_starters))
                no_diff_gws = int(sum(1 for w in worst_starters if w <= 3.0))
                no_diff_pct = float(no_diff_gws / n_gws * 100.0)

                all_cids = [prem_cid, *b_cids]
                corrs = [corr_mat[all_cids[i], all_cids[j]] for i, j in pair_indices]
                avg_corr = float(np.mean(corrs)) if corrs else 0.0

                rqi = compute_def_rqi(
                    tot_rot_xp=tot_rot_xp,
                    num_gws=n_gws,
                    rot_avg_fdr=rot_avg_fdr,
                    no_diff_pct=no_diff_pct,
                    fdr_corr=avg_corr,
                    total_price=tot_price,
                )

                has_promoted = any(p["club_short"] in PROMOTED_CLUBS for p in p_objs)
                all_tier_rows.append(
                    {
                        "tier": "Tier 2: 1 Premium Anchor + 4 Budget (£23.5m-£24.5m)",
                        "tier_id": 2,
                        "horizon": h_name,
                        "start_gw": start_gw,
                        "end_gw": end_gw,
                        "num_gws": n_gws,
                        "lineup_summary": f"[Anchor: {prem_obj['web_name']} ({prem_obj['club_short']} £{prem_obj['price']:.1f}m)] + "
                        + " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs[1:]),
                        "clubs": "-".join(p["club_short"] for p in p_objs),
                        "total_price": round(tot_price, 1),
                        "rqi": rqi,
                        "tot_rot_xp": round(tot_rot_xp, 2),
                        "tot_rot_xp_maxxp": round(tot_max_xp, 2),
                        "maxxp_delta": round(tot_max_xp - tot_rot_xp, 2),
                        "rot_avg_fdr": round(rot_avg_fdr, 4),
                        "max_worst_starter": round(max_worst_starter, 1),
                        "no_diff_gws": no_diff_gws,
                        "no_diff_pct": round(no_diff_pct, 1),
                        "avg_fdr_corr": round(avg_corr, 4),
                        "has_promoted_proxy": has_promoted,
                    }
                )

        # -------------------------------------------------------------
        # Tier 3: 2 Premium Anchors (£5.5-£6.5m) + 3 Budget (£4.0-£4.5m)
        # -------------------------------------------------------------
        for prem_pair in itertools.combinations(premium_defs, 2):
            prem1, prem2 = player_meta[prem_pair[0]], player_meta[prem_pair[1]]
            prem_clubs = {prem1["club_short"], prem2["club_short"]}
            if len(prem_clubs) < 2:
                continue

            prem1_cid = id_to_idx[int(prem1["club_id"])]
            prem2_cid = id_to_idx[int(prem2["club_id"])]
            prem1_fdr = h_fdr[prem1_cid, :]
            prem2_fdr = h_fdr[prem2_cid, :]
            prem1_xp = np.array([float(xp_lookup[prem_pair[0]].get(gw, 0.0)) for gw in gws])
            prem2_xp = np.array([float(xp_lookup[prem_pair[1]].get(gw, 0.0)) for gw in gws])

            valid_b = [b for b in budget_defs if player_meta[b]["club_short"] not in prem_clubs]
            for b_combo in itertools.combinations(valid_b, 3):
                p_objs = [prem1, prem2] + [player_meta[pid] for pid in b_combo]
                tot_price = sum(float(p["price"]) for p in p_objs)
                if tot_price > 26.5 or tot_price < 25.0:
                    continue

                b_cids = [id_to_idx[int(p["club_id"])] for p in p_objs[2:]]
                b_fdrs = h_fdr[b_cids, :]
                b_xps = np.array([[float(xp_lookup[pid].get(gw, 0.0)) for gw in gws] for pid in b_combo])

                fdr_picks_xp = []
                rot_fdr_picks = []
                worst_starters = []
                max_xp_picks = []

                for t in range(n_gws):
                    b_fdr_t = b_fdrs[:, t]
                    b_xp_t = b_xps[:, t]
                    order = sorted(range(3), key=lambda idx: (b_fdr_t[idx], -b_xp_t[idx]))
                    best_b_idx = order[0]

                    wk_xp = prem1_xp[t] + prem2_xp[t] + b_xp_t[best_b_idx]
                    fdr_picks_xp.append(wk_xp)
                    wk_fdr = np.mean([prem1_fdr[t], prem2_fdr[t], b_fdr_t[best_b_idx]])
                    rot_fdr_picks.append(wk_fdr)
                    worst_starters.append(max(prem1_fdr[t], prem2_fdr[t], b_fdr_t[best_b_idx]))

                    top1_b_xp = np.argsort(-b_xp_t)[0]
                    max_xp_picks.append(prem1_xp[t] + prem2_xp[t] + b_xp_t[top1_b_xp])

                tot_rot_xp = float(sum(fdr_picks_xp))
                tot_max_xp = float(sum(max_xp_picks))
                rot_avg_fdr = float(np.mean(rot_fdr_picks))
                max_worst_starter = float(max(worst_starters))
                no_diff_gws = int(sum(1 for w in worst_starters if w <= 3.0))
                no_diff_pct = float(no_diff_gws / n_gws * 100.0)

                all_cids = [prem1_cid, prem2_cid, *b_cids]
                corrs = [corr_mat[all_cids[i], all_cids[j]] for i, j in pair_indices]
                avg_corr = float(np.mean(corrs)) if corrs else 0.0

                rqi = compute_def_rqi(
                    tot_rot_xp=tot_rot_xp,
                    num_gws=n_gws,
                    rot_avg_fdr=rot_avg_fdr,
                    no_diff_pct=no_diff_pct,
                    fdr_corr=avg_corr,
                    total_price=tot_price,
                )

                has_promoted = any(p["club_short"] in PROMOTED_CLUBS for p in p_objs)
                all_tier_rows.append(
                    {
                        "tier": "Tier 3: 2 Premium Anchors + 3 Budget (£25.5m-£26.5m)",
                        "tier_id": 3,
                        "horizon": h_name,
                        "start_gw": start_gw,
                        "end_gw": end_gw,
                        "num_gws": n_gws,
                        "lineup_summary": f"[Anchors: {prem1['web_name']} ({prem1['club_short']} £{prem1['price']:.1f}m) + {prem2['web_name']} ({prem2['club_short']} £{prem2['price']:.1f}m)] + "
                        + " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs[2:]),
                        "clubs": "-".join(p["club_short"] for p in p_objs),
                        "total_price": round(tot_price, 1),
                        "rqi": rqi,
                        "tot_rot_xp": round(tot_rot_xp, 2),
                        "tot_rot_xp_maxxp": round(tot_max_xp, 2),
                        "maxxp_delta": round(tot_max_xp - tot_rot_xp, 2),
                        "rot_avg_fdr": round(rot_avg_fdr, 4),
                        "max_worst_starter": round(max_worst_starter, 1),
                        "no_diff_gws": no_diff_gws,
                        "no_diff_pct": round(no_diff_pct, 1),
                        "avg_fdr_corr": round(avg_corr, 4),
                        "has_promoted_proxy": has_promoted,
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
    """Simulate player lineups specifically for GW1 BB (5 starters) + GW2-3 rotation (3 starters)."""
    xp_lookup = {
        int(pid): grp.set_index("gameweek_id")["projected_points"].to_dict()
        for pid, grp in gw_xp.groupby("player_id")
    }
    player_meta = starters.set_index("player_id").to_dict("index")

    gw1_f = fixtures[fixtures["gameweek_id"] == 1]
    clash_pairs = set()
    for _, f in gw1_f.iterrows():
        h_idx = id_to_idx[int(f["home_club_id"])]
        a_idx = id_to_idx[int(f["away_club_id"])]
        clash_pairs.add(frozenset([h_idx, a_idx]))

    corr_mat = precompute_pairwise_corr(fdr_mat[:, 0:3])
    pair_indices = list(itertools.combinations(range(5), 2))

    budget_defs: list[int] = []
    premium_defs: list[int] = []

    for _, grp in starters.groupby("club_short"):
        b_sub = grp[grp["price"] <= 4.5].sort_values(
            ["price", "per90_xg", "per90_defcon"], ascending=[True, False, False]
        )
        if not b_sub.empty:
            budget_defs.append(int(b_sub.iloc[0]["player_id"]))

        p_sub = grp[grp["price"] >= 5.5].sort_values(
            ["per90_xg", "per90_defcon", "price"], ascending=[False, False, True]
        )
        if not p_sub.empty:
            premium_defs.append(int(p_sub.iloc[0]["player_id"]))

    rows: list[dict] = []

    # -------------------------------------------------------------
    # Tier 1: Pure Budget BB1 (£21.5m-£22.5m)
    # -------------------------------------------------------------
    for combo in itertools.combinations(budget_defs, 5):
        p_objs = [player_meta[pid] for pid in combo]
        c_idxs = [id_to_idx[int(p["club_id"])] for p in p_objs]
        has_clash = any(frozenset([c_idxs[i], c_idxs[j]]) in clash_pairs for i in range(5) for j in range(i + 1, 5))
        if has_clash:
            continue

        gw1_fdrs = [fdr_mat[c_idxs[i], 0] for i in range(5)]
        if max(gw1_fdrs) > 3.0:
            continue

        tot_price = sum(float(p["price"]) for p in p_objs)
        if tot_price > 22.5:
            continue

        # GW1: all 5 play
        gw1_xps = [float(xp_lookup[pid].get(1, 0.0)) for pid in combo]
        gw1_pts = float(sum(gw1_xps))

        # GW2: top 3 by FDR
        gw2_fdrs = [fdr_mat[c_idxs[i], 1] for i in range(5)]
        gw2_xps = [float(xp_lookup[pid].get(2, 0.0)) for pid in combo]
        order2 = sorted(range(5), key=lambda idx: (gw2_fdrs[idx], -gw2_xps[idx]))[:3]
        gw2_pts = float(sum(gw2_xps[i] for i in order2))

        # GW3: top 3 by FDR
        gw3_fdrs = [fdr_mat[c_idxs[i], 2] for i in range(5)]
        gw3_xps = [float(xp_lookup[pid].get(3, 0.0)) for pid in combo]
        order3 = sorted(range(5), key=lambda idx: (gw3_fdrs[idx], -gw3_xps[idx]))[:3]
        gw3_pts = float(sum(gw3_xps[i] for i in order3))

        tot_effective_xp = gw1_pts + gw2_pts + gw3_pts
        gw1_avg_fdr = float(np.mean(gw1_fdrs))
        gw2_3_rot_fdr = float((sum(gw2_fdrs[i] for i in order2) + sum(gw3_fdrs[i] for i in order3)) / 6.0)
        effective_avg_fdr = float(
            (sum(gw1_fdrs) + sum(gw2_fdrs[i] for i in order2) + sum(gw3_fdrs[i] for i in order3)) / 11.0
        )

        corrs = [corr_mat[c_idxs[i], c_idxs[j]] for i, j in pair_indices]
        avg_corr = float(np.mean(corrs)) if corrs else 0.0

        rqi = compute_bb_rqi(
            tot_effective_xp=tot_effective_xp,
            gw1_avg_fdr=gw1_avg_fdr,
            gw2_3_rot_fdr=gw2_3_rot_fdr,
            effective_avg_fdr=effective_avg_fdr,
            avg_corr=avg_corr,
            total_price=tot_price,
        )

        has_promoted = any(p["club_short"] in PROMOTED_CLUBS for p in p_objs)
        rows.append(
            {
                "tier": "Tier 1: Pure Budget BB1 (£21.5m-£22.5m)",
                "tier_id": 1,
                "lineup_summary": " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs),
                "clubs": "-".join(p["club_short"] for p in p_objs),
                "total_price": round(tot_price, 1),
                "bb_rqi": rqi,
                "tot_effective_xp": round(tot_effective_xp, 2),
                "gw1_xp_5def": round(gw1_pts, 2),
                "gw2_3_xp_6def": round(gw2_pts + gw3_pts, 2),
                "gw1_avg_fdr": round(gw1_avg_fdr, 2),
                "gw2_3_rot_fdr": round(gw2_3_rot_fdr, 2),
                "effective_avg_fdr": round(effective_avg_fdr, 4),
                "avg_fdr_corr": round(avg_corr, 4),
                "has_promoted_proxy": has_promoted,
            }
        )

    # -------------------------------------------------------------
    # Tier 2: 1 Premium Anchor (£5.5-£6.5m) + 4 Budget (£4.0-£4.5m)
    # -------------------------------------------------------------
    for prem in premium_defs:
        prem_obj = player_meta[prem]
        prem_club = prem_obj["club_short"]
        prem_cid = id_to_idx[int(prem_obj["club_id"])]
        valid_b = [b for b in budget_defs if player_meta[b]["club_short"] != prem_club]

        for b_combo in itertools.combinations(valid_b, 4):
            combo = (prem, *b_combo)
            p_objs = [player_meta[pid] for pid in combo]
            c_idxs = [id_to_idx[int(p["club_id"])] for p in p_objs]

            has_clash = any(frozenset([c_idxs[i], c_idxs[j]]) in clash_pairs for i in range(5) for j in range(i + 1, 5))
            if has_clash:
                continue

            gw1_fdrs = [fdr_mat[c_idxs[i], 0] for i in range(5)]
            if max(gw1_fdrs) > 3.0:
                continue

            tot_price = sum(float(p["price"]) for p in p_objs)
            if tot_price > 24.5 or tot_price < 23.5:
                continue

            gw1_xps = [float(xp_lookup[pid].get(1, 0.0)) for pid in combo]
            gw1_pts = float(sum(gw1_xps))

            # GW2: Anchor + top 2 budget
            gw2_b_fdrs = [fdr_mat[c_idxs[i], 1] for i in range(1, 5)]
            gw2_b_xps = [float(xp_lookup[pid].get(2, 0.0)) for pid in b_combo]
            order2 = sorted(range(4), key=lambda idx: (gw2_b_fdrs[idx], -gw2_b_xps[idx]))[:2]
            gw2_pts = float(xp_lookup[prem].get(2, 0.0)) + sum(gw2_b_xps[i] for i in order2)

            # GW3: Anchor + top 2 budget
            gw3_b_fdrs = [fdr_mat[c_idxs[i], 2] for i in range(1, 5)]
            gw3_b_xps = [float(xp_lookup[pid].get(3, 0.0)) for pid in b_combo]
            order3 = sorted(range(4), key=lambda idx: (gw3_b_fdrs[idx], -gw3_b_xps[idx]))[:2]
            gw3_pts = float(xp_lookup[prem].get(3, 0.0)) + sum(gw3_b_xps[i] for i in order3)

            tot_effective_xp = gw1_pts + gw2_pts + gw3_pts
            gw1_avg_fdr = float(np.mean(gw1_fdrs))
            gw2_3_rot_fdr = float(
                (fdr_mat[prem_cid, 1] + sum(gw2_b_fdrs[i] for i in order2) + fdr_mat[prem_cid, 2] + sum(gw3_b_fdrs[i] for i in order3)) / 6.0
            )
            effective_avg_fdr = float(
                (sum(gw1_fdrs) + fdr_mat[prem_cid, 1] + sum(gw2_b_fdrs[i] for i in order2) + fdr_mat[prem_cid, 2] + sum(gw3_b_fdrs[i] for i in order3)) / 11.0
            )

            corrs = [corr_mat[c_idxs[i], c_idxs[j]] for i, j in pair_indices]
            avg_corr = float(np.mean(corrs)) if corrs else 0.0

            rqi = compute_bb_rqi(
                tot_effective_xp=tot_effective_xp,
                gw1_avg_fdr=gw1_avg_fdr,
                gw2_3_rot_fdr=gw2_3_rot_fdr,
                effective_avg_fdr=effective_avg_fdr,
                avg_corr=avg_corr,
                total_price=tot_price,
            )

            has_promoted = any(p["club_short"] in PROMOTED_CLUBS for p in p_objs)
            rows.append(
                {
                    "tier": "Tier 2: 1 Premium Anchor + 4 Budget (£23.5m-£24.5m)",
                    "tier_id": 2,
                    "lineup_summary": f"[Anchor: {prem_obj['web_name']} ({prem_obj['club_short']} £{prem_obj['price']:.1f}m)] + "
                    + " + ".join(f"{p['web_name']} ({p['club_short']} £{p['price']:.1f}m)" for p in p_objs[1:]),
                    "clubs": "-".join(p["club_short"] for p in p_objs),
                    "total_price": round(tot_price, 1),
                    "bb_rqi": rqi,
                    "tot_effective_xp": round(tot_effective_xp, 2),
                    "gw1_xp_5def": round(gw1_pts, 2),
                    "gw2_3_xp_6def": round(gw2_pts + gw3_pts, 2),
                    "gw1_avg_fdr": round(gw1_avg_fdr, 2),
                    "gw2_3_rot_fdr": round(gw2_3_rot_fdr, 2),
                    "effective_avg_fdr": round(effective_avg_fdr, 4),
                    "avg_fdr_corr": round(avg_corr, 4),
                    "has_promoted_proxy": has_promoted,
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

    print("Simulating multi-tier 5-DEF player combinations...")
    df_tiers = simulate_player_tier_combinations(starters, gw_xp, fdr_mat, id_to_idx)

    print("Simulating specialized GW1 BB + GW4 WC pre-wildcard scenario...")
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
    baseline["has_promoted_proxy"] = baseline["club_short"].isin(PROMOTED_CLUBS)
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
