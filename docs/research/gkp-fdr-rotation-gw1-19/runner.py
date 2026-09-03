"""GKP FDR Rotation Runner (GW1-19). Companion CSVs for this topic folder."""

from __future__ import annotations

import os
from typing import Any

import httpx
import numpy as np
import pandas as pd

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
MOD_FDR_LE_THRESH = 2.25

# Club + starting GKP web_name. Club is the shirt we rotate; name is the FPL asset.
PREDICTED_GKPS: list[tuple[str, str]] = [
    ("Arsenal", "Raya"),
    ("Aston Villa", "Suzuki"),
    ("Bournemouth", "Petrović"),
    ("Brentford", "Kelleher"),
    ("Brighton", "Verbruggen"),
    ("Chelsea", "Martinez"),
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
    ("Sunderland", "Roefs"),
]


def _fetch_bootstrap_elements() -> list[dict[str, Any]] | None:
    try:
        with httpx.Client(timeout=30.0, headers={"User-Agent": "fpl-jubilee-ascent-research"}) as client:
            response = client.get(BOOTSTRAP_URL)
            response.raise_for_status()
            payload = response.json()
            elements = payload.get("elements")
            return elements if isinstance(elements, list) else None
    except (httpx.HTTPError, ValueError):
        return None


def _match_gkp(elements: list[dict[str, Any]], web_name: str) -> dict[str, Any] | None:
    needle = web_name.lower()
    exact = [e for e in elements if int(e.get("element_type", 0)) == 1 and str(e.get("web_name", "")).lower() == needle]
    if exact:
        return exact[0]
    contains = [e for e in elements if int(e.get("element_type", 0)) == 1 and needle in str(e.get("web_name", "")).lower()]
    return contains[0] if contains else None


