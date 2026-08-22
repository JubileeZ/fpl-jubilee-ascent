"""
GKP FDR Rotation Runner (GW1-19)
Generates companion CSV artifacts for docs/research/gkp-fdr-rotation-gw1-19/
"""

import pandas as pd
import numpy as np
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Load data
fixtures = pd.read_parquet("data/processed/fixtures.parquet")
clubs = pd.read_parquet("data/processed/clubs.parquet")
players = pd.read_parquet("data/processed/players.parquet")

predicted_gkps = [
    ("Arsenal", "Raya"),
    ("Aston Villa", "Suzuki"),
    ("Bournemouth", "Petrović"),
    ("Brentford", "Kelleher"),
    ("Brighton", "Verbruggen"),
    ("Chelsea", "Sánchez"),
    ("Coventry City", "Rushworth"),
    ("Crystal Palace", "Henderson"),
    ("Everton", "Pickford"),
    ("Fulham", "Leno"),
    ("Hull City", "Tzolakis"),
    ("Ipswich Town", "Scherpen"),
    ("Leeds", "Trafford"),
    ("Liverpool", "A.Becker"),
    ("Man City", "Donnarumma"),
    ("Man Utd", "Lammens"),
    ("Newcastle", "Horníček"),
    ("Nott'm Forest", "Sels"),
    ("Spurs", "Kinsky"),
    ("Sunderland", "Roefs")
]

gkp_data = []
for club_name, gkp_name in predicted_gkps:
    club = clubs[clubs["name"] == club_name].iloc[0]
    p = players[(players["club_id"] == club["id"]) & (players["position_id"] == 1)]
    match = p[p["web_name"].str.lower() == gkp_name.lower()]
    if len(match) == 0:
        match = p[p["web_name"].str.contains(gkp_name, case=False)]
    row = match.iloc[0]
    gkp_data.append({
        "club_id": club["id"],
        "club_name": club["name"],
        "club_short": club["short_name"],
        "player_id": row["id"],
        "player_name": row["web_name"],
        "cost": row["now_cost"] / 10.0
    })
df_gkp = pd.DataFrame(gkp_data)

gw1_19 = fixtures[(fixtures["gameweek_id"] >= 1) & (fixtures["gameweek_id"] <= 19)]

# Standalone stats
solo_stats = []
team_gw_fdr = {}

for club_id in clubs["id"]:
    for gw in range(1, 20):
        home_fix = gw1_19[(gw1_19["gameweek_id"] == gw) & (gw1_19["home_club_id"] == club_id)]
        away_fix = gw1_19[(gw1_19["gameweek_id"] == gw) & (gw1_19["away_club_id"] == club_id)]
        
        base_list, mod_list, opp_list = [], [], []
        for _, r in home_fix.iterrows():
            base = float(r["team_h_difficulty"])
            base_list.append(base)
            mod_list.append(base - 0.25)
            opp_list.append(clubs.loc[clubs["id"] == r["away_club_id"], "short_name"].values[0] + " (H)")
        for _, r in away_fix.iterrows():
            base = float(r["team_a_difficulty"])
            base_list.append(base)
            mod_list.append(base + 0.25)
            opp_list.append(clubs.loc[clubs["id"] == r["home_club_id"], "short_name"].values[0] + " (A)")
            
        team_gw_fdr[(club_id, gw)] = {
            "base_fdr": np.mean(base_list),
            "mod_fdr": np.mean(mod_list),
            "opp": ", ".join(opp_list)
        }

for _, row in df_gkp.iterrows():
    c_id = row["club_id"]
    h_fix = gw1_19[gw1_19["home_club_id"] == c_id]
    a_fix = gw1_19[gw1_19["away_club_id"] == c_id]
    home_base_sum = h_fix["team_h_difficulty"].sum()
    away_base_sum = a_fix["team_a_difficulty"].sum()
    total_base = home_base_sum + away_base_sum
    total_mod = (home_base_sum - 0.25 * len(h_fix)) + (away_base_sum + 0.25 * len(a_fix))
    
    solo_stats.append({
        "club_name": row["club_name"],
        "club_short": row["club_short"],
        "player_name": row["player_name"],
        "cost": row["cost"],
        "home_matches": len(h_fix),
        "away_matches": len(a_fix),
        "total_base_fdr": total_base,
        "total_mod_fdr": total_mod,
        "avg_mod_fdr": round(total_mod / 19.0, 3)
    })

