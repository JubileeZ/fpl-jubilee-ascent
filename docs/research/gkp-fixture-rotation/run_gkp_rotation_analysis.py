"""GKP Fixture Rotation & FDR Correlation Analysis script.

Calculates Pearson correlation of FDR sequences and rotated effective FDR for all genuine starter
goalkeeper pairs (Nailed Starter or Regular Starter in expected-role-gw1-5.csv) with combined cost <= £9.5m
across multiple planning horizons.
"""

from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
RESEARCH_DIR = PROJECT_ROOT / "data" / "research"
OUT_DIR = RESEARCH_DIR / "gkp-fixture-rotation"


def run_analysis() -> pd.DataFrame:
    players = pd.read_parquet(DATA_DIR / "players.parquet")
    clubs = pd.read_parquet(DATA_DIR / "clubs.parquet")
    fixtures = pd.read_parquet(DATA_DIR / "fixtures.parquet")
    exp_roles = pd.read_csv(RESEARCH_DIR / "expected-role-gw1-5" / "expected-role-gw1-5.csv")

    # Filter strictly for genuine starting goalkeepers (Nailed Starter or Regular Starter)
    starters = exp_roles[
        (exp_roles["position"] == "GKP")
        & (exp_roles["expected_role"].isin(["Nailed Starter", "Regular Starter"]))
    ].copy()
    starters["price"] = starters["player_id"].map(players.set_index("id")["now_cost"] / 10.0)
    starters["club_id"] = starters["player_id"].map(players.set_index("id")["club_id"])

    # Build FDR matrix
    club_ids = sorted(clubs["id"].tolist())
    fdr_matrix = {c_id: {} for c_id in club_ids}

    for _, f in fixtures.iterrows():
        gw = int(f["gameweek_id"])
        h_club = int(f["home_club_id"])
        a_club = int(f["away_club_id"])
        h_diff = float(f["team_h_difficulty"])
        a_diff = float(f["team_a_difficulty"])

        fdr_matrix[h_club][gw] = min(fdr_matrix[h_club].get(gw, 99), h_diff)
        fdr_matrix[a_club][gw] = min(fdr_matrix[a_club].get(gw, 99), a_diff)

    df_fdr = pd.DataFrame(fdr_matrix)

    horizons = [
        ("gw1_6", 1, 6),
        ("gw1_10", 1, 10),
        ("gw1_19", 1, 19),
        ("full_season", 1, 38),
    ]

    all_rows = []
    starter_records = starters.to_dict("records")

    for h_name, start_gw, end_gw in horizons:
        sub_fdr = df_fdr.loc[start_gw:end_gw]
        num_gws = end_gw - start_gw + 1

        for i in range(len(starter_records)):
            for j in range(i + 1, len(starter_records)):
                g1, g2 = starter_records[i], starter_records[j]
                c1, c2 = int(g1["club_id"]), int(g2["club_id"])

                if c1 == c2:
                    continue

                tot_price = g1["price"] + g2["price"]
                if tot_price > 9.5:
                    continue

                s1 = sub_fdr[c1]
                s2 = sub_fdr[c2]

                corr = s1.corr(s2)
                avg1 = s1.mean()
                avg2 = s2.mean()
                rotated = np.minimum(s1.values, s2.values)
                rot_avg = rotated.mean()
                best_single = min(avg1, avg2)
                gain = best_single - rot_avg
                easy_gws = int(np.sum(rotated <= 2))

                all_rows.append(
                    {
                        "horizon": h_name,
                        "start_gw": start_gw,
                        "end_gw": end_gw,
                        "club1": g1["club_short"],
                        "gkp1": g1["web_name"],
                        "role1": g1["expected_role"],
                        "price1": g1["price"],
                        "club2": g2["club_short"],
                        "gkp2": g2["web_name"],
                        "role2": g2["expected_role"],
                        "price2": g2["price"],
                        "total_price": tot_price,
                        "fdr_corr": round(corr, 4),
                        "avg_fdr1": round(avg1, 4),
                        "avg_fdr2": round(avg2, 4),
                        "rotated_avg_fdr": round(rot_avg, 4),
                        "fdr_gain": round(gain, 4),
                        "easy_gws": easy_gws,
                        "easy_gw_pct": round(easy_gws / num_gws * 100, 1),
                    }
                )

    res_df = pd.DataFrame(all_rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res_df.to_csv(OUT_DIR / "gkp_rotation_matrix.csv", index=False)
    return res_df


if __name__ == "__main__":
    df = run_analysis()
    print(f"Generated {len(df)} genuine starter GKP rotation records in {OUT_DIR / 'gkp_rotation_matrix.csv'}")