def build_gkp_frame(clubs: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    live_elements = _fetch_bootstrap_elements()
    rows: list[dict[str, Any]] = []
    for club_name, gkp_name in PREDICTED_GKPS:
        club = clubs[clubs["name"] == club_name].iloc[0]
        live = _match_gkp(live_elements, gkp_name) if live_elements is not None else None
        if live is not None:
            live_club_id = int(live["team"])
            if live_club_id != int(club["id"]):
                raise ValueError(f"{gkp_name} live club_id={live_club_id} != predicted {club_name} id={club['id']}")
            player_id = int(live["id"])
            player_name = str(live["web_name"])
            cost = float(live["now_cost"]) / 10.0
        else:
            pool = players[players["position_id"] == 1]
            match = pool[pool["web_name"].str.lower() == gkp_name.lower()]
            if match.empty:
                match = pool[pool["web_name"].str.contains(gkp_name, case=False, regex=False)]
            row = match.iloc[0]
            player_id = int(row["id"])
            player_name = str(row["web_name"])
            cost = float(row["now_cost"]) / 10.0
        rows.append({
            "club_id": int(club["id"]),
            "club_name": str(club["name"]),
            "club_short": str(club["short_name"]),
            "player_id": player_id,
            "player_name": player_name,
            "cost": cost,
        })
    return pd.DataFrame(rows)


def build_team_gw_fdr(clubs: pd.DataFrame, gw1_19: pd.DataFrame) -> dict[tuple[int, int], dict[str, Any]]:
    team_gw_fdr: dict[tuple[int, int], dict[str, Any]] = {}
    for club_id in clubs["id"]:
        for gw in range(1, 20):
            home_fix = gw1_19[(gw1_19["gameweek_id"] == gw) & (gw1_19["home_club_id"] == club_id)]
            away_fix = gw1_19[(gw1_19["gameweek_id"] == gw) & (gw1_19["away_club_id"] == club_id)]
            base_list: list[float] = []
            mod_list: list[float] = []
            opp_list: list[str] = []
            for _, r in home_fix.iterrows():
                base = float(r["team_h_difficulty"])
                base_list.append(base)
                mod_list.append(base - 0.25)
                opp_list.append(str(clubs.loc[clubs["id"] == r["away_club_id"], "short_name"].values[0]) + " (H)")
            for _, r in away_fix.iterrows():
                base = float(r["team_a_difficulty"])
                base_list.append(base)
                mod_list.append(base + 0.25)
                opp_list.append(str(clubs.loc[clubs["id"] == r["home_club_id"], "short_name"].values[0]) + " (A)")
            team_gw_fdr[(int(club_id), gw)] = {
                "base_fdr": float(np.mean(base_list)),
                "mod_fdr": float(np.mean(mod_list)),
                "opp": ", ".join(opp_list),
            }
    return team_gw_fdr


def main() -> None:
    fixtures = pd.read_parquet("data/processed/fixtures.parquet")
    clubs = pd.read_parquet("data/processed/clubs.parquet")
    players = pd.read_parquet("data/processed/players.parquet")
    df_gkp = build_gkp_frame(clubs, players)
    gw1_19 = fixtures[(fixtures["gameweek_id"] >= 1) & (fixtures["gameweek_id"] <= 19)]
    team_gw_fdr = build_team_gw_fdr(clubs, gw1_19)

    solo_stats: list[dict[str, Any]] = []
    for _, row in df_gkp.iterrows():
        c_id = int(row["club_id"])
        h_fix = gw1_19[gw1_19["home_club_id"] == c_id]
        a_fix = gw1_19[gw1_19["away_club_id"] == c_id]
        home_base_sum = float(h_fix["team_h_difficulty"].sum())
        away_base_sum = float(a_fix["team_a_difficulty"].sum())
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
            "avg_mod_fdr": round(total_mod / 19.0, 3),
        })
    df_solo = pd.DataFrame(solo_stats).sort_values("total_mod_fdr").reset_index(drop=True)
    df_solo.to_csv(os.path.join(OUTPUT_DIR, "starting_gkps_gw1_19.csv"), index=False)
    print("Saved starting_gkps_gw1_19.csv")

    all_pairs: list[dict[str, Any]] = []
    n = len(df_gkp)
    for i in range(n):
        for j in range(i + 1, n):
            g1, g2 = df_gkp.iloc[i], df_gkp.iloc[j]
            combined_cost = float(g1["cost"] + g2["cost"])
            weekly_mod: list[float] = []
            weekly_base: list[float] = []
            for gw in range(1, 20):
                f1 = team_gw_fdr[(int(g1["club_id"]), gw)]
                f2 = team_gw_fdr[(int(g2["club_id"]), gw)]
                weekly_mod.append(min(float(f1["mod_fdr"]), float(f2["mod_fdr"])))
                weekly_base.append(min(float(f1["base_fdr"]), float(f2["base_fdr"])))
            mod_arr = np.array(weekly_mod, dtype=float)
            n_le = int((mod_arr <= MOD_FDR_LE_THRESH).sum())
            all_pairs.append({
                "pair_name": f"{g1['player_name']} ({g1['club_short']}) + {g2['player_name']} ({g2['club_short']})",
                "gkp1_name": g1["player_name"],
                "gkp1_club": g1["club_short"],
                "gkp1_cost": g1["cost"],
                "gkp2_name": g2["player_name"],
                "gkp2_club": g2["club_short"],
                "gkp2_cost": g2["cost"],
                "combined_cost": round(combined_cost, 1),
                "combined_cost_band": round(round(combined_cost * 2) / 2, 1),
                "total_mod_fdr": round(float(mod_arr.sum()), 2),
                "total_base_fdr": round(float(np.sum(weekly_base)), 2),
                "avg_mod_fdr": round(float(mod_arr.mean()), 3),
                "avg_base_fdr": round(float(np.mean(weekly_base)), 3),
                "n_gw_mod_le_2_25": n_le,
                "pct_gw_mod_le_2_25": round(100.0 * n_le / 19.0, 1),
                "max_mod_fdr": round(float(mod_arr.max()), 2),
            })
    df_pairs = pd.DataFrame(all_pairs).sort_values(
        by=["combined_cost", "total_mod_fdr", "total_base_fdr"]
    ).reset_index(drop=True)
    df_pairs.to_csv(os.path.join(OUTPUT_DIR, "gkp_rotation_pairs_summary.csv"), index=False)
    print("Saved gkp_rotation_pairs_summary.csv")

    raya_mask = (df_pairs["gkp1_name"] == "Raya") | (df_pairs["gkp2_name"] == "Raya")
    raya_rows: list[dict[str, Any]] = []
    for _, r in df_pairs.loc[raya_mask].iterrows():
        if r["gkp1_name"] == "Raya":
            partner_name, partner_club, partner_cost = r["gkp2_name"], r["gkp2_club"], r["gkp2_cost"]
        else:
            partner_name, partner_club, partner_cost = r["gkp1_name"], r["gkp1_club"], r["gkp1_cost"]
        raya_rows.append({
            "raya_name": "Raya",
            "raya_club": "ARS",
            "raya_cost": 6.0,
            "partner_name": partner_name,
            "partner_club": partner_club,
            "partner_cost": partner_cost,
            "combined_cost": r["combined_cost"],
            "total_mod_fdr": r["total_mod_fdr"],
            "total_base_fdr": r["total_base_fdr"],
            "avg_mod_fdr": r["avg_mod_fdr"],
            "n_gw_mod_le_2_25": r["n_gw_mod_le_2_25"],
            "pct_gw_mod_le_2_25": r["pct_gw_mod_le_2_25"],
            "max_mod_fdr": r["max_mod_fdr"],
        })
    df_raya = pd.DataFrame(raya_rows).sort_values(
        by=["total_mod_fdr", "pct_gw_mod_le_2_25"], ascending=[True, False]
    ).reset_index(drop=True)
    df_raya.insert(0, "rank_total_mod_fdr", range(1, len(df_raya) + 1))
    df_raya.to_csv(os.path.join(OUTPUT_DIR, "raya_rotation_partners.csv"), index=False)
    print("Saved raya_rotation_partners.csv")

    key_pairs = [
        ("ARS", "MCI", "Raya (ARS, £6.0m) + Donnarumma (MCI, £5.5m)"),
        ("ARS", "TOT", "Raya (ARS, £6.0m) + Kinsky (TOT, £4.5m)"),
        ("NFO", "TOT", "Sels (NFO, £5.0m) + Kinsky (TOT, £4.5m)"),
        ("BOU", "IPS", "Petrović (BOU, £4.5m) + Scherpen (IPS, £4.5m)"),
        ("COV", "MCI", "Rushworth (COV, £4.5m) + Donnarumma (MCI, £5.5m)"),
    ]
    sched_rows: list[dict[str, Any]] = []
    for c1_short, c2_short, label in key_pairs:
        c1 = df_gkp[df_gkp["club_short"] == c1_short].iloc[0]
        c2 = df_gkp[df_gkp["club_short"] == c2_short].iloc[0]
        for gw in range(1, 20):
            f1 = team_gw_fdr[(int(c1["club_id"]), gw)]
            f2 = team_gw_fdr[(int(c2["club_id"]), gw)]
            if float(f1["mod_fdr"]) <= float(f2["mod_fdr"]):
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
                "effective_mod_fdr": picked_fdr,
            })
    pd.DataFrame(sched_rows).to_csv(os.path.join(OUTPUT_DIR, "gw1_19_rotation_schedule_picks.csv"), index=False)
    print("Saved gw1_19_rotation_schedule_picks.csv")


if __name__ == "__main__":
    main()
