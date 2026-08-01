"""Expected Stats GW1–5 builder: computes per-90 rates for Nailed & Regular Starters.

Applies 50% 2025/26 FPL season + 50% Career stats blending across a 3-season window (2023–2026).
For low-sample / foreign transfer players, incorporates 3-season European league match log research.
"""

import json
from pathlib import Path
import pandas as pd

# Position baselines derived from 2025/26 Premier League data
POSITION_BASELINES = {
    "GKP": {"xg": 0.00, "xa": 0.00, "defcon": 0.00, "saves": 2.78, "gc": 1.38},
    "DEF": {"xg": 0.06, "xa": 0.06, "defcon": 4.25, "saves": 0.00, "gc": 1.39},
    "MID": {"xg": 0.15, "xa": 0.15, "defcon": 3.10, "saves": 0.00, "gc": 1.37},
    "FWD": {"xg": 0.41, "xa": 0.13, "defcon": 1.50, "saves": 0.00, "gc": 1.41},
}

# External 3-season (2023-2026) research rates for foreign transfers & low PL sample players
EXTERNAL_RESEARCH_RATES = {
    25: {"xg": 0.770, "xa": 0.240, "defcon": 1.22, "saves": 0.00, "gc": 1.10, "note": "External 3-season research: Sporting CP / Arsenal 2023-26 (0.77 xG/90, 0.24 xA/90)"}, # Gyokeres
    217: {"xg": 0.340, "xa": 0.350, "defcon": 2.28, "saves": 0.00, "gc": 1.20, "note": "External 3-season research: Bayer Leverkusen / Liverpool 2023-26 (0.34 xG/90, 0.35 xA/90)"}, # Wirtz
    357: {"xg": 0.200, "xa": 0.250, "defcon": 2.81, "saves": 0.00, "gc": 1.25, "note": "External 3-season research: Bayer Leverkusen / Liverpool DEF 2023-26 (0.20 xG/90, 0.25 xA/90)"}, # Frimpong
    211: {"xg": 0.240, "xa": 0.200, "defcon": 2.55, "saves": 0.00, "gc": 1.30, "note": "External 3-season research: Villarreal / Crystal Palace 2023-26"}, # Yeremy
    514: {"xg": 0.370, "xa": 0.170, "defcon": 2.40, "saves": 0.00, "gc": 1.30, "note": "External 3-season research: Bayern Munich / Spurs 2023-26 (0.37 xG/90)"}, # Tel
    335: {"xg": 0.090, "xa": 0.140, "defcon": 5.71, "saves": 0.00, "gc": 1.35, "note": "External 3-season research: Hoffenheim / Leeds 2023-26 (5.71 def actions/90)"}, # Stach
    336: {"xg": 0.330, "xa": 0.110, "defcon": 1.40, "saves": 0.00, "gc": 1.35, "note": "External 3-season research: AC Milan / Leeds 2023-26 (0.33 xG/90)"}, # Okafor
    331: {"xg": 0.040, "xa": 0.050, "defcon": 6.15, "saves": 0.00, "gc": 1.30, "note": "External 3-season research: Lille / Leeds 2023-26 (6.15 def actions/90)"}, # Gudmundsson
    445: {"xg": 0.110, "xa": 0.020, "defcon": 8.78, "saves": 0.00, "gc": 1.15, "note": "External 3-season research: AC Milan / Newcastle DEF 2023-26 (8.78 def actions/90)"}, # Thiaw
    412: {"xg": 0.000, "xa": 0.000, "defcon": 0.00, "saves": 3.47, "gc": 1.15, "note": "External 3-season research: Royal Antwerp / Man Utd GKP 2023-26 (3.47 saves/90)"}, # Lammens
    533: {"xg": 0.090, "xa": 0.080, "defcon": 8.42, "saves": 0.00, "gc": 1.25, "note": "External 3-season research: PSG / Leverkusen / Sunderland 2023-26"}, # Mukiele
    535: {"xg": 0.060, "xa": 0.020, "defcon": 9.82, "saves": 0.00, "gc": 1.25, "note": "External 3-season research: Getafe / Sunderland 2023-26 (9.82 def actions/90)"}, # Alderete
    536: {"xg": 0.040, "xa": 0.020, "defcon": 7.24, "saves": 0.00, "gc": 1.25, "note": "External 3-season research: Atletico Madrid / Sunderland 2023-26"}, # Reinildo
    542: {"xg": 0.140, "xa": 0.200, "defcon": 5.31, "saves": 0.00, "gc": 1.30, "note": "External 3-season research: Rennes / Roma / Sunderland 2023-26"}, # E.Le Fée
    545: {"xg": 0.070, "xa": 0.080, "defcon": 6.25, "saves": 0.00, "gc": 1.30, "note": "External 3-season research: Union SG / Sunderland 2023-26"}, # Sadiki
    529: {"xg": 0.000, "xa": 0.000, "defcon": 0.00, "saves": 3.27, "gc": 1.31, "note": "External 3-season research: NEC Nijmegen / Sunderland GKP 2023-26 (3.27 saves/90)"}, # Roefs
    504: {"xg": 0.185, "xa": 0.035, "defcon": 11.72, "saves": 0.00, "gc": 1.46, "note": "External 3-season research: Westerlo / HSV 2024-26 match logs"}, # Vuskovic
    172: {"xg": 0.000, "xa": 0.000, "defcon": 0.00, "saves": 2.25, "gc": 1.07, "note": "External 3-season research: Coventry City GKP 2024-26 match logs"}, # Wilson
    182: {"xg": 0.035, "xa": 0.015, "defcon": 8.97, "saves": 0.00, "gc": 1.30, "note": "External 3-season research: Young Boys / Eintracht Frankfurt 2024-26"}, # Amenda
    175: {"xg": 0.035, "xa": 0.150, "defcon": 6.44, "saves": 0.00, "gc": 1.00, "note": "External 3-season research: Coventry City DEF 2024-26"}, # van Ewijk
    188: {"xg": 0.185, "xa": 0.205, "defcon": 3.96, "saves": 0.00, "gc": 1.35, "note": "External 3-season research: Coventry City MID 2024-26"}, # Torp
    186: {"xg": 0.255, "xa": 0.155, "defcon": 2.06, "saves": 0.00, "gc": 1.35, "note": "External 3-season research: Coventry City MID 2024-26"}, # Mason-Clark
    184: {"xg": 0.045, "xa": 0.205, "defcon": 4.90, "saves": 0.00, "gc": 1.25, "note": "External 3-season research: Swansea / Coventry City 2024-26"}, # Grimes
    247: {"xg": 0.105, "xa": 0.175, "defcon": 4.38, "saves": 0.00, "gc": 1.40, "note": "External 3-season research: Middlesbrough 2024-26 (Championship POTS)"}, # Hackney
    278: {"xg": 0.075, "xa": 0.055, "defcon": 7.75, "saves": 0.00, "gc": 1.16, "note": "External 3-season research: Preston North End 2024-26"}, # Hughes
    280: {"xg": 0.030, "xa": 0.125, "defcon": 6.65, "saves": 0.00, "gc": 1.24, "note": "External 3-season research: Hull City DEF 2024-26"}, # Coyle
    286: {"xg": 0.195, "xa": 0.215, "defcon": 2.55, "saves": 0.00, "gc": 1.50, "note": "External 3-season research: Farense / Hull City 2024-26"}, # Belloumi
    562: {"xg": 0.455, "xa": 0.175, "defcon": 2.90, "saves": 0.00, "gc": 1.20, "note": "External 3-season research: Celtic / Ipswich Town 2024-26"}, # Maeda
    334: {"xg": 0.070, "xa": 0.110, "defcon": 10.03, "saves": 0.00, "gc": 1.10, "note": "External 3-season research: Sassuolo / Juventus 2024-26"}, # Muharemovic
    362: {"xg": 0.045, "xa": 0.085, "defcon": 8.58, "saves": 0.00, "gc": 1.24, "note": "External 3-season research: Rennes / Clermont 2024-26"}, # Jacquet
    558: {"xg": 0.085, "xa": 0.100, "defcon": 7.01, "saves": 0.00, "gc": 1.20, "note": "External 3-season research: RB Leipzig 2024-26"}, # Schlager
}


