"""Modular pre-deadline internal expected-minutes (xMins) baseline engine.

Constructs full-pool and sparse `(player_id, gameweek_id) -> xMins` estimates strictly from
pre-deadline Official FPL API metadata (`status`, `chance_of_playing_next_round`,
`news`, club fixtures) and `< target_gw` match history (plus optional prior-season
seed). Frozen production configuration (`SP_Soft_Shield_M1`) combines Soft Empirical
Shield curves with sparse `M1` club GKP allocation while leaving healthy outfielders
blank so `Model Champion` retains native conditional participation states.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from features.injury_triage import (
    compute_healthy_baseline_xmins,
    parse_fpl_return_date,
    resolve_gw_reference_date,
)

DEFAULT_CHANCE_MULTIPLIERS: tuple[tuple[int, float], ...] = (
    (0, 0.0),
    (25, 0.04),
    (50, 0.27),
    (75, 0.58),
    (100, 1.0),
)

# S-1 (2025-26) calibrated empirical recovery curves relative to healthy a_100 at horizon step t=0..5
SOFT_UNKNOWN_CURVE: tuple[float, ...] = (0.00, 0.08, 0.20, 0.33, 0.48, 0.55)
SOFT_SUSPENDED_N_CURVE: tuple[float, ...] = (0.00, 0.20, 0.35, 0.58, 0.81, 1.00)
SOFT_DOUBTFUL_CURVES: tuple[tuple[int, tuple[float, ...]], ...] = (
    (0, SOFT_UNKNOWN_CURVE),
    (25, (0.04, 0.23, 0.40, 0.53, 0.54, 0.62)),
    (50, (0.32, 0.64, 0.81, 0.88, 0.93, 0.93)),
    (75, (0.57, 0.83, 0.95, 1.00, 1.00, 1.00)),
    (100, (1.00, 1.00, 1.00, 1.00, 1.00, 1.00)),
)

_REQUIRED_FIXTURE_COLS = {"id", "gameweek_id", "home_club_id", "away_club_id"}


@dataclass(frozen=True)
class InternalXminsConfig:
    """Configuration for modular internal xMins baseline components (defaults = frozen SP_Soft_Shield_M1)."""

    enable_gkp_role: bool = True
    enable_starter_recovery: bool = False
    enable_availability_ramp: bool = True
    enable_club_reconciliation: bool = False

    gkp_clear_starter_mins: float = 89.0
    gkp_backup_mins: float = 1.0
    gkp_handover_starts: int = 2

    recovery_min_prior_starts: int = 4
    recovery_window_fixtures: int = 6
    recovery_max_missed_gws: int = 2
    recovery_1gw_weight: float = 0.85
    recovery_2gw_weight: float = 0.65

    chance_multipliers: tuple[tuple[int, float], ...] = DEFAULT_CHANCE_MULTIPLIERS
    doubtful_horizon_decay: float = 0.5
    post_return_min_prior_starts: int = 2

    outfield_club_target_mins: float = 890.0
    reconcile_gamma: float = 1.25
    reconcile_min_active_mins: float = 10.0
    outfield_cap_def: float = 87.5
    outfield_cap_mid_fwd: float = 84.5


def _chance_multiplier(chance: float, status: str, config: InternalXminsConfig) -> float:
    """Map FPL availability chance & status to S-1 calibrated play-time multiplier."""
    if status in {"i", "s", "u", "n"}:
        return 0.0
    if pd.isna(chance) or chance >= 100.0:
        return 1.0
    if chance <= 0.0:
        return 0.0
    table = sorted(config.chance_multipliers, key=lambda kv: kv[0])
    for lo, hi in zip(table, table[1:]):
        if lo[0] <= chance <= hi[0]:
            span = max(1, hi[0] - lo[0])
            w = (chance - lo[0]) / span
            return float(lo[1] + w * (hi[1] - lo[1]))
    return float(table[-1][1])


def soft_doubtful_multiplier(chance: float, step: int) -> float:
    """Interpolate S-1 calibrated availability multiplier for ``status='d'/'a'`` with ``chance < 100``."""
    idx = min(max(int(step), 0), 5)
    if chance <= 0.0:
        return SOFT_DOUBTFUL_CURVES[0][1][idx]
    if chance >= 100.0:
        return 1.0
    for (c_lo, cur_lo), (c_hi, cur_hi) in zip(SOFT_DOUBTFUL_CURVES, SOFT_DOUBTFUL_CURVES[1:]):
        if c_lo <= chance <= c_hi:
            weight = (chance - c_lo) / max(1, c_hi - c_lo)
            return float(cur_lo[idx] + weight * (cur_hi[idx] - cur_lo[idx]))
    return 1.0


def _clean_players(df_players: pd.DataFrame) -> pd.DataFrame:
    """Filter to outfield/GKP pool (`position_id` 1..4) with integer ID columns."""
    if df_players.empty or not {"id", "club_id", "position_id"}.issubset(df_players.columns):
        return pd.DataFrame(columns=["id", "club_id", "position_id"])
    players = df_players[df_players["position_id"].isin((1, 2, 3, 4))].copy()
    players["id"] = players["id"].astype(int)
    players["club_id"] = players["club_id"].astype(int)
    players["position_id"] = players["position_id"].astype(int)
    return players


def _prior_history(df_perfs: pd.DataFrame | None, target_gw: int) -> pd.DataFrame:
    """Return strictly causal match history (`gameweek_id < target_gw`)."""
    if df_perfs is None or df_perfs.empty or "gameweek_id" not in df_perfs.columns:
        return pd.DataFrame()
    return df_perfs[df_perfs["gameweek_id"] < int(target_gw)].copy()


def _build_perf_lookup(hist: pd.DataFrame) -> dict[tuple[int, int], tuple[float, int]]:
    """Index causal `(player_id, fixture_id) -> (minutes, starts)` safely."""
    if hist.empty or not {"player_id", "fixture_id", "minutes"}.issubset(hist.columns):
        return {}
    starts_col = hist["starts"] if "starts" in hist.columns else pd.Series(0, index=hist.index)
    return {
        (int(pid), int(fid)): (float(mins), int(st))
        for pid, fid, mins, st in zip(
            hist["player_id"].astype(int),
            hist["fixture_id"].astype(int),
            pd.to_numeric(hist["minutes"], errors="coerce").fillna(0.0),
            pd.to_numeric(starts_col, errors="coerce").fillna(0),
        )
    }


def _extract_club_schedule(
    df_fixtures: pd.DataFrame,
    planning_gws: list[int],
) -> tuple[dict[tuple[int, int], list[tuple[int, date | None]]], dict[tuple[int, int], date]]:
    """Map `(club_id, gw)` -> `[(fixture_id, kickoff_date)]` and earliest kickoff date."""
    if df_fixtures.empty or not _REQUIRED_FIXTURE_COLS.issubset(df_fixtures.columns):
        return {}, {}
    sub = df_fixtures[df_fixtures["gameweek_id"].isin(planning_gws)].copy()
    if sub.empty:
        return {}, {}
    sub["k_date"] = (
        pd.to_datetime(sub["kickoff_time"], utc=True, errors="coerce").dt.date
        if "kickoff_time" in sub.columns
        else pd.NaT
    )
    sort_cols = [c for c in ("gameweek_id", "kickoff_time", "id") if c in sub.columns]
    sub = sub.sort_values(sort_cols, kind="stable")

    club_gw_fixtures: dict[tuple[int, int], list[tuple[int, date | None]]] = {}
    club_gw_first_date: dict[tuple[int, int], date] = {}
    for _, row in sub.iterrows():
        gw = int(row["gameweek_id"])
        fid = int(row["id"])
        raw_d = row["k_date"]
        k_date: date | None = None if pd.isna(raw_d) else raw_d
        for col in ("home_club_id", "away_club_id"):
            cid = int(row[col])
            key = (cid, gw)
            club_gw_fixtures.setdefault(key, []).append((fid, k_date))
            if k_date is not None and (key not in club_gw_first_date or k_date < club_gw_first_date[key]):
                club_gw_first_date[key] = k_date
    return club_gw_fixtures, club_gw_first_date


def _build_club_fixture_history(df_fixtures: pd.DataFrame, target_gw: int) -> dict[int, list[int]]:
    """Return ordered list of fixture_ids strictly before `target_gw` per `club_id`."""
    if df_fixtures.empty or not _REQUIRED_FIXTURE_COLS.issubset(df_fixtures.columns):
        return {}
    past = df_fixtures[df_fixtures["gameweek_id"] < int(target_gw)].copy()
    if past.empty:
        return {}
    sort_cols = [c for c in ("gameweek_id", "kickoff_time", "id") if c in past.columns]
    past = past.sort_values(sort_cols, kind="stable")
    out: dict[int, list[int]] = {}
    for _, row in past.iterrows():
        fid = int(row["id"])
        for col in ("home_club_id", "away_club_id"):
            out.setdefault(int(row[col]), []).append(fid)
    return out


def _resolve_return_gw(
    club_id: int,
    ret_date: date | None,
    planning_gws: list[int],
    club_gw_first_date: Mapping[tuple[int, int], date],
) -> int | None:
    """Resolve first planning GW on or after `ret_date` for `club_id`."""
    if ret_date is None:
        return None
    for gw in planning_gws:
        k_date = club_gw_first_date.get((club_id, gw))
        if k_date is not None and k_date >= ret_date:
            return gw
    return None


def _build_seed_priors(
    df_players: pd.DataFrame,
    seed_perfs: pd.DataFrame | None,
    seed_players: pd.DataFrame | None,
) -> dict[int, tuple[float, float, int]]:
    """Map current player_id -> (seed_start_rate, seed_start_mins, seed_starts) via Official code."""
    if seed_perfs is None or seed_players is None or seed_perfs.empty or seed_players.empty:
        return {}
    if "code" not in df_players.columns or "code" not in seed_players.columns:
        return {}

    sp_map = seed_players.dropna(subset=["code"]).drop_duplicates("code").set_index("code")["id"].to_dict()
    agg = (
        seed_perfs.groupby("player_id", as_index=False)
        .agg(
            n_rows=("minutes", "count"),
            starts=("starts", "sum"),
            mins_when_start=("minutes", lambda s: float(s[s > 0].mean()) if (s > 0).any() else 0.0),
        )
        .set_index("player_id")
    )
    out: dict[int, tuple[float, float, int]] = {}
    for _, row in df_players.iterrows():
        pid = int(row["id"])
        code = row.get("code")
        if pd.isna(code) or code not in sp_map:
            continue
        spid = int(sp_map[code])
        if spid in agg.index:
            r = agg.loc[spid]
            starts = int(r["starts"])
            out[pid] = (float(starts) / max(1.0, float(r["n_rows"])), float(r["mins_when_start"]), starts)
    return out


def _fit_baseline_and_tenure(
    players: pd.DataFrame,
    hist: pd.DataFrame,
    seed_perfs: pd.DataFrame | None,
    seed_players: pd.DataFrame | None,
    *,
    min_prior_starts: int = 2,
) -> tuple[dict[int, float], dict[int, bool], dict[int, int], dict[int, float], dict[int, tuple[float, float, int]]]:
    """Compute healthy fit baseline, starter tenure, prior starts, prior medians, and seed priors."""
    prior_starts_count: dict[int, int] = {}
    prior_start_median: dict[int, float] = {}
    if not hist.empty and {"player_id", "starts", "minutes"}.issubset(hist.columns):
        started_rows = hist[pd.to_numeric(hist["starts"], errors="coerce").fillna(0) > 0]
        if not started_rows.empty:
            prior_starts_count = started_rows.groupby("player_id")["starts"].sum().astype(int).to_dict()
            prior_start_median = started_rows.groupby("player_id")["minutes"].median().astype(float).to_dict()

    seed_priors = _build_seed_priors(players, seed_perfs, seed_players)
    healthy_cost_fallback = compute_healthy_baseline_xmins(players, hist if not hist.empty else None)

    fit_mins_map: dict[int, float] = {}
    tenure_map: dict[int, bool] = {}
    for _, row in players.iterrows():
        pid = int(row["id"])
        seed_rate, seed_mins, seed_starts = seed_priors.get(pid, (0.0, 0.0, 0))
        if pid in prior_start_median and prior_starts_count.get(pid, 0) >= 1:
            fit_mins = float(prior_start_median[pid])
        elif seed_starts >= 3 and seed_mins >= 55.0:
            fit_mins = seed_mins
        else:
            fit_mins = float(healthy_cost_fallback.get(pid, 78.0))
        fit_mins_map[pid] = float(np.clip(fit_mins, 60.0, 89.0))
        tenure_map[pid] = (
            hist.empty
            or prior_starts_count.get(pid, 0) >= min_prior_starts
            or (seed_starts >= 5 and seed_rate >= 0.50)
        )
    return fit_mins_map, tenure_map, prior_starts_count, prior_start_median, seed_priors


def _rank_club_gkps(
    gkps: list[int],
    hist_fids: list[int],
    perf_lookup: Mapping[tuple[int, int], tuple[float, int]],
    prior_starts_count: Mapping[int, int],
    gkp_meta: Mapping[int, tuple[str, float, int]],
    handover_starts: int,
) -> list[int]:
    """Order club GKPs with 2-start available-rival handover and 1-game unflagged starter retention."""
    last2_fids = hist_fids[-handover_starts:] if len(hist_fids) >= handover_starts else []
    last6_fids = hist_fids[-6:]

    def rank_key(pid: int) -> tuple[int, int, int, int, float]:
        status, cost, seed_s = gkp_meta[pid]
        handover = 1 if (last2_fids and all(perf_lookup.get((pid, f), (0.0, 0))[1] > 0 for f in last2_fids)) else 0
        s6 = sum(1 for f in last6_fids if perf_lookup.get((pid, f), (0.0, 0))[1] > 0)
        last1_missed = 1 if (
            len(last6_fids) >= 4
            and s6 >= 3
            and status == "a"
            and perf_lookup.get((pid, last6_fids[-1]), (0.0, 0))[1] == 0
        ) else 0
        tot_s = prior_starts_count.get(pid, 0) + (seed_s if len(hist_fids) < 3 else 0)
        return (handover, last1_missed, s6, tot_s, cost)

    return sorted(gkps, key=rank_key, reverse=True)


def _allocate_gkp_slot_minutes(
    ranked_gkps: list[int],
    available_caps: Mapping[int, float],
    starter_cap: float,
    backup_mins: float,
    total_match_cap: float,
) -> dict[int, float]:
    """Assign GKP #1 and #2 minutes from ordered candidates and upper availability caps."""
    out = {pid: 0.0 for pid in ranked_gkps}
    available = [pid for pid in ranked_gkps if available_caps.get(pid, 0.0) > 0.0]
    if not available:
        return out
    gk1 = available[0]
    m1 = min(starter_cap, float(available_caps[gk1]))
    out[gk1] = m1
    if len(available) > 1:
        gk2 = available[1]
        rem = max(backup_mins, total_match_cap - m1) if m1 < (starter_cap - 0.5) else backup_mins
        out[gk2] = min(starter_cap, float(available_caps[gk2]), rem)
    return out


