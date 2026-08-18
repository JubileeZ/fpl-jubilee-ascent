"""2025/26 Historical GKP Backtest: Revised Category Averages (Regular Starters)

Evaluates empirical 2025/26 FPL season data for regular starting goalkeepers (starts >= 25):
1. All Premium Set & Forget (£5.5m+ at start of season).
2. Solo Budget £4.5m Set & Forget (£4.5m starters at start of season + £4.0m bench).
3. All valid Regular Pair Rotations (£9.0m-£9.6m total budget, filtered for regular starters).
"""

from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive" / "2025-26" / "processed"
OUT_DIR = PROJECT_ROOT / "data" / "archive" / "gkp-fixture-rotation"


def run_historical_backtest():
    players = pd.read_parquet(ARCHIVE_DIR / "players.parquet")
    clubs = pd.read_parquet(ARCHIVE_DIR / "clubs.parquet")
    fixtures = pd.read_parquet(ARCHIVE_DIR / "fixtures.parquet")
    perf = pd.read_parquet(ARCHIVE_DIR / "player_performances.parquet")

    # Filter Goalkeepers (position_id == 1)
    gkps = players[players["position_id"] == 1].copy()
    gkp_ids = gkps["id"].tolist()
    
    perf_gkp = perf[perf["player_id"].isin(gkp_ids)].copy()

    # Calculate season totals per goalkeeper from performance log
    gkp_stats = perf_gkp.groupby("player_id").agg(
        total_pts=("total_points", "sum"),
        minutes=("minutes", "sum"),
        starts=("starts", "sum"),
        clean_sheets=("clean_sheets", "sum"),
        saves=("saves", "sum"),
        bonus=("bonus", "sum"),
    ).reset_index()

    starters = pd.merge(gkps[["id", "web_name", "club_id", "now_cost"]], gkp_stats, left_on="id", right_on="player_id")
    # Filter for regular starters (starts >= 25 in 2025/26) to prevent non-playing noise
    reg_starters = starters[starters["starts"] >= 25].copy()
    reg_starters["start_price"] = reg_starters["now_cost"] / 10.0

    # Build weekly points lookup: player_id -> {gw: total_points}
    weekly_pts = {}
    for p_id in reg_starters["id"].unique():
        p_perf = perf_gkp[perf_gkp["player_id"] == p_id]
        weekly_pts[p_id] = p_perf.set_index("gameweek_id")["total_points"].to_dict()

    # Build weekly FDR lookup per club: club_id -> {gw: FDR} and is_home
    club_fdr = {c_id: {} for c_id in clubs["id"].unique()}
    club_is_home = {c_id: {} for c_id in clubs["id"].unique()}

    for _, f in fixtures.iterrows():
        gw = int(f["gameweek_id"])
        h_club = int(f["home_club_id"])
        a_club = int(f["away_club_id"])
        h_diff = float(f["team_h_difficulty"])
        a_diff = float(f["team_a_difficulty"])

        club_fdr[h_club][gw] = min(club_fdr[h_club].get(gw, 99), h_diff)
        club_fdr[a_club][gw] = min(club_fdr[a_club].get(gw, 99), a_diff)
        club_is_home[h_club][gw] = True
        club_is_home[a_club][gw] = False

    # 1. Premium S&F (£5.5m+)
    premiums = reg_starters[reg_starters["start_price"] >= 5.5].copy()
    premiums["total_cost"] = premiums["start_price"] + 4.0

    # 2. Solo Budget £4.5m S&F (£4.5m-£4.6m)
    budgets_45 = reg_starters[(reg_starters["start_price"] >= 4.5) & (reg_starters["start_price"] <= 4.6)].copy()
    budgets_45["total_cost"] = budgets_45["start_price"] + 4.0

    # 3. Regular Pair Rotations (£9.0m-£9.6m)
    starter_list = reg_starters.to_dict("records")
    pair_results = []
    all_gws = list(range(1, 39))

    for i in range(len(starter_list)):
        for j in range(i + 1, len(starter_list)):
            g1, g2 = starter_list[i], starter_list[j]
            if g1["club_id"] == g2["club_id"]:
                continue
            
            tot_price = g1["start_price"] + g2["start_price"]
            if tot_price > 9.6:
                continue
            if min(g1["start_price"], g2["start_price"]) > 5.0:
                continue

            id1, id2 = g1["id"], g2["id"]
            c1, c2 = g1["club_id"], g2["club_id"]

            fdr_pts_total = 0
            hindsight_pts_total = 0

            for gw in all_gws:
                pts1 = weekly_pts[id1].get(gw, 0)
                pts2 = weekly_pts[id2].get(gw, 0)

                fdr1 = club_fdr[c1].get(gw, 3)
                fdr2 = club_fdr[c2].get(gw, 3)

                home1 = club_is_home[c1].get(gw, False)
                home2 = club_is_home[c2].get(gw, False)

                if fdr1 < fdr2:
                    start_choice = 1
                elif fdr2 < fdr1:
                    start_choice = 2
                else:
                    if home1 and not home2:
                        start_choice = 1
                    elif home2 and not home1:
                        start_choice = 2
                    else:
                        start_choice = 1

                if start_choice == 1:
                    fdr_pts_total += pts1
                else:
                    fdr_pts_total += pts2

                hindsight_pts_total += max(pts1, pts2)

            pair_results.append({
                "gkp1": g1["web_name"],
                "price1": g1["start_price"],
                "gkp2": g2["web_name"],
                "price2": g2["start_price"],
                "total_price": tot_price,
                "fdr_rotation_pts": fdr_pts_total,
                "hindsight_pts": hindsight_pts_total,
            })

    df_pairs = pd.DataFrame(pair_results).sort_values("fdr_rotation_pts", ascending=False)
    top5_pairs = df_pairs.head(5)

    summary_df = pd.DataFrame([
        {
            "category": "All Premiums S&F (£5.5m+)",
            "sample_size": len(premiums),
            "avg_cost": round(premiums["total_cost"].mean(), 2),
            "avg_pts": round(premiums["total_pts"].mean(), 1),
            "pts_per_million": round(premiums["total_pts"].mean() / premiums["total_cost"].mean(), 2),
        },
        {
            "category": "All Solo Budget £4.5m S&F (£4.5m-£4.6m)",
            "sample_size": len(budgets_45),
            "avg_cost": round(budgets_45["total_cost"].mean(), 2),
            "avg_pts": round(budgets_45["total_pts"].mean(), 1),
            "pts_per_million": round(budgets_45["total_pts"].mean() / budgets_45["total_cost"].mean(), 2),
        },
        {
            "category": "All Regular Pair Rotations (FDR Rule)",
            "sample_size": len(df_pairs),
            "avg_cost": round(df_pairs["total_price"].mean(), 2),
            "avg_pts": round(df_pairs["fdr_rotation_pts"].mean(), 1),
            "pts_per_million": round(df_pairs["fdr_rotation_pts"].mean() / df_pairs["total_price"].mean(), 2),
        },
        {
            "category": "Top 5 Regular Pair Rotations (FDR Rule)",
            "sample_size": len(top5_pairs),
            "avg_cost": round(top5_pairs["total_price"].mean(), 2),
            "avg_pts": round(top5_pairs["fdr_rotation_pts"].mean(), 1),
            "pts_per_million": round(top5_pairs["fdr_rotation_pts"].mean() / top5_pairs["total_price"].mean(), 2),
        },
        {
            "category": "All Regular Pair Rotations (Hindsight Best)",
            "sample_size": len(df_pairs),
            "avg_cost": round(df_pairs["total_price"].mean(), 2),
            "avg_pts": round(df_pairs["hindsight_pts"].mean(), 1),
            "pts_per_million": round(df_pairs["hindsight_pts"].mean() / df_pairs["total_price"].mean(), 2),
        },
    ])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df_pairs.to_csv(OUT_DIR / "historical_pair_rotations_regular_starters_2025_26.csv", index=False)
    summary_df.to_csv(OUT_DIR / "historical_revised_category_averages_2025_26.csv", index=False)

    print("=== REVISED REGULAR STARTER CATEGORY AVERAGES ===")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    run_historical_backtest()
