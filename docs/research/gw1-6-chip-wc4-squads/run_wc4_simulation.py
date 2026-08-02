"""GW1–6 Chip & WC4 Wildcard Squad Optimization Engine.

Calculates GW1-6 projections via ParticipationStateHybridModel,
solves GW1/GW2 Bench Boost squads (£99.5m budget, £0.5m ITB) with 1+ Liverpool player,
and solves GW4 Wildcard squads comparing Unconstrained MILP vs Cheap-Defense Cap (GKP+DEF <= £31.5m) with 3 Liverpool players (Triple Liverpool).
Enforces 0 FTs in GW5 to bank 2+ FTs for GW6 post-international break.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

sys.path.insert(0, ".")

from features.builder import _fixture_maps
from models.participation_state_hybrid import ParticipationStateHybridModel

ITB_BUFFER = 0.5
MAX_BUDGET = 100.0

spec = importlib.util.spec_from_file_location("pmod", "docs/research/expected-stats-gw1-5/project_expected_points.py")
pmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pmod)


def generate_gw1_6_projections() -> pd.DataFrame:
    df_stats = pd.read_csv("data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv")
    df_fixtures = pd.read_parquet("data/processed/fixtures.parquet")
    df_clubs = pd.read_parquet("data/processed/clubs.parquet")
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
                "per90_defensive_contribution": float(player.get("per90_defensive_contribution", player["per90_defcon"])),
                "per90_saves": float(player["per90_saves"]),
                "per90_goals_conceded": float(player["per90_goals_conceded"]),
                "per90_threat": 0.0, "per90_creativity": 0.0, "per90_goals": 0.0, "per90_assists": 0.0,
                "per90_yellow_cards": 0.0, "per90_red_cards": 0.0, "per90_penalties_saved": 0.0,
                "per90_penalties_missed": 0.0, "per90_own_goals": 0.0,
                "is_immediate_next_gw": False, "has_availability_snapshot": False, "chance_of_playing": 100.0,
                "rate_source": player.get("rate_source", ""), "provenance_note": player.get("provenance_note", ""),
            })

    features = pd.DataFrame(rows)
    preds = ParticipationStateHybridModel().predict(features, horizon=6)
    merged = features.merge(preds, on=["player_id", "gameweek_id", "fixture_id"], how="left", suffixes=("", "_pred"))
    merged["projected_points"] = merged["projected_points"].fillna(0.0)
    merged["projected_minutes"] = merged["projected_minutes"].fillna(0.0)

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
            per90_defcon=("per90_defensive_contribution", "first"),
            per90_xg=("per90_xg", "first"),
            per90_xa=("per90_xa", "first"),
        )
    )

    df_p = df_players[["id", "now_cost", "selected_by_percent"]]
    gw_agg = gw_agg.merge(df_p, left_on="player_id", right_on="id", how="left")
    gw_agg["cost"] = gw_agg["now_cost"] / 10.0

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

    df_out = pd.DataFrame(final_rows).sort_values("total_6gw_xp", ascending=False)
    df_out = df_out[df_out["expected_role"].isin(pmod.DRAFT_ROLES)].reset_index(drop=True)
    return df_out


def solve_squad_advanced(
    df: pd.DataFrame,
    gw_list: list[int],
    bb_gw: int | None = None,
    max_spend: float = 100.0,
    max_def_spend: float | None = None,
    min_liv: int = 1,
) -> pd.DataFrame:
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

    # Total cost <= max_spend
    cost_row = np.zeros(2 * n)
    cost_row[:n] = df["cost"].values
    a_rows.append(cost_row)
    b_l.append(0.0)
    b_u.append(max_spend)

    # Position counts
    for pos, qty in [("GKP", 2), ("DEF", 5), ("MID", 5), ("FWD", 3)]:
        row = np.zeros(2 * n)
        row[:n] = (df["position"] == pos).astype(float).values
        a_rows.append(row)
        b_l.append(float(qty))
        b_u.append(float(qty))

    # Max 3 per club; MIN LIV CONSTRAINT
    for club in df["club_short"].unique():
        row = np.zeros(2 * n)
        row[:n] = (df["club_short"] == club).astype(float).values
        a_rows.append(row)
        lo = float(min_liv) if club == "LIV" else 0.0
        b_l.append(lo)
        b_u.append(3.0)

    # Defensive spend cap (GKP + DEF) if requested
    if max_def_spend is not None:
        def_cost_row = np.zeros(2 * n)
        def_cost_row[:n] = (df["position"].isin(["GKP", "DEF"])).astype(float).values * df["cost"].values
        a_rows.append(def_cost_row)
        b_l.append(0.0)
        b_u.append(max_def_spend)

    # XI link constraints: y <= x; sum y = 11
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

    # XI position limits: 1 GKP, 3-5 DEF, 2-5 MID, 1-3 FWD
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
        raise RuntimeError(f"MILP failed: {res.status}")

    squad = df.iloc[np.where(res.x[:n] > 0.5)[0]].copy()
    squad["is_starter"] = res.x[n:][np.where(res.x[:n] > 0.5)[0]] > 0.5
    squad.attrs["spend"] = float(squad["cost"].sum())
    squad.attrs["def_spend"] = float(squad[squad["position"].isin(["GKP", "DEF"])]["cost"].sum())
    squad.attrs["mid_fwd_spend"] = float(squad[squad["position"].isin(["MID", "FWD"])]["cost"].sum())
    return squad


def run_full_wc4_study():
    df_proj = generate_gw1_6_projections()
    p_csv = Path("data/research/gw1-6-chip-wc4-squads/gw1-6_projections.csv")
    p_csv.parent.mkdir(parents=True, exist_ok=True)
    df_proj.to_csv(p_csv, index=False)

    # Solve GW1/GW2 BB Drafts with min 1 LIV pre-WC
    bb1_squad = solve_squad_advanced(df_proj, gw_list=[1, 2, 3], bb_gw=1, max_spend=99.5, min_liv=1)
    bb2_squad = solve_squad_advanced(df_proj, gw_list=[1, 2, 3], bb_gw=2, max_spend=99.5, min_liv=1)

    # Solve GW4 WC Squads with min 3 LIV post-WC (Triple Liverpool)
    wc4_opt1_unconstrained = solve_squad_advanced(df_proj, gw_list=[4, 5, 6], bb_gw=None, max_spend=100.0, min_liv=3)
    wc4_opt2_cheapdef = solve_squad_advanced(df_proj, gw_list=[4, 5, 6], bb_gw=None, max_spend=100.0, max_def_spend=31.5, min_liv=3)

    print("\n=======================================================")
    print("GW1 BENCH BOOST 1 DRAFT (£99.5m spend, min 1 LIV)")
    print("=======================================================")
    print(f"Total Spend: £{bb1_squad.attrs['spend']:.1f}m | GKP+DEF: £{bb1_squad.attrs['def_spend']:.1f}m | MID+FWD: £{bb1_squad.attrs['mid_fwd_spend']:.1f}m")
    print(bb1_squad[["web_name", "club_short", "position", "cost", "expected_role", "gw1_xp", "gw1_3_xp", "is_starter"]].sort_values(["position", "cost"], ascending=[True, False]).to_string(index=False))

    print("\n=======================================================")
    print("GW4 WILDCARD — OPTION 1: UNCONSTRAINED MILP (min 3 LIV)")
    print("=======================================================")
    print(f"Total Spend: £{wc4_opt1_unconstrained.attrs['spend']:.1f}m | Starters XI GW4-6 xP: {wc4_opt1_unconstrained[wc4_opt1_unconstrained['is_starter']]['gw4_6_xp'].sum():.2f}")
    print(wc4_opt1_unconstrained[["web_name", "club_short", "position", "cost", "expected_role", "gw4_xp", "gw5_xp", "gw6_xp", "gw4_6_xp", "is_starter"]].sort_values(["position", "cost"], ascending=[True, False]).to_string(index=False))

    print("\n=======================================================")
    print("GW4 WILDCARD — OPTION 2: CHEAP DEFENSE CAP <= £31.5m (min 3 LIV)")
    print("=======================================================")
    print(f"Total Spend: £{wc4_opt2_cheapdef.attrs['spend']:.1f}m | Starters XI GW4-6 xP: {wc4_opt2_cheapdef[wc4_opt2_cheapdef['is_starter']]['gw4_6_xp'].sum():.2f}")
    print(wc4_opt2_cheapdef[["web_name", "club_short", "position", "cost", "expected_role", "gw4_xp", "gw5_xp", "gw6_xp", "gw4_6_xp", "is_starter"]].sort_values(["position", "cost"], ascending=[True, False]).to_string(index=False))

    records = []
    for squad_label, sq, gws in [
        ("GW1 Draft (BB1, min 1 LIV)", bb1_squad, [1, 2, 3]),
        ("GW2 Draft (BB2, min 1 LIV)", bb2_squad, [1, 2, 3]),
        ("WC4 Option 1 (Unconstrained, min 3 LIV)", wc4_opt1_unconstrained, [4, 5, 6]),
        ("WC4 Option 2 (Cheap DEF <= £31.5m, min 3 LIV)", wc4_opt2_cheapdef, [4, 5, 6]),
    ]:
        for _, r in sq.iterrows():
            rec = {
                "squad_label": squad_label,
                "player_id": int(r["player_id"]),
                "web_name": r["web_name"],
                "club_short": r["club_short"],
                "position": r["position"],
                "cost": r["cost"],
                "expected_role": r["expected_role"],
                "is_starter": bool(r.get("is_starter", True)),
                "per90_defcon": r["per90_defcon"],
                "per90_xg": r["per90_xg"],
                "per90_xa": r["per90_xa"],
            }
            for gw in gws:
                rec[f"gw{gw}_xp"] = r[f"gw{gw}_xp"]
                rec[f"gw{gw}_xmins"] = r[f"gw{gw}_xmins"]
            records.append(rec)

    sim_csv = Path("data/research/gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv")
    pd.DataFrame(records).to_csv(sim_csv, index=False)
    print(f"\nExported squad simulation CSV to {sim_csv}")


if __name__ == "__main__":
    run_full_wc4_study()