def _compute_m2_recovery_targets(
    p_meta: Mapping[int, Mapping[str, object]],
    club_hist_fids: Mapping[int, list[int]],
    perf_lookup: Mapping[tuple[int, int], tuple[float, int]],
    cfg: InternalXminsConfig,
) -> dict[int, tuple[float, float]]:
    """Precompute M2 unflagged 1-2 GW starter absence recovery targets."""
    targets: dict[int, tuple[float, float]] = {}
    for pid, meta in p_meta.items():
        if int(meta["position_id"]) == 1:  # type: ignore[arg-type]
            continue
        if str(meta["status"]) != "a" or float(meta["chance"]) < 100.0:  # type: ignore[arg-type]
            continue
        fids = club_hist_fids.get(int(meta["club_id"]), [])  # type: ignore[arg-type]
        if not fids:
            continue

        missed_0m = 0
        for fid in reversed(fids):
            m, st = perf_lookup.get((pid, fid), (0.0, 0))
            if st == 0 and m == 0.0:
                missed_0m += 1
            else:
                break
        if not (1 <= missed_0m <= cfg.recovery_max_missed_gws):
            continue

        prior_fids = fids[:-missed_0m]
        window = prior_fids[-cfg.recovery_window_fixtures :] if prior_fids else []
        starts_in_win = sum(1 for fid in window if perf_lookup.get((pid, fid), (0.0, 0))[1] > 0)
        seed_rate = float(meta["seed_rate"])  # type: ignore[arg-type]
        seed_starts = int(meta["seed_starts"])  # type: ignore[arg-type]
        established = (
            (len(window) >= 3 and starts_in_win >= min(cfg.recovery_min_prior_starts, len(window)) and starts_in_win / len(window) >= 0.66)
            or (len(window) < 3 and seed_starts >= 10 and seed_rate >= 0.70 and starts_in_win == len(window))
        )
        if not established:
            continue
        fit_mins = float(meta["fit_mins"])  # type: ignore[arg-type]
        w0 = cfg.recovery_1gw_weight if missed_0m == 1 else cfg.recovery_2gw_weight
        targets[pid] = (w0 * fit_mins, min(fit_mins, 0.92 * fit_mins))
    return targets


