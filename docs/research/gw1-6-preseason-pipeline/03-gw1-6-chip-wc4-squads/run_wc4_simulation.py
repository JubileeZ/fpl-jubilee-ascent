"""GW1–6 chip exploration matrix (16 scenarios) + user-squad / FT banking.

Matrix axes (grill lock 2026-08-10):
  (BB1 | BB2) × WC4 Opt1 × (FH3 | TC3) × (Allow|Ban Haaland pre) × (Allow|Ban B.Fernandes pre)

Ban scope: pre-chip GW1–3 squad only; FH3 and WC4 may include banned players.
Have = allow MILP (no force-include). TC3 = 3× highest GW3 xP in that scenario's GW3 XI.
Availability overlays via availability_priors (watch 0.70; exclude_gw1-5 → GW1–5 only).
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

MAX_BUDGET = 100.0
HAALAND_WEB = "Haaland"
BRUNO_WEB = "B.Fernandes"

spec = importlib.util.spec_from_file_location(
    "pmod",
    "docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/project_expected_points.py",
)
pmod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pmod)

_PRIOR_SPEC = importlib.util.spec_from_file_location(
    "availability_priors",
    Path("docs/research/gw1-6-preseason-pipeline/availability_priors.py"),
)
_PRIOR_MOD = importlib.util.module_from_spec(_PRIOR_SPEC)
assert _PRIOR_SPEC.loader is not None
_PRIOR_SPEC.loader.exec_module(_PRIOR_MOD)
apply_availability_priors = _PRIOR_MOD.apply_availability_priors


def generate_gw1_6_projections() -> pd.DataFrame:
    df_stats = pd.read_csv(
        "data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv"
    )
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
                "per90_threat": 0.0, "per90_creativity": 0.0, "per90_goals": 0.0, "per90_assists": 0.0,
                "per90_yellow_cards": 0.0, "per90_red_cards": 0.0, "per90_penalties_saved": 0.0,
                "per90_penalties_missed": 0.0, "per90_own_goals": 0.0,
                "is_immediate_next_gw": False, "has_availability_snapshot": False,
                "chance_of_playing": 100.0,
                "rate_source": player.get("rate_source", ""),
                "provenance_note": player.get("provenance_note", ""),
            })

    features = pd.DataFrame(rows)
    preds = ParticipationStateHybridModel().predict(features, horizon=6)
    merged = features.merge(
        preds, on=["player_id", "gameweek_id", "fixture_id"], how="left", suffixes=("", "_pred")
    )
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


def tc3_bonus(starters: pd.DataFrame) -> tuple[str, float]:
    """Return (captain web_name, extra xP beyond the 1× already in XI) for TC (= +2×)."""
    best = starters.sort_values("gw3_xp", ascending=False).iloc[0]
    return str(best["web_name"]), float(best["gw3_xp"]) * 2.0


def compute_banked_fts_gw6(
    *,
    rolls_gw2: bool = True,
    rolls_gw3: bool = True,
    rolls_gw5: bool = True,
) -> int:
    """FPL FT accrual: enter GW2 with 1; unused FT banks (+1/week, cap 5); WC preserves."""
    fts = 1
    for rolled in (rolls_gw2, rolls_gw3):
        if rolled:
            fts = min(5, fts + 1)
        # spent 1 then weekly +1 → unchanged count
    # WC preserves bank
    if rolls_gw5:
        fts = min(5, fts + 1)
    return int(fts)


def filter_bans(ban_haaland: bool, ban_bruno: bool) -> set[str]:
    bans: set[str] = set()
    if ban_haaland:
        bans.add(HAALAND_WEB)
    if ban_bruno:
        bans.add(BRUNO_WEB)
    return bans


def score_fixed_squad(
    squad: pd.DataFrame,
    bb_gw: int | None,
    mid_chip: str,
    fh_squad: pd.DataFrame | None,
) -> dict[int, float]:
    gw_xps: dict[int, float] = {}
    if mid_chip == "FH3":
        assert fh_squad is not None
        for gw in (1, 2):
            _, xp = get_gw_starters(squad, gw, bb_gw=bb_gw)
            gw_xps[gw] = xp
        _, xp3 = get_gw_starters(fh_squad, 3, bb_gw=None)
        gw_xps[3] = xp3
    else:
        for gw in (1, 2, 3):
            starters, xp = get_gw_starters(squad, gw, bb_gw=bb_gw)
            if gw == 3 and mid_chip == "TC3":
                _, bonus = tc3_bonus(starters)
                xp += bonus
            gw_xps[gw] = xp
    return gw_xps


def load_user_squad(df_proj: pd.DataFrame) -> pd.DataFrame:
    picks = pd.read_parquet("data/processed/user_picks.parquet")
    players = pd.read_parquet("data/processed/players.parquet")
    clubs = pd.read_parquet("data/processed/clubs.parquet")
    club_map = dict(zip(clubs["id"], clubs["short_name"], strict=False))
    pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
    rows: list[dict] = []
    missing: list[int] = []
    for _, pick in picks.iterrows():
        pid = int(pick["player_id"])
        hit = df_proj[df_proj["player_id"] == pid]
        if len(hit):
            rows.append(hit.iloc[0].to_dict())
            continue
        missing.append(pid)
        prow = players[players["id"] == pid]
        if prow.empty:
            # Stale pick id not in current players.parquet
            stub = {
                "player_id": pid,
                "web_name": f"unknown_{pid}",
                "club_short": "UNK",
                "position": "MID",
                "expected_role": "Out of Contention",
                "draft_availability": "eligible",
                "cost": float(pick.get("selling_price", pick.get("purchase_price", 45))) / 10.0,
                "per90_defcon": 0.0,
                "per90_xg": 0.0,
                "per90_xa": 0.0,
                "total_6gw_xp": 0.0,
                "gw1_3_xp": 0.0,
                "gw4_6_xp": 0.0,
            }
        else:
            meta = prow.iloc[0]
            stub = {
                "player_id": pid,
                "web_name": meta["web_name"],
                "club_short": club_map.get(int(meta["club_id"]), ""),
                "position": pos_map.get(int(meta["position_id"]), "MID"),
                "expected_role": "Out of Contention",
                "draft_availability": "eligible",
                "cost": float(meta["now_cost"]) / 10.0,
                "per90_defcon": 0.0,
                "per90_xg": 0.0,
                "per90_xa": 0.0,
                "total_6gw_xp": 0.0,
                "gw1_3_xp": 0.0,
                "gw4_6_xp": 0.0,
            }
        for gw in range(1, 7):
            stub[f"gw{gw}_xp"] = 0.0
            stub[f"gw{gw}_xmins"] = 0.0
        rows.append(stub)
    squad = pd.DataFrame(rows)
    if len(squad) != 15:
        raise RuntimeError(f"user_picks resolved to {len(squad)} rows (expected 15)")
    squad.attrs["spend"] = float(squad["cost"].sum())
    squad.attrs["missing_projection_ids"] = missing
    if missing:
        print(f"[warn] user_picks outside XI Contention projections (0 xP stubs): {missing}")
    return squad


def run_full_wc4_study() -> pd.DataFrame:
    df_proj = generate_gw1_6_projections()
    p_csv = Path("data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_projections.csv")
    p_csv.parent.mkdir(parents=True, exist_ok=True)
    df_proj.to_csv(p_csv, index=False)

    wc4_opt1 = solve_squad_advanced(
        df_proj, gw_list=[4, 5, 6], bb_gw=None, max_spend=100.0, min_liv=0
    )
    fh3_squad = solve_squad_advanced(
        df_proj, gw_list=[3], bb_gw=None, max_spend=100.0, min_liv=0
    )

    summary_records: list[dict] = []
    detailed_records: list[dict] = []
    sid = 0

    print("\n==========================================================================")
    print("GW1-6 EXPLORATION MATRIX: BB × WC4 Opt1 × (FH3|TC3) × Haaland × Bruno")
    print("==========================================================================")

    for bb_gw in (1, 2):
        for mid_chip in ("FH3", "TC3"):
            for ban_h in (False, True):
                for ban_b in (False, True):
                    sid += 1
                    bans = filter_bans(ban_h, ban_b)
                    if mid_chip == "FH3":
                        pre = solve_squad_advanced(
                            df_proj, gw_list=[1, 2], bb_gw=bb_gw, max_spend=100.0,
                            min_liv=1, banned_web_names=bans,
                        )
                        fh = fh3_squad
                    else:
                        pre = solve_squad_advanced(
                            df_proj, gw_list=[1, 2, 3], bb_gw=bb_gw, max_spend=100.0,
                            min_liv=1, banned_web_names=bans,
                        )
                        fh = None

                    gw_xps = score_fixed_squad(pre, bb_gw, mid_chip, fh)
                    tc_name = ""
                    if mid_chip == "TC3":
                        starters3, _ = get_gw_starters(pre, 3, bb_gw=bb_gw)
                        tc_name, _ = tc3_bonus(starters3)

                    for gw in (4, 5, 6):
                        _, xp = get_gw_starters(wc4_opt1, gw, bb_gw=None)
                        gw_xps[gw] = xp

                    banked = compute_banked_fts_gw6(
                        rolls_gw2=True, rolls_gw3=True, rolls_gw5=True
                    )
                    name = (
                        f"S{sid}: BB{bb_gw} + {mid_chip} + WC4 Opt1 | "
                        f"H={'ban' if ban_h else 'allow'} | B={'ban' if ban_b else 'allow'}"
                    )
                    summary_records.append({
                        "scenario_id": f"S{sid}",
                        "scenario": name,
                        "bb_chip": f"GW{bb_gw}",
                        "mid_chip": mid_chip,
                        "wc4_option": "Opt1",
                        "ban_haaland_pre": ban_h,
                        "ban_bruno_pre": ban_b,
                        "tc_captain": tc_name,
                        "gw1_xp": round(gw_xps[1], 2),
                        "gw2_xp": round(gw_xps[2], 2),
                        "gw3_xp": round(gw_xps[3], 2),
                        "gw1_3_xp": round(gw_xps[1] + gw_xps[2] + gw_xps[3], 2),
                        "gw4_xp": round(gw_xps[4], 2),
                        "gw5_xp": round(gw_xps[5], 2),
                        "gw6_xp": round(gw_xps[6], 2),
                        "gw4_6_xp": round(gw_xps[4] + gw_xps[5] + gw_xps[6], 2),
                        "total_6gw_xp": round(sum(gw_xps.values()), 2),
                        "pre_spend": pre.attrs["spend"],
                        "post_spend": wc4_opt1.attrs["spend"],
                        "itb_gw6": round(100.0 - wc4_opt1.attrs["spend"], 1),
                        "gw5_transfers": 0,
                        "banked_fts_gw6": banked,
                    })

                    pre_phase = "GW1-2 Pre-FH" if mid_chip == "FH3" else "GW1-3 Pre-WC"
                    for _, r in pre.iterrows():
                        detailed_records.append({
                            "scenario": name, "phase": pre_phase,
                            "player_id": int(r["player_id"]), "web_name": r["web_name"],
                            "club_short": r["club_short"], "position": r["position"],
                            "cost": r["cost"], "expected_role": r["expected_role"],
                            "gw1_xp": r["gw1_xp"], "gw2_xp": r["gw2_xp"],
                            "gw3_xp": 0.0 if mid_chip == "FH3" else r["gw3_xp"],
                            "gw4_xp": 0.0, "gw5_xp": 0.0, "gw6_xp": 0.0,
                        })
                    if fh is not None:
                        for _, r in fh.iterrows():
                            detailed_records.append({
                                "scenario": name, "phase": "GW3 Free-Hit",
                                "player_id": int(r["player_id"]), "web_name": r["web_name"],
                                "club_short": r["club_short"], "position": r["position"],
                                "cost": r["cost"], "expected_role": r["expected_role"],
                                "gw1_xp": 0.0, "gw2_xp": 0.0, "gw3_xp": r["gw3_xp"],
                                "gw4_xp": 0.0, "gw5_xp": 0.0, "gw6_xp": 0.0,
                            })
                    for _, r in wc4_opt1.iterrows():
                        detailed_records.append({
                            "scenario": name, "phase": "GW4-6 Post-WC",
                            "player_id": int(r["player_id"]), "web_name": r["web_name"],
                            "club_short": r["club_short"], "position": r["position"],
                            "cost": r["cost"], "expected_role": r["expected_role"],
                            "gw1_xp": 0.0, "gw2_xp": 0.0, "gw3_xp": 0.0,
                            "gw4_xp": r["gw4_xp"], "gw5_xp": r["gw5_xp"], "gw6_xp": r["gw6_xp"],
                        })

    df_summary = pd.DataFrame(summary_records)
    print("\n--- 16-SCENARIO SUMMARY ---")
    cols = [
        "scenario_id", "bb_chip", "mid_chip", "ban_haaland_pre", "ban_bruno_pre",
        "tc_captain", "gw1_3_xp", "gw4_6_xp", "total_6gw_xp", "banked_fts_gw6",
    ]
    print(df_summary[cols].to_string(index=False))

    fh_best = df_summary[df_summary["mid_chip"] == "FH3"].sort_values(
        "total_6gw_xp", ascending=False
    ).iloc[0]
    tc_best = df_summary[df_summary["mid_chip"] == "TC3"].sort_values(
        "total_6gw_xp", ascending=False
    ).iloc[0]
    print("\n--- DECISION (top FH3 / top TC3) ---")
    print(f"Top FH3: {fh_best['scenario']} → {fh_best['total_6gw_xp']:.2f} xP")
    print(f"Top TC3: {tc_best['scenario']} → {tc_best['total_6gw_xp']:.2f} xP")

    # User squad comparison (reproducible from user_picks.parquet)
    user_rows: list[dict] = []
    try:
        user = load_user_squad(df_proj)
        for bb_gw in (1, 2):
            for mid_chip in ("FH3", "TC3"):
                gw_xps = score_fixed_squad(
                    user, bb_gw, mid_chip, fh3_squad if mid_chip == "FH3" else None
                )
                for gw in (4, 5, 6):
                    _, xp = get_gw_starters(wc4_opt1, gw, bb_gw=None)
                    gw_xps[gw] = xp
                banked = compute_banked_fts_gw6(rolls_gw2=True, rolls_gw3=True, rolls_gw5=True)
                peer = df_summary[
                    (df_summary["bb_chip"] == f"GW{bb_gw}")
                    & (df_summary["mid_chip"] == mid_chip)
                    & (~df_summary["ban_haaland_pre"])
                    & (~df_summary["ban_bruno_pre"])
                ].iloc[0]
                total = sum(gw_xps.values())
                user_rows.append({
                    "path": f"User + BB{bb_gw} + {mid_chip} + WC4 Opt1",
                    "gw1_3_xp": round(gw_xps[1] + gw_xps[2] + gw_xps[3], 2),
                    "gw4_6_xp": round(gw_xps[4] + gw_xps[5] + gw_xps[6], 2),
                    "total_6gw_xp": round(total, 2),
                    "peer_milp_total": float(peer["total_6gw_xp"]),
                    "lag_vs_peer": round(total - float(peer["total_6gw_xp"]), 2),
                    "pre_wc_opp_loss": round(
                        (gw_xps[1] + gw_xps[2] + gw_xps[3]) - float(peer["gw1_3_xp"]), 2
                    ),
                    "banked_fts_gw6": banked,
                    "user_spend": user.attrs["spend"],
                })
        df_user = pd.DataFrame(user_rows)
        print("\n--- USER SQUAD vs ALLOW-ALLOW PEER ---")
        print(df_user.to_string(index=False))
        user_csv = Path(
            "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_user_squad_comparison.csv"
        )
        df_user.to_csv(user_csv, index=False)
        print(f"Exported user comparison to {user_csv}")
    except Exception as exc:  # noqa: BLE001 — research runner should continue
        print(f"\n[warn] user_picks comparison skipped: {exc}")

    sim_csv = Path(
        "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv"
    )
    pd.DataFrame(detailed_records).to_csv(sim_csv, index=False)
    summary_csv = Path(
        "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv"
    )
    df_summary.to_csv(summary_csv, index=False)
    print(f"\nExported detailed simulation to {sim_csv}")
    print(f"Exported summary to {summary_csv}")
    return df_summary


if __name__ == "__main__":
    run_full_wc4_study()
