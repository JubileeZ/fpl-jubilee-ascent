"""GW1–5 Expected Points Projection Engine.

Integrates per-90 rates from data/research/expected-stats-gw1-5.csv with
fixture difficulty (FDR) and availability overrides from expected-role-gw1-5.csv,
using the ParticipationStateHybridModel scoring logic.
"""

import math
from pathlib import Path
import sys

sys.path.insert(0, ".")

import pandas as pd

from models.scoring_matrix import event_points, Position

_POS_MAP = {"GKP": "GK", "DEF": "D", "MID": "M", "FWD": "F"}


def _poisson_pmf(k: int, lmbda: float) -> float:
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    return (lmbda**k) * math.exp(-lmbda) / math.factorial(k)


def _negbin_pmf(k: int, lmbda: float, r: float = 3.0) -> float:
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    p = r / (r + lmbda)
    coeff = 1.0
    for j in range(k):
        coeff *= (j + r) / (j + 1)
    return coeff * (p**r) * ((1.0 - p)**k)


def _negbin_cdf_complement(threshold: int, lmbda: float, r: float = 7.5) -> float:
    if lmbda <= 0:
        return 0.0
    cdf = sum(_negbin_pmf(k, lmbda, r) for k in range(threshold))
    return min(max(1.0 - cdf, 0.0), 1.0)


def _expected_negbin_conceded_penalty(lmbda: float, r: float = 3.0) -> float:
    if lmbda <= 0:
        return 0.0
    max_k = max(30, int(math.ceil(lmbda + 10.0 * math.sqrt(lmbda + 1.0))))
    return sum(math.floor(k / 2) * _negbin_pmf(k, lmbda, r) for k in range(max_k + 1))