def _reconcile_club_outfield(
    outfield: list[int],
    fix_mins: dict[int, float],
    avail_map: Mapping[int, float],
    hard_locked: set[int],
    p_meta: Mapping[int, Mapping[str, object]],
    prior_start_median: Mapping[int, float],
    cfg: InternalXminsConfig,
) -> None:
    """Adjust healthy active outfield fixture minutes toward `cfg.outfield_club_target_mins` in-place."""
    eligible = [pid for pid in outfield if pid not in hard_locked and fix_mins[pid] >= cfg.reconcile_min_active_mins]
    if not eligible:
        return
    caps: dict[int, float] = {}
    for pid in eligible:
        pos = int(p_meta[pid]["position_id"])  # type: ignore[arg-type]
        pos_cap = cfg.outfield_cap_def if pos == 2 else cfg.outfield_cap_mid_fwd
        base_cap = min(90.0, max(pos_cap, prior_start_median.get(pid, pos_cap)))
        caps[pid] = min(base_cap, fix_mins[pid]) if avail_map[pid] < 0.99 else base_cap

    fixed_sum = sum(fix_mins[pid] for pid in outfield if pid not in eligible)
    target_elig = max(0.0, cfg.outfield_club_target_mins - fixed_sum)
    if abs(target_elig - sum(fix_mins[pid] for pid in eligible)) <= 1.0:
        return

    vals = {pid: fix_mins[pid] for pid in eligible}
    for _ in range(15):
        rem_diff = target_elig - sum(vals.values())
        if abs(rem_diff) <= 0.5:
            break
        if rem_diff > 0:
            movers = [pid for pid in eligible if vals[pid] < caps[pid] - 1e-6]
            if not movers:
                break
            weights = {pid: max(1e-6, vals[pid] ** cfg.reconcile_gamma) for pid in movers}
            w_sum = sum(weights.values())
            for pid in movers:
                vals[pid] = min(caps[pid], vals[pid] + rem_diff * weights[pid] / w_sum)
        else:
            movers = [pid for pid in eligible if vals[pid] > 1e-6]
            if not movers:
                break
            weights = {pid: max(1e-6, vals[pid]) for pid in movers}
            w_sum = sum(weights.values())
            for pid in movers:
                vals[pid] = max(0.0, vals[pid] + rem_diff * weights[pid] / w_sum)
    fix_mins.update(vals)


