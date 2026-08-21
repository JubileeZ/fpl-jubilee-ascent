"""GW1–6 Preseason Optimization Pipeline: GW1 BB + WC4 Canonical Strategy.

Focuses exclusively on the single canonical scenario (GW1 Bench Boost + GW4 Wildcard):
- GW1: Bench Boost active (15 starters scoring; £100.0m budget; max 3 per club).
- GW1-3: Locked transfers (0 transfers in GW1-3; starting 11 optimized each GW).
- GW4: Wildcard Rebuild (optimal 15-player squad targeting GW4-6+ fixtures).
- GW5: Roll transfer (transfers=0).
- GW6: Enter post-international break with 4 banked Free Transfers.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

sys.path.insert(0, ".")

from features.builder import _fixture_maps
from models.participation_state_hybrid import ParticipationStateHybridModel

MAX_BUDGET = 100.0

spec = importlib.util.spec_from_file_location(
    "pmod",
    "docs/archive/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/project_expected_points.py",
)
pmod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pmod)

_PRIOR_SPEC = importlib.util.spec_from_file_location(
    "availability_priors",
    Path("docs/archive/gw1-6-preseason-pipeline/availability_priors.py"),
)
_PRIOR_MOD = importlib.util.module_from_spec(_PRIOR_SPEC)
assert _PRIOR_SPEC.loader is not None
_PRIOR_SPEC.loader.exec_module(_PRIOR_MOD)
apply_availability_priors = _PRIOR_MOD.apply_availability_priors

_SEED_SPEC = importlib.util.spec_from_file_location(
    "dual_vector_seed_s3",
    Path("docs/archive/gw1-19-first-half-chip-path/build_dual_vector_seed.py"),
)
_SEED_MOD = importlib.util.module_from_spec(_SEED_SPEC)
assert _SEED_SPEC.loader is not None
_SEED_SPEC.loader.exec_module(_SEED_MOD)


def generate_gw1_6_projections() -> pd.DataFrame:
    df_stats = pd.read_csv(
        "docs/archive/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv"
    )
    df_fixtures = pd.read_parquet("data/processed/fixtures.parquet")
    df_clubs = _SEED_MOD.load_seeded_clubs()
    df_players = pd.read_parquet("data/processed/players.parquet")

    club_short_to_id = dict(zip(df_clubs["short_name"], df_clubs["id"], strict=False))
    fixture_map = _fixture_maps(df_fixtures, df_clubs, list(range(1, 7)))

    rows = []
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
                "position_id": pmod._POS_TO_ID.get(str(player["position"]), 3),
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
            })

    features = pd.DataFrame(rows)
    preds = ParticipationStateHybridModel().predict(features, horizon=6)
    merged = features.merge(
        preds, on=["player_id", "gameweek_id", "fixture_id"], how="left", suffixes=("", "_pred")
    )
    merged["projected_points"] = merged["projected_points"].fillna(0.0)
    merged["projected_minutes"] = merged["projected_minutes"].fillna(0.0)

    cost_map = dict(zip(df_players["id"], df_players["now_cost"] / 10.0, strict=False))
    defcon_map = dict(zip(df_stats["player_id"], df_stats["per90_defcon"], strict=False))
    xg_map = dict(zip(df_stats["player_id"], df_stats["per90_xg"], strict=False))
    xa_map = dict(zip(df_stats["player_id"], df_stats["per90_xa"], strict=False))

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
    gw_agg["per90_defcon"] = gw_agg["player_id"].map(defcon_map).fillna(0.0)
    gw_agg["per90_xg"] = gw_agg["player_id"].map(xg_map).fillna(0.0)
    gw_agg["per90_xa"] = gw_agg["player_id"].map(xa_map).fillna(0.0)

    final_rows = []
    for pid, grp in gw_agg.groupby("player_id"):
        grp = grp.sort_values("gameweek_id")
        meta = grp.iloc[0]
        row = {
            "player_id": int(pid),
            "web_name": meta["web_name"],
            "club_short": meta["club_short"],
            "position": meta["position"],
            "expected_role": meta["expected_role"],
            "draft_availability": meta["draft_availability"],
            "cost": float(meta["cost"]),
            "per90_defcon": float(meta["per90_defcon"]),
            "per90_xg": float(meta["per90_xg"]),
            "per90_xa": float(meta["per90_xa"]),
        }
        total_xp_6 = 0.0
        for gw in range(1, 7):
            hit = grp[grp["gameweek_id"] == gw]
            xp = float(hit["projected_points"].sum()) if len(hit) else 0.0
            mins = float(hit["projected_minutes"].sum()) if len(hit) else 0.0
            row[f"gw{gw}_xp"] = round(xp, 2)
            row[f"gw{gw}_xmins"] = round(mins, 1)
            total_xp_6 += xp
        row["total_6gw_xp"] = round(total_xp_6, 2)
        row["gw1_3_xp"] = round(row["gw1_xp"] + row["gw2_xp"] + row["gw3_xp"], 2)
        row["gw4_6_xp"] = round(row["gw4_xp"] + row["gw5_xp"] + row["gw6_xp"], 2)
        final_rows.append(row)

    return pd.DataFrame(final_rows).sort_values("total_6gw_xp", ascending=False).reset_index(drop=True)


def solve_squad_advanced(
    df: pd.DataFrame,
    gw_list: list[int],
    bb_gw: int | None = None,
    max_spend: float = 100.0,
    max_def_spend: float | None = None,
    min_liv: int = 0,
    banned_web_names: set[str] | None = None,
) -> pd.DataFrame:
    df = df[df["expected_role"].isin(pmod.DRAFT_ROLES)].copy()
    if banned_web_names:
        df = df[~df["web_name"].isin(banned_web_names)]
    df = df.reset_index(drop=True)
    n = len(df)
    c = np.zeros(2 * n)
    for gw in gw_list:
        xp = df[f"gw{gw}_xp"].values
        if bb_gw == gw:
            c[:n] -= xp
        else:
            c[n:] -= xp

    a_rows: list[np.ndarray] = []
    b_l: list[float] = []
    b_u: list[float] = []

    cost_row = np.zeros(2 * n)
    cost_row[:n] = df["cost"].values
    a_rows.append(cost_row)
    b_l.append(0.0)
    b_u.append(max_spend)

    for pos, qty in [("GKP", 2), ("DEF", 5), ("MID", 5), ("FWD", 3)]:
        row = np.zeros(2 * n)
        row[:n] = (df["position"] == pos).astype(float).values
        a_rows.append(row)
        b_l.append(float(qty))
        b_u.append(float(qty))

    for club in df["club_short"].unique():
        row = np.zeros(2 * n)
        row[:n] = (df["club_short"] == club).astype(float).values
        a_rows.append(row)
        lo = float(min_liv) if club == "LIV" else 0.0
        b_l.append(lo)
        b_u.append(3.0)

    if max_def_spend is not None:
        def_cost_row = np.zeros(2 * n)
        def_cost_row[:n] = (
            df["position"].isin(["GKP", "DEF"]).astype(float).values * df["cost"].values
        )
        a_rows.append(def_cost_row)
        b_l.append(0.0)
        b_u.append(max_def_spend)

    for i in range(n):
        row = np.zeros(2 * n)
        row[i] = -1.0
        row[n + i] = 1.0
        a_rows.append(row)
        b_l.append(-np.inf)
        b_u.append(0.0)

    sum_y = np.zeros(2 * n)
    sum_y[n:] = 1.0
    a_rows.append(sum_y)
    b_l.append(11.0)
    b_u.append(11.0)

    for pos, lo, hi in [("GKP", 1, 1), ("DEF", 3, 5), ("MID", 2, 5), ("FWD", 1, 3)]:
        row = np.zeros(2 * n)
        row[n:] = (df["position"] == pos).astype(float).values
        a_rows.append(row)
        b_l.append(float(lo))
        b_u.append(float(hi))

    res = milp(
        c=c,
        integrality=np.ones(2 * n),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(np.array(a_rows), b_l, b_u),
    )
    if res.x is None or res.status != 0:
        raise RuntimeError(f"MILP failed: {res.status} bans={banned_web_names} gws={gw_list}")

    squad = df.iloc[np.where(res.x[:n] > 0.5)[0]].copy()
    squad["is_starter"] = res.x[n:][np.where(res.x[:n] > 0.5)[0]] > 0.5
    squad.attrs["spend"] = float(squad["cost"].sum())
    squad.attrs["def_spend"] = float(squad[squad["position"].isin(["GKP", "DEF"])]["cost"].sum())
    return squad


def get_gw_starters(
    df_squad: pd.DataFrame, gw: int, bb_gw: int | None = None
) -> tuple[pd.DataFrame, float]:
    if bb_gw == gw:
        return df_squad.copy(), float(df_squad[f"gw{gw}_xp"].sum())

    gkps = df_squad[df_squad["position"] == "GKP"].sort_values(f"gw{gw}_xp", ascending=False)
    best_gkp = gkps.iloc[0:1]
    outfield = df_squad[df_squad["position"] != "GKP"].copy()
    n = len(outfield)
    c = -outfield[f"gw{gw}_xp"].values
    a_rows = [np.ones(n)]
    b_l = [10.0]
    b_u = [10.0]
    for pos, lo, hi in [("DEF", 3, 5), ("MID", 2, 5), ("FWD", 1, 3)]:
        a_rows.append((outfield["position"] == pos).astype(float).values)
        b_l.append(float(lo))
        b_u.append(float(hi))
    res = milp(
        c=c, integrality=np.ones(n), bounds=Bounds(0, 1),
        constraints=LinearConstraint(np.array(a_rows), b_l, b_u),
    )
    selected_outfield = outfield.iloc[np.where(res.x > 0.5)[0]]
    starters = pd.concat([best_gkp, selected_outfield])
    return starters, float(starters[f"gw{gw}_xp"].sum())


def run_full_wc4_study() -> pd.DataFrame:
    df_proj = generate_gw1_6_projections()
    p_csv = Path("docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_projections.csv")
    p_csv.parent.mkdir(parents=True, exist_ok=True)
    df_proj.to_csv(p_csv, index=False)

    print("==========================================================================")
    print("GW1–6 OPTIMIZATION: GW1 BB + WC4 CANONICAL STRATEGY")
    print("==========================================================================")

    # 1. Pre-WC Squad (GW1-3, BB1 active in GW1, 0 transfers in GW1-3)
    pre_squad = solve_squad_advanced(df_proj, gw_list=[1, 2, 3], bb_gw=1, max_spend=100.0)

    # 2. Post-WC Squad (GW4-6, WC4 active in GW4, 0 transfers in GW5-6)
    post_squad = solve_squad_advanced(df_proj, gw_list=[4, 5, 6], max_spend=100.0)

    # Calculate points and captains
    # GW1: BB1 (all 15 score) + Captain
    gw1_starters, gw1_base = get_gw_starters(pre_squad, 1, bb_gw=1)
    gw1_cap = pre_squad.sort_values("gw1_xp", ascending=False).iloc[0]
    gw1_xp = gw1_base + float(gw1_cap["gw1_xp"])

    # GW2: Top 11 starters + Captain
    gw2_starters, gw2_base = get_gw_starters(pre_squad, 2, bb_gw=None)
    gw2_cap = gw2_starters.sort_values("gw2_xp", ascending=False).iloc[0]
    gw2_xp = gw2_base + float(gw2_cap["gw2_xp"])

    # GW3: Top 11 starters + Captain
    gw3_starters, gw3_base = get_gw_starters(pre_squad, 3, bb_gw=None)
    gw3_cap = gw3_starters.sort_values("gw3_xp", ascending=False).iloc[0]
    gw3_xp = gw3_base + float(gw3_cap["gw3_xp"])

    gw1_3_xp = gw1_xp + gw2_xp + gw3_xp

    # GW4: Top 11 starters from WC4 squad + Captain
    gw4_starters, gw4_base = get_gw_starters(post_squad, 4, bb_gw=None)
    gw4_cap = gw4_starters.sort_values("gw4_xp", ascending=False).iloc[0]
    gw4_xp = gw4_base + float(gw4_cap["gw4_xp"])

    # GW5: Top 11 starters + Captain (0 transfers rolled)
    gw5_starters, gw5_base = get_gw_starters(post_squad, 5, bb_gw=None)
    gw5_cap = gw5_starters.sort_values("gw5_xp", ascending=False).iloc[0]
    gw5_xp = gw5_base + float(gw5_cap["gw5_xp"])

    # GW6: Top 11 starters + Captain (0 transfers rolled)
    gw6_starters, gw6_base = get_gw_starters(post_squad, 6, bb_gw=None)
    gw6_cap = gw6_starters.sort_values("gw6_xp", ascending=False).iloc[0]
    gw6_xp = gw6_base + float(gw6_cap["gw6_xp"])

    gw4_6_xp = gw4_xp + gw5_xp + gw6_xp
    total_6gw = gw1_3_xp + gw4_6_xp

    summary_record = {
        "scenario_id": "S1",
        "scenario": "GW1 BB + WC4 Canonical (Locked GW1-3, Roll GW5)",
        "bb_chip": "GW1",
        "wc_chip": "GW4",
        "gw1_captain": gw1_cap["web_name"],
        "gw2_captain": gw2_cap["web_name"],
        "gw3_captain": gw3_cap["web_name"],
        "gw4_captain": gw4_cap["web_name"],
        "gw5_captain": gw5_cap["web_name"],
        "gw6_captain": gw6_cap["web_name"],
        "gw1_xp": round(gw1_xp, 2),
        "gw2_xp": round(gw2_xp, 2),
        "gw3_xp": round(gw3_xp, 2),
        "gw1_3_xp": round(gw1_3_xp, 2),
        "gw4_xp": round(gw4_xp, 2),
        "gw5_xp": round(gw5_xp, 2),
        "gw6_xp": round(gw6_xp, 2),
        "gw4_6_xp": round(gw4_6_xp, 2),
        "total_6gw_xp": round(total_6gw, 2),
        "pre_spend": pre_squad.attrs["spend"],
        "post_spend": post_squad.attrs["spend"],
        "itb_gw6": round(100.0 - post_squad.attrs["spend"], 1),
        "gw5_transfers": 0,
        "banked_fts_gw6": 4,
        "score_world": "prior_season_dual_vector_seed",
    }

    df_summary = pd.DataFrame([summary_record])
    print("\n--- CANONICAL SCENARIO SUMMARY ---")
    print(df_summary.to_string(index=False))

    # Detailed row records
    detailed_records = []
    # Pre-WC squad
    for _, r in pre_squad.iterrows():
        pid = int(r["player_id"])
        detailed_records.append({
            "scenario": "GW1 BB + WC4",
            "phase": "GW1-3 Pre-WC (BB1 Active)",
            "player_id": pid,
            "web_name": r["web_name"],
            "club_short": r["club_short"],
            "position": r["position"],
            "cost": r["cost"],
            "expected_role": r["expected_role"],
            "gw1_xp": r["gw1_xp"],
            "gw2_xp": r["gw2_xp"],
            "gw3_xp": r["gw3_xp"],
            "gw4_xp": 0.0,
            "gw5_xp": 0.0,
            "gw6_xp": 0.0,
            "is_starter_gw1": True,
            "is_starter_gw2": pid in set(gw2_starters["player_id"]),
            "is_starter_gw3": pid in set(gw3_starters["player_id"]),
            "is_starter_gw4": False,
            "is_starter_gw5": False,
            "is_starter_gw6": False,
        })

    # Post-WC squad
    for _, r in post_squad.iterrows():
        pid = int(r["player_id"])
        detailed_records.append({
            "scenario": "GW1 BB + WC4",
            "phase": "GW4-6 Post-WC (WC4 Rebuild)",
            "player_id": pid,
            "web_name": r["web_name"],
            "club_short": r["club_short"],
            "position": r["position"],
            "cost": r["cost"],
            "expected_role": r["expected_role"],
            "gw1_xp": 0.0,
            "gw2_xp": 0.0,
            "gw3_xp": 0.0,
            "gw4_xp": r["gw4_xp"],
            "gw5_xp": r["gw5_xp"],
            "gw6_xp": r["gw6_xp"],
            "is_starter_gw1": False,
            "is_starter_gw2": False,
            "is_starter_gw3": False,
            "is_starter_gw4": pid in set(gw4_starters["player_id"]),
            "is_starter_gw5": pid in set(gw5_starters["player_id"]),
            "is_starter_gw6": pid in set(gw6_starters["player_id"]),
        })

    sim_csv = Path("docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv")
    pd.DataFrame(detailed_records).to_csv(sim_csv, index=False)
    summary_csv = Path("docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv")
    df_summary.to_csv(summary_csv, index=False)

    print(f"\nExported detailed simulation to {sim_csv}")
    print(f"Exported summary to {summary_csv}")
    xi_spec = importlib.util.spec_from_file_location(
        "export_select_11_canonical",
        Path("docs/archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/export_select_11.py"),
    )
    xi_mod = importlib.util.module_from_spec(xi_spec)
    assert xi_spec.loader is not None
    xi_spec.loader.exec_module(xi_mod)
    xi_mod.export_select_11()
    sync_spec = importlib.util.spec_from_file_location(
        "sync_live_research_figures",
        Path("docs/archive/sync_live_research_figures.py"),
    )
    sync_mod = importlib.util.module_from_spec(sync_spec)
    assert sync_spec.loader is not None
    sync_spec.loader.exec_module(sync_mod)
    sync_mod.sync_all()
    return df_summary


if __name__ == "__main__":
    run_full_wc4_study()
