"""
DEF FDR Rotation Runner (GW1-19)
Evaluates and ranks all 5-defender rotation combinations across GW1-19 picking best 3 each gameweek.
Generates companion CSV artifacts for docs/research/def-fdr-rotation-gw1-19/
"""

import itertools
import os

import numpy as np
import pandas as pd

from club_occupancy import build_club_occupancy_table

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Load data
fixtures = pd.read_parquet("data/processed/fixtures.parquet")
clubs = pd.read_parquet("data/processed/clubs.parquet")
players = pd.read_parquet("data/processed/players.parquet")
roles = pd.read_csv("features/expected-role-gw1-5.csv")

gw1_19 = fixtures[(fixtures["gameweek_id"] >= 1) & (fixtures["gameweek_id"] <= 19)]

# Sourced / starter defenders per club from expected roles joined with authoritative player club_id
merged_defs = players[players["position_id"] == 2].merge(
    roles[["player_id", "expected_role", "confidence"]],
    left_on="id",
    right_on="player_id",
    how="left",
)

club_starters = {}
for c_id in sorted(clubs["id"].unique()):
    c_short = clubs.loc[clubs["id"] == c_id, "short_name"].values[0]
    c_defs = merged_defs[merged_defs["club_id"] == c_id]
    starters = c_defs[
        c_defs["expected_role"].isin(["Nailed Starter", "Regular Starter"])
    ].sort_values("now_cost")

    if len(starters) == 0:
        # Fallback to all defenders sorted by cost
        starters = c_defs.sort_values("now_cost")

    club_starters[c_id] = [
        {
            "player_id": int(r["id"]),
            "player_name": r["web_name"],
            "cost": float(r["now_cost"]) / 10.0,
            "club_id": c_id,
            "club_short": c_short,
            "expected_role": r.get("expected_role", "Regular Starter"),
        }
        for _, r in starters.iterrows()
    ]

# 2. Precompute fixture difficulties per club per GW
club_gw_fdr = {}
for c_id in clubs["id"]:
    for gw in range(1, 20):
        h_fix = gw1_19[(gw1_19["gameweek_id"] == gw) & (gw1_19["home_club_id"] == c_id)]
        a_fix = gw1_19[(gw1_19["gameweek_id"] == gw) & (gw1_19["away_club_id"] == c_id)]

        base_list, mod_list, opp_list = [], [], []
        for _, r in h_fix.iterrows():
            base = float(r["team_h_difficulty"])
            base_list.append(base)
            mod_list.append(base - 0.25)
            opp_name = clubs.loc[clubs["id"] == r["away_club_id"], "short_name"].values[0]
            opp_list.append(f"{opp_name} (H)")
        for _, r in a_fix.iterrows():
            base = float(r["team_a_difficulty"])
            base_list.append(base)
            mod_list.append(base + 0.25)
            opp_name = clubs.loc[clubs["id"] == r["home_club_id"], "short_name"].values[0]
            opp_list.append(f"{opp_name} (A)")

        club_gw_fdr[(c_id, gw)] = {
            "base_fdr": np.mean(base_list) if base_list else 3.0,
            "mod_fdr": np.mean(mod_list) if mod_list else 3.0,
            "opp": ", ".join(opp_list) if opp_list else "BLANK",
        }

# 3. Standalone DEF stats per club (cheapest regular starter baseline)
solo_stats = []
for c_id in sorted(clubs["id"].unique()):
    c_info = clubs[clubs["id"] == c_id].iloc[0]
    p_lead = club_starters[c_id][0]
    h_fix = gw1_19[gw1_19["home_club_id"] == c_id]
    a_fix = gw1_19[gw1_19["away_club_id"] == c_id]
    home_base_sum = h_fix["team_h_difficulty"].sum()
    away_base_sum = a_fix["team_a_difficulty"].sum()
    total_base = home_base_sum + away_base_sum
    total_mod = (home_base_sum - 0.25 * len(h_fix)) + (away_base_sum + 0.25 * len(a_fix))

    solo_stats.append({
        "club_id": c_id,
        "club_name": c_info["name"],
        "club_short": c_info["short_name"],
        "player_name": p_lead["player_name"],
        "cost": p_lead["cost"],
        "expected_role": p_lead["expected_role"],
        "home_matches": len(h_fix),
        "away_matches": len(a_fix),
        "total_base_fdr": total_base,
        "total_mod_fdr": total_mod,
        "avg_mod_fdr": round(total_mod / 19.0, 3),
    })

df_solo = pd.DataFrame(solo_stats).sort_values("total_mod_fdr").reset_index(drop=True)
df_solo.to_csv(os.path.join(OUTPUT_DIR, "starting_defs_gw1_19.csv"), index=False)
print(f"Saved starting_defs_gw1_19.csv ({len(df_solo)} rows)")