def filter_depressed_post_return(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    planning_gws: list[int],
    post_return_fallback: Mapping[tuple[int, int], float],
    native_mins_map: Mapping[tuple[int, int], float] | None,
    *,
    depressed_threshold_per_fix: float = 45.0,
) -> dict[tuple[int, int], float]:
    """Filter post-return steady fallbacks to cases where Champion native minutes remain depressed."""
    if not post_return_fallback or native_mins_map is None:
        return dict(post_return_fallback)
    club_gw_fixtures, _ = _extract_club_schedule(df_fixtures, planning_gws)
    club_of = df_players.set_index("id")["club_id"].astype(int).to_dict() if not df_players.empty else {}
    return {
        (pid, gw): val
        for (pid, gw), val in post_return_fallback.items()
        if float(native_mins_map.get((pid, gw), 0.0))
        < depressed_threshold_per_fix * max(1, len(club_gw_fixtures.get((club_of.get(pid, -1), gw), [])))
    }


def compute_internal_xmins_from_tables(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    *,
    native_mins_map: Mapping[tuple[int, int], float] | None = None,
    seed_perfs: pd.DataFrame | None = None,
    seed_players: pd.DataFrame | None = None,
    reference_date: date | None = None,
    config: InternalXminsConfig | None = None,
) -> dict[tuple[int, int], float]:
    """Compute configurable `(player_id, gw) -> xMins` strictly from `< target_gw` history and API snapshot."""
    cfg = config or InternalXminsConfig()
    planning_gws = list(range(int(target_gw), int(target_gw) + max(1, int(horizon))))
    ref = reference_date or date.today()

    players = _clean_players(df_players)
    if players.empty:
        return {}
    hist = _prior_history(df_perfs, target_gw)
    perf_lookup = _build_perf_lookup(hist)
    fit_mins_map, tenure_map, prior_starts_count, prior_start_median, seed_priors = _fit_baseline_and_tenure(
        players, hist, seed_perfs, seed_players, min_prior_starts=cfg.post_return_min_prior_starts
    )
    club_hist_fids = _build_club_fixture_history(df_fixtures, target_gw)
    club_gw_fixtures, club_gw_first_date = _extract_club_schedule(df_fixtures, planning_gws)
    if not club_gw_fixtures:
        return {}

    p_meta: dict[int, dict[str, object]] = {}
    club_players: dict[int, list[int]] = {}
    gkp_meta: dict[int, tuple[str, float, int]] = {}
    for _, row in players.iterrows():
        pid = int(row["id"])
        cid = int(row["club_id"])
        pos = int(row["position_id"])
        status = str(row.get("status", "a") or "a").lower()
        raw_ch = row.get("chance_of_playing_next_round")
        chance = 100.0 if raw_ch is None or pd.isna(raw_ch) else float(raw_ch)
        ret_date = parse_fpl_return_date(str(row.get("news") or ""), ref)
        seed_rate, _, seed_starts = seed_priors.get(pid, (0.0, 0.0, 0))
        cost = float(row.get("now_cost", 50) or 50) / 10.0

        p_meta[pid] = {
            "club_id": cid,
            "position_id": pos,
            "cost": cost,
            "status": status,
            "chance": chance,
            "return_gw": _resolve_return_gw(cid, ret_date, planning_gws, club_gw_first_date),
            "fit_mins": fit_mins_map[pid],
            "has_tenure": tenure_map[pid],
            "seed_rate": seed_rate,
            "seed_starts": seed_starts,
        }
        club_players.setdefault(cid, []).append(pid)
        if pos == 1:
            gkp_meta[pid] = (status, cost, seed_starts)

    def availability_for_gw(pid: int, gw: int, base_mins: float) -> tuple[float, float | None]:
        meta = p_meta[pid]
        status = str(meta["status"])
        chance = float(meta["chance"])  # type: ignore[arg-type]
        return_gw = meta["return_gw"]  # type: ignore[assignment]
        fit_mins = float(meta["fit_mins"])  # type: ignore[arg-type]
        step = gw - int(target_gw)

        if not cfg.enable_availability_ramp:
            if status in {"i", "s", "u", "n"} and (step == 0 or chance <= 0.0):
                return 0.0, None
            if step == 0 and chance < 100.0:
                return max(0.0, min(1.0, chance / 100.0)), None
            return 1.0, None

        if status in {"i", "s", "u", "n"}:
            if return_gw is None or gw < int(return_gw):
                return 0.0, 0.0
            steady = min(86.0, fit_mins) if bool(meta["has_tenure"]) else base_mins
            if status == "s":
                return steady / 90.0, steady
            if status == "i":
                if gw == int(target_gw) and chance <= 0.0:
                    return 0.0, 0.0
                if gw == int(return_gw):
                    val = min(20.0, steady)
                    return val / 90.0, val
                if gw == int(return_gw) + 1:
                    val = min(65.0, steady)
                    return val / 90.0, val
                return steady / 90.0, steady
            return 0.0, 0.0

        if chance < 100.0:
            p_play = _chance_multiplier(chance, status, cfg)
            return float(np.clip(1.0 - (1.0 - p_play) * (cfg.doubtful_horizon_decay ** step), 0.0, 1.0)), None
        return 1.0, None

    m2_target_by_pid = _compute_m2_recovery_targets(p_meta, club_hist_fids, perf_lookup, cfg) if cfg.enable_starter_recovery else {}
    gw_totals: dict[tuple[int, int], float] = {(pid, gw): 0.0 for pid in p_meta for gw in planning_gws}

    for cid, pids in club_players.items():
        hist_fids = club_hist_fids.get(cid, [])
        gkps = [pid for pid in pids if int(p_meta[pid]["position_id"]) == 1]  # type: ignore[arg-type]
        outfield = [pid for pid in pids if int(p_meta[pid]["position_id"]) in (2, 3, 4)]  # type: ignore[arg-type]
        ranked_gkps = _rank_club_gkps(gkps, hist_fids, perf_lookup, prior_starts_count, gkp_meta, cfg.gkp_handover_starts)

        for gw in planning_gws:
            step = gw - int(target_gw)
            sched = club_gw_fixtures.get((cid, gw), [])
            n_fix = len(sched)
            if n_fix == 0:
                continue

            for _fid, _kdate in sched:
                fix_mins: dict[int, float] = {}
                avail_map: dict[int, float] = {}
                hard_locked: set[int] = set()

                for pid in pids:
                    meta = p_meta[pid]
                    if native_mins_map is not None and (pid, gw) in native_mins_map:
                        base_m = float(native_mins_map[(pid, gw)]) / n_fix
                    else:
                        base_m = (
                            (prior_starts_count.get(pid, 0) / len(hist_fids)) * float(meta["fit_mins"])  # type: ignore[arg-type]
                            if hist_fids
                            else float(meta["seed_rate"]) * float(meta["fit_mins"])  # type: ignore[arg-type]
                        )
                    base_m = float(np.clip(base_m, 0.0, 90.0))

                    if pid in m2_target_by_pid:
                        t0_val, t1_val = m2_target_by_pid[pid]
                        rec_target = t0_val if step == 0 else t1_val
                        if base_m < rec_target:
                            base_m = rec_target

                    avail, hard_val = availability_for_gw(pid, gw, base_m)
                    avail_map[pid] = avail
                    if hard_val is not None:
                        base_m = float(np.clip(hard_val, 0.0, 90.0))
                        hard_locked.add(pid)
                    elif cfg.enable_availability_ramp and avail < 1.0:
                        base_m = float(np.clip(base_m * avail, 0.0, 90.0))
                    fix_mins[pid] = base_m

                if cfg.enable_gkp_role and ranked_gkps:
                    gk_caps = {pid: (cfg.gkp_clear_starter_mins * avail_map[pid] if avail_map[pid] > 0.0 else 0.0) for pid in ranked_gkps}
                    fix_mins.update(
                        _allocate_gkp_slot_minutes(
                            ranked_gkps, gk_caps, cfg.gkp_clear_starter_mins, cfg.gkp_backup_mins, 90.0
                        )
                    )

                if cfg.enable_club_reconciliation:
                    _reconcile_club_outfield(outfield, fix_mins, avail_map, hard_locked, p_meta, prior_start_median, cfg)

                for pid in pids:
                    gw_totals[(pid, gw)] += float(fix_mins[pid])

    return gw_totals