df_solo = pd.DataFrame(solo_stats).sort_values("total_mod_fdr").reset_index(drop=True)
df_solo.to_csv(os.path.join(OUTPUT_DIR, "starting_gkps_gw1_19.csv"), index=False)
print("Saved starting_gkps_gw1_19.csv")

# Generate all pairs
all_pairs = []
n = len(df_gkp)
for i in range(n):
    for j in range(i + 1, n):
        g1, g2 = df_gkp.iloc[i], df_gkp.iloc[j]
        combined_cost = g1["cost"] + g2["cost"]
        mod_sum, base_sum = 0.0, 0.0
        
        for gw in range(1, 20):
            f1 = team_gw_fdr[(g1["club_id"], gw)]
            f2 = team_gw_fdr[(g2["club_id"], gw)]
            mod_sum += min(f1["mod_fdr"], f2["mod_fdr"])
            base_sum += min(f1["base_fdr"], f2["base_fdr"])
            
        all_pairs.append({
            "pair_name": f"{g1['player_name']} ({g1['club_short']}) + {g2['player_name']} ({g2['club_short']})",
            "gkp1_name": g1["player_name"],
            "gkp1_club": g1["club_short"],
            "gkp1_cost": g1["cost"],
            "gkp2_name": g2["player_name"],
            "gkp2_club": g2["club_short"],
            "gkp2_cost": g2["cost"],
            "combined_cost": combined_cost,
            "total_mod_fdr": round(mod_sum, 2),
            "total_base_fdr": round(base_sum, 2),
            "avg_mod_fdr": round(mod_sum / 19.0, 3),
            "avg_base_fdr": round(base_sum / 19.0, 3)
        })

df_pairs = pd.DataFrame(all_pairs).sort_values(by=["combined_cost", "total_mod_fdr", "total_base_fdr"]).reset_index(drop=True)
df_pairs.to_csv(os.path.join(OUTPUT_DIR, "gkp_rotation_pairs_summary.csv"), index=False)
print("Saved gkp_rotation_pairs_summary.csv")

# GW picks for selected representative top pairs
key_pairs = [
    ("NFO", "TOT", "Sels (NFO, £5.0m) + Kinsky (TOT, £4.5m)"),
    ("BOU", "IPS", "Petrović (BOU, £4.5m) + Scherpen (IPS, £4.5m)"),
    ("COV", "MCI", "Rushworth (COV, £4.5m) + Donnarumma (MCI, £5.5m)"),
    ("MCI", "MUN", "Donnarumma (MCI, £5.5m) + Lammens (MUN, £5.0m)")
]

sched_rows = []
for c1_short, c2_short, label in key_pairs:
    c1 = df_gkp[df_gkp["club_short"] == c1_short].iloc[0]
    c2 = df_gkp[df_gkp["club_short"] == c2_short].iloc[0]
    for gw in range(1, 20):
        f1 = team_gw_fdr[(c1["club_id"], gw)]
        f2 = team_gw_fdr[(c2["club_id"], gw)]
        if f1["mod_fdr"] <= f2["mod_fdr"]:
            picked_gkp = c1["player_name"]
            picked_opp = f1["opp"]
            picked_fdr = f1["mod_fdr"]
        else:
            picked_gkp = c2["player_name"]
            picked_opp = f2["opp"]
            picked_fdr = f2["mod_fdr"]
            
        sched_rows.append({
            "pair_label": label,
            "gameweek": gw,
            "gkp1_opp": f1["opp"],
            "gkp1_mod_fdr": f1["mod_fdr"],
            "gkp2_opp": f2["opp"],
            "gkp2_mod_fdr": f2["mod_fdr"],
            "started_gkp": picked_gkp,
            "started_fixture": picked_opp,
            "effective_mod_fdr": picked_fdr
        })

df_sched = pd.DataFrame(sched_rows)
df_sched.to_csv(os.path.join(OUTPUT_DIR, "gw1_19_rotation_schedule_picks.csv"), index=False)
print("Saved gw1_19_rotation_schedule_picks.csv")