def build_expected_stats(
    role_csv_path: str = "data/research/expected-role-gw1-5/expected-role-gw1-5.csv",
    perf_parquet_path: str = "data/archive/2025-26/processed/player_performances.parquet",
    output_csv_path: str = "data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv",
) -> pd.DataFrame:
    df_role = pd.read_csv(role_csv_path)
    shortlist = df_role[df_role["expected_role"].isin(["Nailed Starter", "Regular Starter"])].copy()

    df_perf25 = pd.read_parquet(perf_parquet_path)
    numeric_cols = ["minutes", "expected_goals", "expected_assists", "defensive_contribution", "saves", "goals_conceded"]
    for col in numeric_cols:
        df_perf25[col] = pd.to_numeric(df_perf25[col], errors="coerce").fillna(0)

    agg25 = df_perf25.groupby("player_id")[numeric_cols].sum().reset_index()

    rows = []
    for _, srow in shortlist.iterrows():
        pid = int(srow["player_id"])
        pos = srow["position"]
        p25 = agg25[agg25["player_id"] == pid]

        mins25 = float(p25["minutes"].iloc[0]) if len(p25) > 0 else 0.0
        xg25 = float(p25["expected_goals"].iloc[0]) if len(p25) > 0 else 0.0
        xa25 = float(p25["expected_assists"].iloc[0]) if len(p25) > 0 else 0.0
        defcon25 = float(p25["defensive_contribution"].iloc[0]) if len(p25) > 0 else 0.0
        saves25 = float(p25["saves"].iloc[0]) if len(p25) > 0 else 0.0
        gc25 = float(p25["goals_conceded"].iloc[0]) if len(p25) > 0 else 0.0

        mins_past = 0.0
        xg_past = 0.0
        xa_past = 0.0
        defcon_past = 0.0
        saves_past = 0.0
        gc_past = 0.0

        summary_file = Path(f"data/raw/element_summary_{pid}.json")
        if summary_file.exists():
            try:
                with open(summary_file) as f:
                    es = json.load(f)
                    # Filter history_past to last 3 seasons (2023/24, 2024/25, 2025/26)
                    for hp in es.get("history_past", []):
                        season = hp.get("season_name", "")
                        if season in {"2023/24", "2024/25", "2025/26"}:
                            m = float(hp.get("minutes", 0))
                            mins_past += m
                            xg_past += float(hp.get("expected_goals", 0.0))
                            xa_past += float(hp.get("expected_assists", 0.0))
                            defcon_past += float(hp.get("defensive_contribution", 0.0))
                            saves_past += float(hp.get("saves", 0.0))
                            gc_past += float(hp.get("goals_conceded", 0.0))
            except Exception:
                pass

        tot_mins = mins25 + mins_past

        if pid in EXTERNAL_RESEARCH_RATES:
            ext = EXTERNAL_RESEARCH_RATES[pid]
            per90_xg = ext["xg"]
            per90_xa = ext["xa"]
            per90_defcon = ext["defcon"]
            per90_saves = ext["saves"]
            per90_gc = ext["gc"]
            src = "external_3season_research"
            note = ext["note"]
        elif tot_mins >= 450:
            if mins25 >= 90 and mins_past >= 90:
                r25_xg, rpast_xg = (xg25 / mins25 * 90.0), (xg_past / mins_past * 90.0)
                r25_xa, rpast_xa = (xa25 / mins25 * 90.0), (xa_past / mins_past * 90.0)
                r25_def, rpast_def = (defcon25 / mins25 * 90.0), (defcon_past / mins_past * 90.0)
                r25_sav, rpast_sav = (saves25 / mins25 * 90.0), (saves_past / mins_past * 90.0)
                r25_gc, rpast_gc = (gc25 / mins25 * 90.0), (gc_past / mins_past * 90.0)

                per90_xg = 0.5 * r25_xg + 0.5 * rpast_xg
                per90_xa = 0.5 * r25_xa + 0.5 * rpast_xa
                per90_defcon = 0.5 * r25_def + 0.5 * rpast_def
                per90_saves = 0.5 * r25_sav + 0.5 * rpast_sav
                per90_gc = 0.5 * r25_gc + 0.5 * rpast_gc
                src = "fpl_historical_50_50"
                note = "50% 2025/26 + 50% 3-season FPL career history blend"
            elif mins25 >= 90:
                per90_xg = xg25 / mins25 * 90.0
                per90_xa = xa25 / mins25 * 90.0
                per90_defcon = defcon25 / mins25 * 90.0
                per90_saves = saves25 / mins25 * 90.0
                per90_gc = gc25 / mins25 * 90.0
                src = "fpl_2025_26_only"
                note = "100% 2025/26 FPL season history"
            else:
                per90_xg = xg_past / mins_past * 90.0
                per90_xa = xa_past / mins_past * 90.0
                per90_defcon = defcon_past / mins_past * 90.0
                per90_saves = saves_past / mins_past * 90.0
                per90_gc = gc_past / mins_past * 90.0
                src = "fpl_3season_career_only"
                note = "100% 3-season FPL career history"
        else:
            base = POSITION_BASELINES.get(pos, POSITION_BASELINES["MID"])
            per90_xg = base["xg"]
            per90_xa = base["xa"]
            per90_defcon = base["defcon"]
            per90_saves = base["saves"]
            per90_gc = base["gc"]
            src = "fallback_baseline"
            note = f"Position baseline ({pos}) fallback due to <450 mins sample"

        rows.append({
            "player_id": pid,
            "web_name": srow["web_name"],
            "club_short": srow["club_short"],
            "position": pos,
            "expected_role": srow["expected_role"],
            "p_start": srow.get("p_start_prior", 0.90 if srow["expected_role"] == "Nailed Starter" else 0.75),
            "p_sub_in": srow.get("p_sub_in_prior", 0.05 if srow["expected_role"] == "Nailed Starter" else 0.10),
            "p_dnp": srow.get("p_dnp_prior", 0.05 if srow["expected_role"] == "Nailed Starter" else 0.15),
            "xmins_if_start": srow.get("xmins_if_start", 85.0 if srow["expected_role"] == "Nailed Starter" else 80.0),
            "xmins_if_sub_in": srow.get("xmins_if_sub_in", 20.0),
            "draft_availability": srow.get("draft_availability", "eligible"),
            "availability_override": srow.get("availability_override", ""),
            "fpl_2025_26_mins": mins25,
            "fpl_career_mins": mins_past,
            "total_mins": tot_mins,
            "rate_source": src,
            "per90_xg": float(round(per90_xg, 4)),
            "per90_xa": float(round(per90_xa, 4)),
            "per90_defcon": float(round(per90_defcon, 4)),
            "per90_saves": float(round(per90_saves, 4)),
            "per90_goals_conceded": float(round(per90_gc, 4)),
            "provenance_note": note,
        })

    out_df = pd.DataFrame(rows)
    Path(output_csv_path).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_csv_path, index=False)
    print(f"Exported {len(out_df)} rows to {output_csv_path}")
    return out_df


if __name__ == "__main__":
    build_expected_stats()