def build_soft_shield_layers(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    *,
    native_mins_map: Mapping[tuple[int, int], float] | None = None,
    seed_perfs: pd.DataFrame | None = None,
    seed_players: pd.DataFrame | None = None,
    reference_date: date | None = None,
) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], float], dict[tuple[int, int], float]]:
    """Build flagged-only Soft Empirical Shield split into (hard_guard, soft_curve, post_return_fallback)."""
    planning_gws = list(range(int(target_gw), int(target_gw) + max(1, int(horizon))))
    ref = reference_date or date.today()
    players = _clean_players(df_players)
    if players.empty:
        return {}, {}, {}

    hist = _prior_history(df_perfs, target_gw)
    fit_mins_map, tenure_map, _, _, _ = _fit_baseline_and_tenure(players, hist, seed_perfs, seed_players)
    club_gw_fixtures, club_gw_first_date = _extract_club_schedule(df_fixtures, planning_gws)
    if not club_gw_fixtures:
        return {}, {}, {}

    hard_guard: dict[tuple[int, int], float] = {}
    soft_curve: dict[tuple[int, int], float] = {}
    post_return_fallback: dict[tuple[int, int], float] = {}

    for _, row in players.iterrows():
        pid = int(row["id"])
        cid = int(row["club_id"])
        status = str(row.get("status", "a") or "a").lower()
        raw_ch = row.get("chance_of_playing_next_round")
        chance = 100.0 if raw_ch is None or pd.isna(raw_ch) else float(raw_ch)
        if status == "a" and chance >= 100.0:
            continue

        news = str(row.get("news") or "")
        return_gw = _resolve_return_gw(cid, parse_fpl_return_date(news, ref), planning_gws, club_gw_first_date)
        fit_mins = fit_mins_map[pid]
        has_tenure = tenure_map[pid]

        for gw in planning_gws:
            n_fix = len(club_gw_fixtures.get((cid, gw), []))
            if n_fix == 0:
                continue
            step = gw - int(target_gw)
            s_idx = min(max(step, 0), 5)
            base_m = float(native_mins_map[(pid, gw)]) if native_mins_map is not None and (pid, gw) in native_mins_map else fit_mins * n_fix

            if status == "u":
                hard_guard[(pid, gw)] = 0.0
            elif status == "n":
                if "parent club" in news.lower():
                    if step == 0:
                        hard_guard[(pid, gw)] = 0.0
                else:
                    mult = SOFT_SUSPENDED_N_CURVE[s_idx]
                    if mult <= 0.0:
                        hard_guard[(pid, gw)] = 0.0
                    elif mult < 0.99:
                        soft_curve[(pid, gw)] = base_m * mult
            elif status == "s":
                if return_gw is not None:
                    if gw < return_gw:
                        hard_guard[(pid, gw)] = 0.0
                    elif has_tenure:
                        post_return_fallback[(pid, gw)] = fit_mins * n_fix
                elif step == 0:
                    hard_guard[(pid, gw)] = 0.0
            elif status == "i":
                if return_gw is not None:
                    if gw < return_gw:
                        hard_guard[(pid, gw)] = 0.0
                    elif gw == return_gw:
                        hard_guard[(pid, gw)] = 0.0 if (gw == int(target_gw) and chance <= 0.0) else min(20.0, fit_mins) * n_fix
                    elif gw == return_gw + 1:
                        hard_guard[(pid, gw)] = min(65.0, fit_mins) * n_fix
                    elif has_tenure:
                        post_return_fallback[(pid, gw)] = fit_mins * n_fix
                else:
                    mult = SOFT_UNKNOWN_CURVE[s_idx]
                    if mult <= 0.0:
                        hard_guard[(pid, gw)] = 0.0
                    else:
                        soft_curve[(pid, gw)] = base_m * mult
            elif chance < 100.0:
                if step == 0 and chance <= 0.0:
                    hard_guard[(pid, gw)] = 0.0
                else:
                    mult = soft_doubtful_multiplier(chance, step)
                    if mult <= 0.0:
                        hard_guard[(pid, gw)] = 0.0
                    elif mult < 0.99:
                        soft_curve[(pid, gw)] = base_m * mult

    return hard_guard, soft_curve, post_return_fallback