# 4. Combinatorics for all 5-DEF sets (up to 3 per club)
club_ids = sorted(clubs["id"].unique())
c_names = dict(zip(clubs["id"], clubs["short_name"]))

combos = []
for c in itertools.combinations_with_replacement(range(len(club_ids)), 5):
    counts = [c.count(x) for x in set(c)]
    if max(counts) <= 3:
        combos.append(c)

print(f"Total valid 5-DEF club combinations: {len(combos)}")

# Pre-build lookup matrices for vectorized calculation
# mod_mat shape: (20, 19), base_mat shape: (20, 19)
mod_mat = np.zeros((len(club_ids), 19))
base_mat = np.zeros((len(club_ids), 19))
for i, c_id in enumerate(club_ids):
    for gw in range(1, 20):
        mod_mat[i, gw - 1] = club_gw_fdr[(c_id, gw)]["mod_fdr"]
        base_mat[i, gw - 1] = club_gw_fdr[(c_id, gw)]["base_fdr"]

combo_arr = np.array(combos)  # (42104, 5)

# Extract FDRs: (42104, 5, 19)
mod_fdrs = mod_mat[combo_arr]
base_fdrs = base_mat[combo_arr]

# Sort mod FDRs across the 5 defenders: (42104, 5, 19)
sort_indices = np.argsort(mod_fdrs, axis=1)
sorted_mod = np.take_along_axis(mod_fdrs, sort_indices, axis=1)
sorted_base = np.take_along_axis(base_fdrs, sort_indices, axis=1)

# Sum lowest 3 each GW: (42104, 19)
lineup_mod_gw = np.sum(sorted_mod[:, :3, :], axis=1)
lineup_base_gw = np.sum(sorted_base[:, :3, :], axis=1)

total_mod_fdr = np.sum(lineup_mod_gw, axis=1)
total_base_fdr = np.sum(lineup_base_gw, axis=1)
avg_def_mod_fdr = total_mod_fdr / (19.0 * 3.0)
avg_def_base_fdr = total_base_fdr / (19.0 * 3.0)

club_shorts_per_set = [
    tuple(c_names[club_ids[ci]] for ci in c_indices) for c_indices in combos
]
df_occupancy = build_club_occupancy_table(
    club_shorts_per_set, total_mod_fdr, total_base_fdr
)
df_occupancy.to_csv(
    os.path.join(OUTPUT_DIR, "def_rotation_club_occupancy.csv"), index=False
)
print(f"Saved def_rotation_club_occupancy.csv ({len(df_occupancy)} rows)")

# Build summary records
summary_rows = []
for idx, c_indices in enumerate(combos):
    club_counts = {}
    for ci in c_indices:
        club_counts[ci] = club_counts.get(ci, 0) + 1

    assigned_players = []
    for ci, count in sorted(club_counts.items()):
        c_id = club_ids[ci]
        for k in range(count):
            p = club_starters[c_id][k] if k < len(club_starters[c_id]) else club_starters[c_id][-1]
            assigned_players.append(p)

    # Sort players by cost descending
    assigned_players = sorted(assigned_players, key=lambda x: x["cost"], reverse=True)
    combined_cost = round(sum(p["cost"] for p in assigned_players), 1)

    # Archetype classification
    costs = [p["cost"] for p in assigned_players]
    premiums = [c for c in costs if c >= 5.5]
    budget_count = sum(1 for c in costs if c <= 4.5)

    if budget_count == 5:
        archetype = "Pure Budget"
    elif len(premiums) == 1 and budget_count == 4:
        archetype = "1-Premium Anchor"
    elif len(premiums) == 2 and budget_count == 3:
        archetype = "2-Premium Anchor"
    else:
        archetype = "Other"

    # Distinct clubs flag
    is_distinct = len(set(c_indices)) == 5

    names_str = " + ".join(f"{p['player_name']} ({p['club_short']})" for p in assigned_players)
    clubs_str = "-".join(p["club_short"] for p in assigned_players)

    summary_rows.append({
        "set_id": idx + 1,
        "set_label": names_str,
        "clubs": clubs_str,
        "archetype": archetype,
        "is_distinct_clubs": is_distinct,
        "combined_cost": combined_cost,
        "total_mod_fdr": round(float(total_mod_fdr[idx]), 2),
        "total_base_fdr": round(float(total_base_fdr[idx]), 2),
        "avg_def_mod_fdr": round(float(avg_def_mod_fdr[idx]), 3),
        "avg_def_base_fdr": round(float(avg_def_base_fdr[idx]), 3),
        "player1": f"{assigned_players[0]['player_name']} ({assigned_players[0]['club_short']}, £{assigned_players[0]['cost']}m)",
        "player2": f"{assigned_players[1]['player_name']} ({assigned_players[1]['club_short']}, £{assigned_players[1]['cost']}m)",
        "player3": f"{assigned_players[2]['player_name']} ({assigned_players[2]['club_short']}, £{assigned_players[2]['cost']}m)",
        "player4": f"{assigned_players[3]['player_name']} ({assigned_players[3]['club_short']}, £{assigned_players[3]['cost']}m)",
        "player5": f"{assigned_players[4]['player_name']} ({assigned_players[4]['club_short']}, £{assigned_players[4]['cost']}m)",
    })