def project_gw1_5_points(
    stats_csv_path: str = "data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv",
    fixtures_parquet_path: str = "data/processed/fixtures.parquet",
    clubs_parquet_path: str = "data/processed/clubs.parquet",
    output_csv_path: str = "data/research/expected-stats-gw1-5/gw1-5_projections.csv",
) -> pd.DataFrame:
    df_stats = pd.read_csv(stats_csv_path)
    df_fixtures = pd.read_parquet(fixtures_parquet_path)
    df_clubs = pd.read_parquet(clubs_parquet_path)

    # Club short code to club_id map
    club_short_to_id = dict(zip(df_clubs["short_name"], df_clubs["id"], strict=False))

    results = []

    for _, row in df_stats.iterrows():
        pid = int(row["player_id"])
        web_name = row["web_name"]
        club_short = row["club_short"]
        pos_str = row["position"]
        pos: Position = _POS_MAP.get(pos_str, "M")
        role = row["expected_role"]
        draft_avail = str(row.get("draft_availability", "eligible"))
        avail_override = str(row.get("availability_override", ""))

        club_id = club_short_to_id.get(club_short)

        p_start_base = float(row.get("p_start", 0.90 if role == "Nailed Starter" else 0.75))
        p_sub_base = float(row.get("p_sub_in", 0.05 if role == "Nailed Starter" else 0.10))
        p_dnp_base = float(row.get("p_dnp", 0.05 if role == "Nailed Starter" else 0.15))

        xmins_start = float(row.get("xmins_if_start", 85.0 if role == "Nailed Starter" else 80.0))
        xmins_sub = float(row.get("xmins_if_sub_in", 20.0))

        per90_xg = float(row.get("per90_xg", 0.0))
        per90_xa = float(row.get("per90_xa", 0.0))
        per90_defcon = float(row.get("per90_defcon", 0.0))
        per90_saves = float(row.get("per90_saves", 0.0))
        per90_gc = float(row.get("per90_goals_conceded", 1.30))

        gw_points = {}
        gw_minutes = {}

        total_5gw_xp = 0.0
        total_5gw_xmins = 0.0

        for gw in range(1, 6):
            # Check availability exclusions
            is_excluded_gw5 = (draft_avail == "exclude_gw1-5") or ("out_gw1-5" in avail_override)
            is_excluded_gw1 = (draft_avail == "exclude_gw1") or ("unavailable_gw1" in avail_override)

            if is_excluded_gw5 or (is_excluded_gw1 and gw == 1):
                p_start, p_sub, p_dnp = 0.0, 0.0, 1.0
            else:
                p_start, p_sub, p_dnp = p_start_base, p_sub_base, p_dnp_base

            # Find fixture for this club in this GW
            gw_fix = df_fixtures[(df_fixtures["gameweek_id"] == gw) & ((df_fixtures["home_club_id"] == club_id) | (df_fixtures["away_club_id"] == club_id))]

            if len(gw_fix) == 0 or p_dnp >= 1.0:
                gw_points[f"gw{gw}_xp"] = 0.0
                gw_minutes[f"gw{gw}_xmins"] = 0.0
                continue

            fix_row = gw_fix.iloc[0]
            is_home = (fix_row["home_club_id"] == club_id)
            fdr = float(fix_row["team_h_difficulty"] if is_home else fix_row["team_a_difficulty"])
            fdr_mult = max(0.2, (6.0 - fdr) / 3.0)

            # State mins & p60
            mins_start = xmins_start
            mins_sub = xmins_sub

            p60_start = min(1.0, max(0.0, (mins_start - 45.0) / 30.0))
            p60_sub = min(1.0, max(0.0, (mins_sub - 45.0) / 30.0))

            expected_mins = p_start * mins_start + p_sub * mins_sub

            # Minute points
            xp_mins = p_start * (1.0 + p60_start) + p_sub * (1.0 + p60_sub)

            # Attack (xG, xA)
            exp_xg_start = per90_xg * (mins_start / 90.0) * fdr_mult
            exp_xg_sub = per90_xg * (mins_sub / 90.0) * fdr_mult
            exp_xg = p_start * exp_xg_start + p_sub * exp_xg_sub
            xp_goals = event_points("goals", pos, exp_xg)

            exp_xa_start = per90_xa * (mins_start / 90.0) * fdr_mult
            exp_xa_sub = per90_xa * (mins_sub / 90.0) * fdr_mult
            exp_xa = p_start * exp_xa_start + p_sub * exp_xa_sub
            xp_assists = event_points("assists", pos, exp_xa)

            # Clean sheet
            lmbda_pitch_start = max(0.05, per90_gc * fdr_mult) * mins_start / 90.0
            lmbda_pitch_sub = max(0.05, per90_gc * fdr_mult) * mins_sub / 90.0

            pcs_start = math.exp(-lmbda_pitch_start) * p60_start
            pcs_sub = math.exp(-lmbda_pitch_sub) * p60_sub
            pcs = p_start * pcs_start + p_sub * pcs_sub
            xp_cs = event_points("clean_sheets", pos, pcs)

            # Conceded penalty
            lmbda_conceded_start = max(0.05, per90_gc * fdr_mult) * mins_start / 90.0
            lmbda_conceded_sub = max(0.05, per90_gc * fdr_mult) * mins_sub / 90.0

            pen_start = _expected_negbin_conceded_penalty(lmbda_conceded_start) if pos in ("GK", "D") else 0.0
            pen_sub = _expected_negbin_conceded_penalty(lmbda_conceded_sub) if pos in ("GK", "D") else 0.0
            xp_conceded = -(p_start * pen_start + p_sub * pen_sub)

            # Defensive contribution (xDEFcon)
            lmbda_def_start = per90_defcon * mins_start / 90.0
            lmbda_def_sub = per90_defcon * mins_sub / 90.0

            thresh = 10 if pos == "D" else 12
            r_val = 8.5 if pos == "D" else 7.0

            pdef_start = _negbin_cdf_complement(thresh, lmbda_def_start, r=r_val) if pos != "GK" else 0.0
            pdef_sub = _negbin_cdf_complement(thresh, lmbda_def_sub, r=r_val) if pos != "GK" else 0.0
            pdef = p_start * pdef_start + p_sub * pdef_sub
            xp_defcon = event_points("defensive_contributions", pos, pdef)

            # Saves (GKP)
            exp_saves_start = per90_saves * mins_start / 90.0 if pos == "GK" else 0.0
            exp_saves_sub = per90_saves * mins_sub / 90.0 if pos == "GK" else 0.0
            xp_saves_start = math.floor(exp_saves_start / 3.0)
            xp_saves_sub = math.floor(exp_saves_sub / 3.0)
            xp_saves = p_start * xp_saves_start + p_sub * xp_saves_sub

            # Bonus heuristic (~0.25 pt baseline for starters)
            xp_bonus = p_start * 0.25 + p_sub * 0.05

            # Sum total xP for this GW
            gw_xp = xp_mins + xp_goals + xp_assists + xp_cs + xp_conceded + xp_defcon + xp_saves + xp_bonus

            gw_points[f"gw{gw}_xp"] = round(gw_xp, 2)
            gw_minutes[f"gw{gw}_xmins"] = round(expected_mins, 1)

            total_5gw_xp += gw_xp
            total_5gw_xmins += expected_mins

        row_res = {
            "player_id": pid,
            "web_name": web_name,
            "club_short": club_short,
            "position": pos_str,
            "expected_role": role,
            "draft_availability": row.get("draft_availability", "eligible"),
            "total_5gw_xp": round(total_5gw_xp, 2),
            "avg_gw_xp": round(total_5gw_xp / 5.0, 2),
            "total_5gw_xmins": round(total_5gw_xmins, 1),
            **gw_points,
            **gw_minutes,
            "rate_source": row.get("rate_source", ""),
            "provenance_note": row.get("provenance_note", ""),
        }
        results.append(row_res)

    out_df = pd.DataFrame(results).sort_values("total_5gw_xp", ascending=False)
    Path(output_csv_path).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_csv_path, index=False)
    print(f"Exported GW1-5 projections ({len(out_df)} players) to {output_csv_path}")
    return out_df


if __name__ == "__main__":
    project_gw1_5_points()