def build_sparse_gkp_baseline(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    *,
    soft_overrides: Mapping[tuple[int, int], float] | None = None,
    seed_perfs: pd.DataFrame | None = None,
    seed_players: pd.DataFrame | None = None,
    clear_starter_mins: float = 89.0,
    backup_mins: float = 1.0,
    handover_starts: int = 2,
) -> dict[tuple[int, int], float]:
    """Allocate club GKP #1/#2 minutes sparsely (`position_id == 1` only) respecting availability overrides."""
    planning_gws = list(range(int(target_gw), int(target_gw) + max(1, int(horizon))))
    players = _clean_players(df_players)
    gk_rows = players[players["position_id"] == 1].copy()
    if gk_rows.empty:
        return {}

    hist = _prior_history(df_perfs, target_gw)
    _, _, prior_starts_count, _, seed_priors = _fit_baseline_and_tenure(gk_rows, hist, seed_perfs, seed_players)
    perf_lookup = _build_perf_lookup(hist)
    club_hist_fids = _build_club_fixture_history(df_fixtures, target_gw)
    club_gw_fixtures, _ = _extract_club_schedule(df_fixtures, planning_gws)
    if not club_gw_fixtures:
        return {}

    soft = soft_overrides or {}
    gkps_by_club: dict[int, list[int]] = {}
    gkp_meta: dict[int, tuple[str, float, int]] = {}
    for _, row in gk_rows.iterrows():
        pid = int(row["id"])
        gkps_by_club.setdefault(int(row["club_id"]), []).append(pid)
        gkp_meta[pid] = (
            str(row.get("status", "a") or "a").lower(),
            float(row.get("now_cost", 45) or 45) / 10.0,
            int(seed_priors.get(pid, (0.0, 0.0, 0))[2]),
        )

    out: dict[tuple[int, int], float] = {}
    for cid, gkps in gkps_by_club.items():
        ranked = _rank_club_gkps(gkps, club_hist_fids.get(cid, []), perf_lookup, prior_starts_count, gkp_meta, handover_starts)
        for gw in planning_gws:
            n_fix = len(club_gw_fixtures.get((cid, gw), []))
            if n_fix == 0:
                continue
            caps = {pid: float(soft.get((pid, gw), clear_starter_mins * n_fix)) for pid in ranked}
            alloc = _allocate_gkp_slot_minutes(
                ranked, caps, clear_starter_mins * n_fix, backup_mins * n_fix, 90.0 * n_fix
            )
            for pid, mins in alloc.items():
                out[(pid, gw)] = mins
    return out