df_summary = pd.DataFrame(summary_rows).sort_values(
    by=["combined_cost", "total_mod_fdr", "total_base_fdr"]
).reset_index(drop=True)

df_summary.to_csv(os.path.join(OUTPUT_DIR, "def_rotation_5sets_summary.csv"), index=False)
print(f"Saved def_rotation_5sets_summary.csv ({len(df_summary)} rows)")

# 5. Gameweek Schedule Picks for Key Representative Sets
def find_set(club_list):
    sorted_target = sorted(club_list)
    for _, row in df_summary.iterrows():
        c_list = sorted(row["clubs"].split("-"))
        if c_list == sorted_target:
            return row
    return None

key_set_configs = [
    ("Pure Budget (Double COV)", ["COV", "COV", "LEE", "NFO", "SUN"]),
    ("Pure Budget (5 Distinct)", ["COV", "FUL", "LEE", "NFO", "SUN"]),
    ("1-Premium Anchor (MCI + Budget)", ["MCI", "COV", "COV", "LEE", "SUN"]),
    ("1-Premium Anchor (5 Distinct)", ["MCI", "COV", "LEE", "NFO", "SUN"]),
    ("2-Premium Anchor (MCI + LIV)", ["MCI", "LIV", "COV", "LEE", "SUN"]),
    ("Global Best Lineup (Double MCI + LIV)", ["MCI", "MCI", "LIV", "COV", "MUN"]),
]

sched_rows = []
for label, c_list in key_set_configs:
    match_row = find_set(c_list)
    if match_row is None:
        continue

    # Reconstruct the 5 player definitions
    c_counts = {}
    for c_short in c_list:
        c_counts[c_short] = c_counts.get(c_short, 0) + 1

    set_players = []
    for c_short, count in sorted(c_counts.items()):
        c_id = clubs.loc[clubs["short_name"] == c_short, "id"].values[0]
        for k in range(count):
            p = club_starters[c_id][k] if k < len(club_starters[c_id]) else club_starters[c_id][-1]
            set_players.append(p)

    for gw in range(1, 20):
        # Evaluate each defender for this GW
        def_gw_eval = []
        for p in set_players:
            fdr_info = club_gw_fdr[(p["club_id"], gw)]
            def_gw_eval.append({
                "player_name": p["player_name"],
                "club_short": p["club_short"],
                "cost": p["cost"],
                "opp": fdr_info["opp"],
                "mod_fdr": fdr_info["mod_fdr"],
                "base_fdr": fdr_info["base_fdr"],
            })

        # Sort by mod_fdr
        sorted_eval = sorted(def_gw_eval, key=lambda x: x["mod_fdr"])
        starters_gw = sorted_eval[:3]
        benched_gw = sorted_eval[3:]

        gw_mod_sum = sum(s["mod_fdr"] for s in starters_gw)
        gw_avg_def_fdr = gw_mod_sum / 3.0

        sched_rows.append({
            "set_label": f"{label} [£{match_row['combined_cost']}m, Total FDR {match_row['total_mod_fdr']}]",
            "gameweek": gw,
            "starter_1": f"{starters_gw[0]['player_name']} ({starters_gw[0]['club_short']}) vs {starters_gw[0]['opp']} [{starters_gw[0]['mod_fdr']}]",
            "starter_2": f"{starters_gw[1]['player_name']} ({starters_gw[1]['club_short']}) vs {starters_gw[1]['opp']} [{starters_gw[1]['mod_fdr']}]",
            "starter_3": f"{starters_gw[2]['player_name']} ({starters_gw[2]['club_short']}) vs {starters_gw[2]['opp']} [{starters_gw[2]['mod_fdr']}]",
            "bench_1": f"{benched_gw[0]['player_name']} ({benched_gw[0]['club_short']}) vs {benched_gw[0]['opp']} [{benched_gw[0]['mod_fdr']}]",
            "bench_2": f"{benched_gw[1]['player_name']} ({benched_gw[1]['club_short']}) vs {benched_gw[1]['opp']} [{benched_gw[1]['mod_fdr']}]",
            "lineup_mod_fdr_sum": round(gw_mod_sum, 2),
            "lineup_avg_def_fdr": round(gw_avg_def_fdr, 3),
        })

df_sched = pd.DataFrame(sched_rows)
df_sched.to_csv(os.path.join(OUTPUT_DIR, "gw1_19_def_rotation_schedule_picks.csv"), index=False)
print(f"Saved gw1_19_def_rotation_schedule_picks.csv ({len(df_sched)} rows)")
