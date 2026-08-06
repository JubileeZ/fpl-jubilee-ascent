"""Expected Stats GW1–5 builder — Permanent Player Code Mapping + usable-season blend.

Rules (grill lock):
- Resolve archive history via FPL `code` (ADR 0004), never raw cross-season player_id.
- Season window 2023/24–2025/26. Usable season = minutes >= MIN_USABLE_MINUTES (450).
- Thin/missing seasons dropped. Blend: 50% latest usable + 50% mean of older usable.
- External research only when no usable FPL season remains; Defcon only if CBIT/CBITR
  or true FPL Defcon (else position baseline Defcon).
- Rate sheet covers XI Contention Set (Nailed / Regular / Rotation / Cameo).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

import pandas as pd

from features.builder import MIN_PRIOR_MINUTES

MIN_USABLE_MINUTES = MIN_PRIOR_MINUTES  # 450 — same floor as Prior-Season Seed
SEASON_WINDOW = ("2023/24", "2024/25", "2025/26")
LATEST_ARCHIVE_SEASON = "2025/26"
XI_CONTENTION_ROLES = ("Nailed Starter", "Regular Starter", "Rotation", "Cameo")

POSITION_BASELINES = {
    "GKP": {"xg": 0.00, "xa": 0.00, "defcon": 0.00, "saves": 2.78, "gc": 1.38},
    "DEF": {"xg": 0.06, "xa": 0.06, "defcon": 4.25, "saves": 0.00, "gc": 1.39},
    "MID": {"xg": 0.15, "xa": 0.15, "defcon": 3.10, "saves": 0.00, "gc": 1.37},
    "FWD": {"xg": 0.41, "xa": 0.13, "defcon": 1.50, "saves": 0.00, "gc": 1.41},
}

# External packages: xG/xA/saves/gc from research.
# Defcon: use researched CBIT/CBITR when defcon_cbit=True (includes best-guess partial sources).
# If defcon_cbit=False → position baseline Defcon.
EXTERNAL_RESEARCH_RATES: dict[int, dict] = {
    25: {"xg": 0.770, "xa": 0.240, "saves": 0.00, "gc": 1.10, "defcon": 1.22, "defcon_cbit": False,
         "note": "External 3-season: Sporting CP / Arsenal (xG/xA); Defcon baseline (no CBIT)"},
    217: {"xg": 0.340, "xa": 0.350, "saves": 0.00, "gc": 1.20, "defcon": 2.28, "defcon_cbit": False,
          "note": "External 3-season: Leverkusen / Liverpool (xG/xA); Defcon baseline"},
    357: {"xg": 0.200, "xa": 0.250, "saves": 0.00, "gc": 1.25, "defcon": 2.81, "defcon_cbit": False,
          "note": "External 3-season: Leverkusen / Liverpool DEF; Defcon baseline"},
    211: {"xg": 0.240, "xa": 0.200, "saves": 0.00, "gc": 1.30, "defcon": 2.55, "defcon_cbit": False,
          "note": "External 3-season: Villarreal / Palace; Defcon baseline"},
    514: {"xg": 0.370, "xa": 0.170, "saves": 0.00, "gc": 1.30, "defcon": 2.40, "defcon_cbit": False,
          "note": "External 3-season: Bayern / Spurs; Defcon baseline"},
    335: {"xg": 0.090, "xa": 0.140, "saves": 0.00, "gc": 1.35, "defcon": 5.71, "defcon_cbit": False,
          "note": "External 3-season: Hoffenheim / Leeds; Defcon baseline"},
    336: {"xg": 0.330, "xa": 0.110, "saves": 0.00, "gc": 1.35, "defcon": 1.40, "defcon_cbit": False,
          "note": "External 3-season: Milan / Leeds; Defcon baseline"},
    331: {"xg": 0.040, "xa": 0.050, "saves": 0.00, "gc": 1.30, "defcon": 6.15, "defcon_cbit": False,
          "note": "External 3-season: Lille / Leeds; Defcon baseline"},
    445: {"xg": 0.110, "xa": 0.020, "saves": 0.00, "gc": 1.15, "defcon": 8.78, "defcon_cbit": False,
          "note": "External 3-season: Milan / Newcastle; Defcon baseline"},
    412: {"xg": 0.000, "xa": 0.000, "saves": 3.47, "gc": 1.15, "defcon": 0.00, "defcon_cbit": True,
          "note": "External 3-season: Antwerp / Man Utd GKP saves"},
    533: {"xg": 0.090, "xa": 0.080, "saves": 0.00, "gc": 1.25, "defcon": 8.42, "defcon_cbit": False,
          "note": "External 3-season: PSG / Leverkusen / Sunderland; Defcon baseline"},
    535: {"xg": 0.060, "xa": 0.020, "saves": 0.00, "gc": 1.25, "defcon": 9.82, "defcon_cbit": False,
          "note": "External 3-season: Getafe / Sunderland; Defcon baseline"},
    536: {"xg": 0.040, "xa": 0.020, "saves": 0.00, "gc": 1.25, "defcon": 7.24, "defcon_cbit": False,
          "note": "External 3-season: Atletico / Sunderland; Defcon baseline"},
    542: {"xg": 0.140, "xa": 0.200, "saves": 0.00, "gc": 1.30, "defcon": 5.31, "defcon_cbit": False,
          "note": "External 3-season: Rennes / Roma / Sunderland; Defcon baseline"},
    545: {"xg": 0.070, "xa": 0.080, "saves": 0.00, "gc": 1.30, "defcon": 6.25, "defcon_cbit": False,
          "note": "External 3-season: Union SG / Sunderland; Defcon baseline"},
    529: {"xg": 0.000, "xa": 0.000, "saves": 3.27, "gc": 1.31, "defcon": 0.00, "defcon_cbit": True,
          "note": "External 3-season: NEC / Sunderland GKP saves"},
    504: {"xg": 0.185, "xa": 0.035, "saves": 0.00, "gc": 1.46, "defcon": 12.45, "defcon_cbit": True,
          "note": "External Westerlo/HSV xG/xA; best-guess CBIT 12.45/90 from HSV Opta (blocks may be shots-only)"},
    172: {"xg": 0.000, "xa": 0.000, "saves": 2.25, "gc": 1.07, "defcon": 0.00, "defcon_cbit": True,
          "note": "External: Coventry GKP saves"},
    # Draft fallback packages (research 2026-08-02)
    173: {"xg": 0.091, "xa": 0.043, "saves": 0.00, "gc": 1.204, "defcon": 9.102, "defcon_cbit": True,
          "note": "External CHA 2023-26: Bobby Thomas Coventry CB; CBIT Defcon; FBref+FotMob; mins~10017"},
    193: {"xg": 0.570, "xa": 0.110, "saves": 0.00, "gc": 1.238, "defcon": 5.279, "defcon_cbit": True,
          "note": "External CHA 2023-26: Haji Wright; best-guess CBITR 5.28/90 from 23/24-24/25 FBref"},
    274: {"xg": 0.000, "xa": 0.000, "saves": 2.333, "gc": 1.010, "defcon": 0.00, "defcon_cbit": True,
          "note": "External SPFL 2023-26: Jack Butland Rangers proxy (no Hull mins yet); mins~9180"},
    290: {"xg": 0.081, "xa": 0.062, "saves": 0.00, "gc": 1.294, "defcon": 9.096, "defcon_cbit": True,
          "note": "External CHA 2023-26: Regan Slater Hull; CBITR Defcon; FBref+FotMob; mins~8905"},
    292: {"xg": 0.043, "xa": 0.031, "saves": 0.00, "gc": 1.28, "defcon": 8.32, "defcon_cbit": True,
          "note": "External 2023-26: Abdülkadir Ömür; best-guess CBITR 8.32/90 from Hull CHA FBref"},
    310: {"xg": 0.024, "xa": 0.032, "saves": 0.00, "gc": 1.47, "defcon": 13.57, "defcon_cbit": True,
          "note": "External 2023-26: Azor Matusiwa; best-guess CBITR 13.57/90 from Ligue 1 FBref"},
    316: {"xg": 0.236, "xa": 0.028, "saves": 0.00, "gc": 1.38, "defcon": 2.78, "defcon_cbit": True,
          "note": "External 2024-26: Emersonn; best-guess partial def actions 2.78/90 (Tkl+Int+Rec)"},
    # CBIT/CBITR Defcon upgrades (research 2026-08-02)
    182: {"xg": 0.035, "xa": 0.015, "saves": 0.00, "gc": 1.30, "defcon": 8.03, "defcon_cbit": True,
          "note": "External YB/Frankfurt xG/xA; best-guess CBIT 8.03/90 from UCL scout sample"},
    175: {"xg": 0.035, "xa": 0.150, "saves": 0.00, "gc": 1.00, "defcon": 7.00, "defcon_cbit": True,
          "note": "External Coventry DEF; FBref CBIT Defcon 7.00/90 (2023-25)"},
    188: {"xg": 0.185, "xa": 0.205, "saves": 0.00, "gc": 1.35, "defcon": 11.05, "defcon_cbit": True,
          "note": "External Coventry MID; FBref CBITR Defcon 11.05/90 (2023-25)"},
    186: {"xg": 0.255, "xa": 0.155, "saves": 0.00, "gc": 1.35, "defcon": 6.52, "defcon_cbit": True,
          "note": "External Coventry MID; FBref CBITR 6.52/90 Coventry slice only"},
    184: {"xg": 0.045, "xa": 0.205, "saves": 0.00, "gc": 1.25, "defcon": 10.80, "defcon_cbit": True,
          "note": "External Swansea/Coventry; FBref CBITR Defcon 10.80/90"},
    247: {"xg": 0.105, "xa": 0.175, "saves": 0.00, "gc": 1.40, "defcon": 12.03, "defcon_cbit": True,
          "note": "External Middlesbrough; FBref CBITR Defcon 12.03/90 (Hackney)"},
    278: {"xg": 0.075, "xa": 0.055, "saves": 0.00, "gc": 1.16, "defcon": 8.14, "defcon_cbit": True,
          "note": "External Preston; FBref CBIT Defcon 8.14/90 (Andrew Hughes)"},
    280: {"xg": 0.030, "xa": 0.125, "saves": 0.00, "gc": 1.24, "defcon": 7.36, "defcon_cbit": True,
          "note": "External Hull DEF; FBref CBIT Defcon 7.36/90 (Coyle)"},
    286: {"xg": 0.195, "xa": 0.215, "saves": 0.00, "gc": 1.50, "defcon": 9.97, "defcon_cbit": True,
          "note": "External Farense/Hull; FBref CBITR Defcon 9.97/90 (Belloumi)"},
    562: {"xg": 0.455, "xa": 0.175, "saves": 0.00, "gc": 1.20, "defcon": 7.69, "defcon_cbit": True,
          "note": "External Celtic xG/xA; best-guess CBITR 7.69/90 (SPFL incomplete; scout+FootyMetrics)"},
    334: {"xg": 0.070, "xa": 0.110, "saves": 0.00, "gc": 1.10, "defcon": 10.23, "defcon_cbit": True,
          "note": "External Sassuolo; FBref CBIT Defcon 10.23/90 (Muharemović)"},
    362: {"xg": 0.045, "xa": 0.085, "saves": 0.00, "gc": 1.24, "defcon": 10.87, "defcon_cbit": True,
          "note": "External Rennes/Clermont; FBref CBIT Defcon 10.87/90 (Jacquet)"},
    558: {"xg": 0.085, "xa": 0.100, "saves": 0.00, "gc": 1.20, "defcon": 12.30, "defcon_cbit": True,
          "note": "External RB Leipzig; FBref CBITR Defcon 12.30/90 (Schlager)"},
}


def _per90(events: float, minutes: float) -> float:
    return (events / minutes * 90.0) if minutes > 0 else 0.0


def _rates_from_sums(
    minutes: float,
    xg: float,
    xa: float,
    defcon: float,
    saves: float,
    gc: float,
) -> dict[str, float] | None:
    if minutes < MIN_USABLE_MINUTES:
        return None
    return {
        "minutes": minutes,
        "xg": _per90(xg, minutes),
        "xa": _per90(xa, minutes),
        "defcon": _per90(defcon, minutes),
        "saves": _per90(saves, minutes),
        "gc": _per90(gc, minutes),
    }


def _archive_season_rates(
    archive_perf: pd.DataFrame,
    archive_pid: int | None,
) -> dict[str, float] | None:
    if archive_pid is None:
        return None
    hist = archive_perf[archive_perf["player_id"] == archive_pid]
    if hist.empty:
        return None
    minutes = float(pd.to_numeric(hist["minutes"], errors="coerce").fillna(0).sum())
    xg = float(pd.to_numeric(hist["expected_goals"], errors="coerce").fillna(0).sum())
    xa = float(pd.to_numeric(hist["expected_assists"], errors="coerce").fillna(0).sum())
    defcon = float(pd.to_numeric(hist["defensive_contribution"], errors="coerce").fillna(0).sum())
    saves = float(pd.to_numeric(hist["saves"], errors="coerce").fillna(0).sum())
    gc = float(pd.to_numeric(hist["goals_conceded"], errors="coerce").fillna(0).sum())
    return _rates_from_sums(minutes, xg, xa, defcon, saves, gc)


def _history_past_season_rates(summary_path: Path, season: str) -> dict[str, float] | None:
    if not summary_path.exists():
        return None
    try:
        with open(summary_path) as f:
            es = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    for hp in es.get("history_past", []):
        if hp.get("season_name") != season:
            continue
        minutes = float(hp.get("minutes", 0) or 0)
        # Prefer FPL Defcon field; else CBIT(+R) component sum when present.
        defcon = float(hp.get("defensive_contribution", 0) or 0)
        if defcon <= 0:
            cbi = float(hp.get("clearances_blocks_interceptions", 0) or 0)
            tackles = float(hp.get("tackles", 0) or 0)
            recoveries = float(hp.get("recoveries", 0) or 0)
            defcon = cbi + tackles + recoveries
        return _rates_from_sums(
            minutes,
            float(hp.get("expected_goals", 0) or 0),
            float(hp.get("expected_assists", 0) or 0),
            defcon,
            float(hp.get("saves", 0) or 0),
            float(hp.get("goals_conceded", 0) or 0),
        )
    return None


def _blend_usable(usable: list[tuple[str, dict[str, float]]]) -> tuple[dict[str, float], str, str]:
    """Recency 50/50: latest usable + mean of older usable. No double-count."""
    keys = ("xg", "xa", "defcon", "saves", "gc")
    if not usable:
        raise ValueError("usable empty")
    usable_sorted = sorted(usable, key=lambda x: SEASON_WINDOW.index(x[0]))
    latest_season, latest = usable_sorted[-1]
    older = usable_sorted[:-1]
    if not older:
        rates = {k: latest[k] for k in keys}
        note = f"100% usable season {latest_season} ({latest['minutes']:.0f} mins)"
        return rates, "fpl_single_usable_season", note
    older_avg = {k: sum(s[k] for _, s in older) / len(older) for k in keys}
    rates = {k: 0.5 * latest[k] + 0.5 * older_avg[k] for k in keys}
    older_names = ",".join(s for s, _ in older)
    note = (
        f"50% {latest_season} ({latest['minutes']:.0f}m) + "
        f"50% mean older usable [{older_names}]"
    )
    return rates, "fpl_recency_50_50", note


def _default_priors(role: str) -> tuple[float, float, float, float, float]:
    if role == "Nailed Starter":
        return 0.90, 0.05, 0.05, 85.0, 20.0
    if role == "Regular Starter":
        return 0.75, 0.10, 0.15, 80.0, 20.0
    if role == "Rotation":
        return 0.45, 0.25, 0.30, 70.0, 20.0
    return 0.15, 0.35, 0.50, 45.0, 15.0  # Cameo


def build_expected_stats(
    role_csv_path: str = "data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv",
    archive_processed: str = "data/archive/2025-26/processed",
    players_parquet: str = "data/processed/players.parquet",
    output_csv_path: str = "data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv",
) -> pd.DataFrame:
    df_role = pd.read_csv(role_csv_path)
    shortlist = df_role[df_role["expected_role"].isin(XI_CONTENTION_ROLES)].copy()

    archive_dir = Path(archive_processed)
    df_arch_players = pd.read_parquet(archive_dir / "players.parquet")
    df_arch_perf = pd.read_parquet(archive_dir / "player_performances.parquet")
    df_curr = pd.read_parquet(players_parquet)

    code_to_archive_id = (
        df_arch_players.set_index("code")["id"].to_dict()
        if "code" in df_arch_players.columns
        else {}
    )
    curr_code = df_curr.set_index("id")["code"].to_dict() if "code" in df_curr.columns else {}

    rows = []
    needs_research: list[str] = []

    for _, srow in shortlist.iterrows():
        pid = int(srow["player_id"])
        pos = str(srow["position"])
        role = str(srow["expected_role"])
        code = curr_code.get(pid)
        archive_pid = code_to_archive_id.get(code) if code is not None else None

        usable: list[tuple[str, dict[str, float]]] = []
        for season in SEASON_WINDOW:
            if season == LATEST_ARCHIVE_SEASON:
                rates = _archive_season_rates(df_arch_perf, archive_pid)
                if rates is None:
                    rates = _history_past_season_rates(
                        Path(f"data/raw/element_summary_{pid}.json"), season
                    )
            else:
                rates = _history_past_season_rates(
                    Path(f"data/raw/element_summary_{pid}.json"), season
                )
            if rates is not None:
                usable.append((season, rates))

        base = POSITION_BASELINES.get(pos, POSITION_BASELINES["MID"])
        if usable:
            blended, src, note = _blend_usable(usable)
            per90_xg = blended["xg"]
            per90_xa = blended["xa"]
            per90_defcon = blended["defcon"]
            per90_saves = blended["saves"]
            per90_gc = blended["gc"]
            usable_mins = sum(r["minutes"] for _, r in usable)
        elif pid in EXTERNAL_RESEARCH_RATES:
            ext = EXTERNAL_RESEARCH_RATES[pid]
            per90_xg = float(ext["xg"])
            per90_xa = float(ext["xa"])
            per90_saves = float(ext["saves"])
            per90_gc = float(ext["gc"])
            if ext.get("defcon_cbit"):
                per90_defcon = float(ext["defcon"])
            else:
                per90_defcon = float(base["defcon"])
            src = "external_3season_research"
            note = str(ext["note"])
            usable_mins = 0.0
        else:
            per90_xg = float(base["xg"])
            per90_xa = float(base["xa"])
            per90_defcon = float(base["defcon"])
            per90_saves = float(base["saves"])
            per90_gc = float(base["gc"])
            src = "fallback_baseline"
            note = f"Position baseline ({pos}); no usable FPL season and no external package"
            usable_mins = 0.0
            needs_research.append(f"{srow['web_name']} ({pid}, {pos}, {srow['club_short']})")

        p_start, p_sub, p_dnp, xmins_s, xmins_u = _default_priors(role)
        p_start = float(srow.get("p_start", p_start))
        p_sub = float(srow.get("p_sub_in", p_sub))
        p_dnp = float(srow.get("p_dnp", p_dnp))
        xmins_s = float(srow.get("mins_if_start", xmins_s))
        xmins_u = float(srow.get("mins_if_sub", xmins_u))

        rows.append({
            "player_id": pid,
            "player_code": int(code) if code is not None and not pd.isna(code) else None,
            "web_name": srow["web_name"],
            "club_short": srow["club_short"],
            "position": pos,
            "expected_role": role,
            "p_start": p_start,
            "p_sub_in": p_sub,
            "p_dnp": p_dnp,
            "xmins_if_start": xmins_s,
            "xmins_if_sub_in": xmins_u,
            "draft_availability": srow.get("draft_availability", "eligible"),
            "availability_override": srow.get("availability_override", ""),
            "usable_season_count": len(usable),
            "usable_mins_total": round(usable_mins, 1),
            "rate_source": src,
            "per90_xg": round(per90_xg, 4),
            "per90_xa": round(per90_xa, 4),
            "per90_defcon": round(per90_defcon, 4),
            "per90_defensive_contribution": round(per90_defcon, 4),
            "per90_saves": round(per90_saves, 4),
            "per90_goals_conceded": round(per90_gc, 4),
            "provenance_note": note,
        })

    out_df = pd.DataFrame(rows)
    Path(output_csv_path).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_csv_path, index=False)
    print(f"Exported {len(out_df)} XI Contention rows to {output_csv_path}")
    print("rate_source counts:\n", out_df["rate_source"].value_counts().to_string())
    if needs_research:
        print(f"\nNeeds external research package ({len(needs_research)}):")
        for line in needs_research[:30]:
            print(f"  - {line}")
        if len(needs_research) > 30:
            print(f"  ... +{len(needs_research) - 30} more")
    return out_df


if __name__ == "__main__":
    build_expected_stats()