def build_frozen_internal_minutes_baseline(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    *,
    native_mins_map: Mapping[tuple[int, int], float] | None = None,
    seed_perfs: pd.DataFrame | None = None,
    seed_players: pd.DataFrame | None = None,
    reference_date: date | None = None,
) -> dict[tuple[int, int], float]:
    """Build frozen SP_Soft_Shield_M1 map: Soft Empirical Shield + Sparse M1 GKP (outfielders stay on L1)."""
    hard_guard, soft_curve, post_fallback = build_soft_shield_layers(
        df_players,
        df_fixtures,
        df_perfs,
        target_gw,
        horizon,
        native_mins_map=native_mins_map,
        seed_perfs=seed_perfs,
        seed_players=seed_players,
        reference_date=reference_date,
    )
    planning_gws = list(range(int(target_gw), int(target_gw) + max(1, int(horizon))))
    filtered_post = filter_depressed_post_return(df_players, df_fixtures, planning_gws, post_fallback, native_mins_map)
    soft_all = {**filtered_post, **soft_curve, **hard_guard}
    gkp_map = build_sparse_gkp_baseline(
        df_players,
        df_fixtures,
        df_perfs,
        target_gw,
        horizon,
        soft_overrides=soft_all,
        seed_perfs=seed_perfs,
        seed_players=seed_players,
    )
    return {**soft_all, **gkp_map}


