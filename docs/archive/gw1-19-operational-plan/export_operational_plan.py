"""Export Operational First-Half Plan CSVs: frozen 15s, no greedy FTs."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FH_DIR = ROOT / "docs/archive/gw1-19-first-half-chip-path"
OUT_DIR = ROOT / "docs/archive/gw1-19-operational-plan"
CHIP_PY = ROOT / "docs/archive/gw1-19-first-half-chip-path/run_chip_path.py"
POS_ORDER = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}

_SPEC = importlib.util.spec_from_file_location("dv_chips_xi", CHIP_PY)
CHIPS_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(CHIPS_MOD)
CHIP_BY_GW = {1: "BB", 4: "WC", 12: "FH", 17: "TC"}


def _ids(df: pd.DataFrame) -> list[int]:
    return [int(x) for x in df["player_id"].tolist()]


def export() -> dict[str, Path]:
    pool = pd.read_csv(FH_DIR / "gw1-19_projections.csv")
    squads_src = pd.read_csv(FH_DIR / "first_half_squads.csv")
    wc4 = squads_src[squads_src["wc"] == 4]
    pre = wc4[wc4["phase"] == "pre-WC"].copy()
    post = wc4[wc4["phase"] == "WC rebuild"].copy()
    fh = wc4[wc4["phase"] == "FH"].copy()
    pre_ids = _ids(pre)
    post_ids = _ids(post)
    fh_ids = _ids(fh)
    if len(pre_ids) != 15 or len(post_ids) != 15 or len(fh_ids) != 15:
        raise RuntimeError("expected three 15-player WC4 phases")

    owned = pd.concat(
        [
            pre.assign(plan_phase="pre-WC", owned=True, snapshot="live"),
            post.assign(plan_phase="WC rebuild", owned=True, snapshot="live"),
            fh.assign(plan_phase="FH snapshot", owned=False, snapshot="rebuild_at_deadline"),
        ],
        ignore_index=True,
    )
    owned = owned[
        [
            "plan_phase",
            "owned",
            "snapshot",
            "player_id",
            "web_name",
            "club_short",
            "position",
            "cost",
            "expected_role",
        ]
    ]

    xi_rows: list[dict[str, object]] = []
    week_rows: list[dict[str, object]] = []
    for gw in range(1, 20):
        ids = fh_ids if gw == 12 else (pre_ids if gw < 4 else post_ids)
        squad = pool[pool["player_id"].isin(ids)].copy()
        if len(squad) != 15:
            raise RuntimeError(f"GW{gw} squad size {len(squad)}")
        bb = gw == 1
        tc = gw == 17
        xp, cap, starters = CHIPS_MOD.score_week(squad, gw, bb=bb, tc=tc)
        starters = starters.copy()
        starters["_pos"] = starters["position"].map(POS_ORDER)
        col = CHIPS_MOD.xp_col(gw)
        starters = starters.sort_values(["_pos", col], ascending=[True, False])
        held = set(int(x) for x in starters["player_id"])
        bench = squad[~squad["player_id"].isin(held)].sort_values(["position", "web_name"])
        n_def = int((starters["position"] == "DEF").sum())
        n_mid = int((starters["position"] == "MID").sum())
        n_fwd = int((starters["position"] == "FWD").sum())
        formation = "BB-15" if bb else f"{n_def}-{n_mid}-{n_fwd}"
        chip = CHIP_BY_GW.get(gw, "")
        phase = "fh-snapshot" if gw == 12 else ("pre-WC" if gw < 4 else "WC rebuild")
        xi_xp = float(starters[col].sum())
        bench_names = ", ".join(bench["web_name"].tolist())
        week_rows.append(
            {
                "gw": gw,
                "chip": chip,
                "formation": formation,
                "captain": cap,
                "week_xp": round(float(xp), 2),
                "xi_xp": round(xi_xp, 2),
                "plan_phase": phase,
                "fh_15_status": "rebuild_at_deadline" if gw == 12 else "owned",
                "bench": bench_names,
            }
        )
        for _, r in starters.iterrows():
            xi_rows.append(
                {
                    "gw": gw,
                    "chip": chip,
                    "formation": formation,
                    "captain": cap,
                    "player_id": int(r["player_id"]),
                    "web_name": r["web_name"],
                    "club_short": r["club_short"],
                    "position": r["position"],
                    "cost": float(r["cost"]),
                    "xp": round(float(r[col]), 2),
                    "is_captain": r["web_name"] == cap,
                    "xi_xp": round(xi_xp, 2),
                    "week_xp": round(float(xp), 2),
                    "plan_phase": phase,
                    "bench": bench_names,
                }
            )

    weeks = pd.DataFrame(week_rows)
    select11 = pd.DataFrame(xi_rows)
    total = round(float(weeks["week_xp"].sum()), 2)
    summary = pd.DataFrame(
        [
            {
                "plan_id": "OP1",
                "bb": 1,
                "wc": 4,
                "fh": 12,
                "tc": 17,
                "frozen_19gw_xi_xp": total,
                "score_world": "prior_season_dual_vector_seed",
                "ft_engine": "bank_state_hurdle",
                "fh_15_status": "rebuild_at_deadline",
                "follows_greedy_ft_csv": False,
                "pre_spend": round(float(pre["cost"].sum()), 1),
                "wc_spend": round(float(post["cost"].sum()), 1),
            }
        ]
    )
    hurdles = pd.DataFrame(
        [
            {"fts_at_deadline": 5, "nth_at_five": 1, "hurdle_xp": 0.2, "rule": "use-or-lose first FT at cap"},
            {"fts_at_deadline": 5, "nth_at_five": 2, "hurdle_xp": "", "rule": "use hurdle for bank after spend"},
            {"fts_at_deadline": 4, "nth_at_five": "", "hurdle_xp": 1.0, "rule": "not yet wasting incoming FT"},
            {"fts_at_deadline": 3, "nth_at_five": "", "hurdle_xp": 1.5, "rule": "holding premium"},
            {"fts_at_deadline": 2, "nth_at_five": "", "hurdle_xp": 2.5, "rule": "or flagged DNP"},
            {"fts_at_deadline": 1, "nth_at_five": "", "hurdle_xp": 2.5, "rule": "or flagged DNP"},
            {"fts_at_deadline": 0, "nth_at_five": "", "hurdle_xp": 4.0, "rule": "hit_cost or flagged DNP"},
        ]
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "squads": OUT_DIR / "operational_squads.csv",
        "select_11": OUT_DIR / "operational_select_11.csv",
        "weeks": OUT_DIR / "operational_weeks.csv",
        "hurdles": OUT_DIR / "operational_ft_hurdles.csv",
        "summary": OUT_DIR / "operational_summary.csv",
    }
    owned.to_csv(paths["squads"], index=False)
    select11.to_csv(paths["select_11"], index=False)
    weeks.to_csv(paths["weeks"], index=False)
    hurdles.to_csv(paths["hurdles"], index=False)
    summary.to_csv(paths["summary"], index=False)
    return paths


if __name__ == "__main__":
    written = export()
    summary = pd.read_csv(written["summary"])
    print("frozen_19gw_xi_xp", float(summary.loc[0, "frozen_19gw_xi_xp"]))
    for path in written.values():
        print("Wrote", path)