def build_internal_minutes_baseline(
    processed_dir: Path,
    target_gw: int,
    horizon: int,
    *,
    native_mins_map: Mapping[tuple[int, int], float] | None = None,
    seed_processed_dir: Path | None = None,
    reference_date: date | None = None,
    config: InternalXminsConfig | None = None,
) -> dict[tuple[int, int], float]:
    """Convenience wrapper loading Parquet tables from processed_dir."""
    df_players = pd.read_parquet(processed_dir / "players.parquet")
    df_fixtures = pd.read_parquet(processed_dir / "fixtures.parquet")
    perfs_path = processed_dir / "player_performances.parquet"
    df_perfs = pd.read_parquet(perfs_path) if perfs_path.exists() else pd.DataFrame()

    seed_perfs = None
    seed_players = None
    if seed_processed_dir is not None and seed_processed_dir.exists():
        sp_path = seed_processed_dir / "player_performances.parquet"
        spl_path = seed_processed_dir / "players.parquet"
        if sp_path.exists() and spl_path.exists():
            seed_perfs = pd.read_parquet(sp_path)
            seed_players = pd.read_parquet(spl_path)

    ref = reference_date or resolve_gw_reference_date(processed_dir, target_gw)
    if config is None:
        return build_frozen_internal_minutes_baseline(
            df_players,
            df_fixtures,
            df_perfs,
            target_gw,
            horizon,
            native_mins_map=native_mins_map,
            seed_perfs=seed_perfs,
            seed_players=seed_players,
            reference_date=ref,
        )
    return compute_internal_xmins_from_tables(
        df_players,
        df_fixtures,
        df_perfs,
        target_gw,
        horizon,
        native_mins_map=native_mins_map,
        seed_perfs=seed_perfs,
        seed_players=seed_players,
        reference_date=ref,
        config=config,
    )
