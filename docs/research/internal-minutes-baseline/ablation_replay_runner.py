"""Research-only Option 1 (State-Preserving + Soft Shield) & Option 2 (Sparse Module) 6-GW Rolling Replay Ablation."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime
import json
import lzma
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Mapping, cast

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
IDEATION_DIR = ROOT / "docs/research/candidate-ideation"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(IDEATION_DIR) not in sys.path:
    sys.path.insert(0, str(IDEATION_DIR))

from backtesting.native_transfer_solver import native_strategic_solve  # noqa: E402
from backtesting.ownership_anchor import OwnershipAnchor, UniverseSchema, solve_ownership_anchor  # noqa: E402
from backtesting.rolling_replay import (  # noqa: E402
    DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS,
    DEFAULT_HORIZON,
    QualityPolicy,
    run_rolling_replay,
)
from commands.run_stage_a_and_b import _outcomes_for_gw  # noqa: E402
from features.availability_snapshots import resolve_latest_snapshot  # noqa: E402
from features.builder import build_features  # noqa: E402
from features.injury_triage import parse_fpl_return_date  # noqa: E402
from features.internal_xmins import (  # noqa: E402
    InternalXminsConfig,
    _build_club_fixture_history,
    _build_seed_priors,
    _extract_club_schedule,
    compute_internal_xmins_from_tables,
)
from historical_replay_inputs import stage_s1_inputs  # noqa: E402
from models.base import cap_projected_minutes, iter_feature_rows, resolve_asof_target_gw  # noqa: E402
from models.def_xg_shrink_challenger import (  # noqa: E402
    DefXgShrinkChallengerModel,
    _POSITION_K,
    _RATIO_CLIP,
    shrunk_xg_rates,
)
from models.hold_chase_challenger import (  # noqa: E402
    _CEILING_TILT_FROM,
    _MINS_TILT,
    _XG_SHARP_FROM,
    _XG_SHARP_SLOPE,
    _XG_TRIM_BELOW,
    _XG_TRIM_FACTOR,
    HoldChaseChallengerModel,
)
from models.learned_start_challenger import (  # noqa: E402
    learned_start_probabilities,
    target_start_probabilities,
)
from models.metrics_component_hybrid import _POS_CODE, _number  # noqa: E402
from models.participation_state_hybrid import target_to_states  # noqa: E402
from s2_historical_replay_inputs import stage_s2_inputs  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
CACHE_ROOT = ROOT / ".tmp/agent/internal-minutes-ablation"
SHIELD_REFERENCE_NET = {"2025-26": 2107, "2024-25": 2206}

FROZEN_CFG = InternalXminsConfig(
    enable_gkp_role=True,
    enable_starter_recovery=False,
    enable_availability_ramp=True,
    enable_club_reconciliation=True,
)
M1_ONLY_CFG = InternalXminsConfig(
    enable_gkp_role=True,
    enable_starter_recovery=False,
    enable_availability_ramp=False,
    enable_club_reconciliation=False,
)
M3_ONLY_CFG = InternalXminsConfig(
    enable_gkp_role=False,
    enable_starter_recovery=False,
    enable_availability_ramp=True,
    enable_club_reconciliation=False,
)
M4_ONLY_CFG = InternalXminsConfig(
    enable_gkp_role=False,
    enable_starter_recovery=False,
    enable_availability_ramp=False,
    enable_club_reconciliation=True,
)

# S-1 (2025-26) empirical recovery ratios relative to healthy a_100 at horizon step t = 0..5
SOFT_UNKNOWN_CURVE = (0.00, 0.08, 0.20, 0.33, 0.48, 0.55)
SOFT_SUSPENDED_N_CURVE = (0.00, 0.20, 0.35, 0.58, 0.81, 1.00)
SOFT_DOUBTFUL_CURVES: tuple[tuple[int, tuple[float, ...]], ...] = (
    (0, SOFT_UNKNOWN_CURVE),
    (25, (0.04, 0.23, 0.40, 0.53, 0.54, 0.62)),
    (50, (0.32, 0.64, 0.81, 0.88, 0.93, 0.93)),
    (75, (0.57, 0.83, 0.95, 1.00, 1.00, 1.00)),
    (100, (1.00, 1.00, 1.00, 1.00, 1.00, 1.00)),
)

ALL_ARMS: tuple[str, ...] = (
    "L1_native",
    "Sparse_M1_gkp",
    "Sparse_M1_M3",
    "Solo_M4_reconcile",
    "Soft_Shield_M1",
    "SP_M1_M3_M4",
    "SP_Soft_Shield_M1",
    "SP_Soft_M1_M3_M4",
)
SP_ARMS = {"SP_M1_M3_M4", "SP_Soft_Shield_M1", "SP_Soft_M1_M3_M4"}


def _clamp01(val: float) -> float:
    return min(1.0, max(0.0, float(val)))


def scale_states_to_target(
    p_dnp: float,
    p_start: float,
    p_sub_in: float,
    start_mins: float,
    sub_mins: float,
    p60_start: float,
    p60_sub: float,
    target_mins: float,
) -> tuple[float, float, float, float, float, float, float]:
    """Scale native participation states to hit ``target_mins`` while preserving conditional uncertainty."""
    target = max(0.0, float(target_mins))
    if target <= 0.0:
        return 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    native_mins = p_start * start_mins + p_sub_in * sub_mins
    if abs(target - native_mins) <= 1e-6:
        return p_dnp, p_start, p_sub_in, start_mins, sub_mins, p60_start, p60_sub

    if native_mins < 5.0:
        ps, psub, pd, sm, subm = target_to_states(target)
        return (
            pd,
            ps,
            psub,
            sm,
            subm,
            _clamp01((sm - 45.0) / 30.0),
            _clamp01((subm - 45.0) / 30.0),
        )

    if target < native_mins:
        alpha = target / native_mins
        new_start = p_start * alpha
        new_sub = p_sub_in * alpha
        new_dnp = max(0.0, 1.0 - new_start - new_sub)
        tot = new_dnp + new_start + new_sub
        if tot > 0.0 and abs(tot - 1.0) > 1e-9:
            new_dnp, new_start, new_sub = new_dnp / tot, new_start / tot, new_sub / tot
        return new_dnp, new_start, new_sub, start_mins, sub_mins, p60_start, p60_sub

    # Scaling UP: dnp -> start (cap 0.99), then sub -> start (cap 0.99), then extend start_mins <= 90
    cur_dnp, cur_start, cur_sub = p_dnp, p_start, p_sub_in
    cur_sm, cur_subm = start_mins, sub_mins
    cur_p60_s, cur_p60_sub = p60_start, p60_sub
    cur_mins = native_mins

    if cur_sm > 1e-6 and cur_dnp > 0.0:
        need_p = (target - cur_mins) / cur_sm
        dp = min(cur_dnp, max(0.0, 0.99 - cur_start), need_p)
        cur_start += dp
        cur_dnp -= dp
        cur_mins = cur_start * cur_sm + cur_sub * cur_subm

    if cur_mins < target - 1e-6 and cur_sub > 0.0 and cur_sm > cur_subm + 1e-6:
        need_p = (target - cur_mins) / (cur_sm - cur_subm)
        dp = min(cur_sub, max(0.0, 0.99 - cur_start), need_p)
        cur_start += dp
        cur_sub -= dp
        cur_mins = cur_start * cur_sm + cur_sub * cur_subm

    if cur_mins < target - 1e-6 and cur_start > 1e-6:
        cur_sm = min(90.0, max(cur_sm, (target - cur_sub * cur_subm) / cur_start))
        cur_p60_s = max(cur_p60_s, _clamp01((cur_sm - 45.0) / 30.0))

    tot = cur_dnp + cur_start + cur_sub
    if tot > 0.0 and abs(tot - 1.0) > 1e-9:
        cur_dnp, cur_start, cur_sub = cur_dnp / tot, cur_start / tot, cur_sub / tot
    return cur_dnp, cur_start, cur_sub, cur_sm, cur_subm, cur_p60_s, cur_p60_sub


class StatePreservingDefXgShrinkModel(DefXgShrinkChallengerModel):
    """Research Challenger subclass that scales native (p_start, p_sub, p_60) toward external_xmins."""

    @property
    def name(self) -> str:
        return "state_preserving_def_xg_shrink"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        # Prepare features through DefXgShrink -> LearnedStart -> MultiFeature -> HoldChase without loss
        features = features_df.copy()
        if not self._xg_hist.empty:
            positions = features.drop_duplicates("player_id").set_index("player_id")["position_id"]
            new = shrunk_xg_rates(self._xg_hist, positions, _POSITION_K)
            old = shrunk_xg_rates(self._xg_hist, positions, {})
            ratio = (new / old.where(old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)
            features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()

        target_gw = resolve_asof_target_gw(features, self._raw_history)
        self._p_target = target_start_probabilities(
            features,
            learned_start_probabilities(self._raw_history, features),
            target_gw=target_gw,
        )
        self._assist_rates = self._fit_assist_rates(features)

        xg = pd.to_numeric(features.get("per90_xg", 0.0), errors="coerce").fillna(0.0)
        xa = pd.to_numeric(features.get("per90_xa", 0.0), errors="coerce").fillna(0.0)
        sharp = 1.0 + _XG_SHARP_SLOPE * ((xg - _XG_SHARP_FROM) / _XG_SHARP_FROM).clip(lower=0.0, upper=1.0)
        sharp = sharp.where(xg >= _XG_TRIM_BELOW, _XG_TRIM_FACTOR)
        features["per90_xg"] = (xg * sharp).clip(lower=0.0)
        ceiling = (features["per90_xg"] + xa) >= _CEILING_TILT_FROM
        for column in ("xmins_if_start", "xmins_if_sub_in"):
            if column in features.columns:
                features.loc[ceiling, column] = pd.to_numeric(features.loc[ceiling, column], errors="coerce").fillna(0.0) * _MINS_TILT
        features = HoldChaseChallengerModel._apply_hard_fixture_defence(features)

        components: list[dict[str, object]] = []
        bonus_groups: defaultdict[int, list[int]] = defaultdict(list)
        component_columns = (
            "xp_minutes",
            "xp_goals",
            "xp_assists",
            "xp_clean_sheet",
            "xp_conceded",
            "xp_defcon",
            "xp_saves",
            "xp_yellow_cards",
            "xp_red_cards",
            "xp_penalties_saved",
            "xp_penalties_missed",
            "xp_own_goals",
            "xp_bonus",
        )

        for row, gameweek_id, fixture_id in iter_feature_rows(features, horizon):
            if fixture_id is not None and fixture_id < 0:
                components.append({
                    "player_id": int(row["player_id"]),
                    "gameweek_id": gameweek_id,
                    "fixture_id": fixture_id,
                    "projected_points": 0.0,
                    "projected_minutes": 0.0,
                    "xbps": 0.0,
                    "p_dnp": 1.0,
                    "p_start": 0.0,
                    "p_sub_in": 0.0,
                })
                continue

            # Always compute native participation states first
            p_dnp, p_start, p_sub_in = self._state_probabilities(row)
            is_immediate = bool(row.get("is_immediate_next_gw", False))
            has_snapshot = bool(row.get("has_availability_snapshot", False))
            chance = _number(row, "chance_of_playing", 100.0)
            status = str(row.get("status", "")).lower()

            if is_immediate and (
                (has_snapshot and chance <= 0.0)
                or (not has_snapshot and (chance <= 0.0 or status in {"i", "s", "u", "n"}))
            ):
                p_dnp, p_start, p_sub_in = 1.0, 0.0, 0.0

            start_minutes = self._conditional_minutes(row, "start", 78.0)
            sub_minutes = self._conditional_minutes(row, "sub_in", 18.0)
            p60_start = _clamp01(_number(row, "p_60_if_start", (start_minutes - 45.0) / 30.0))
            p60_sub = _clamp01(_number(row, "p_60_if_sub_in", (sub_minutes - 45.0) / 30.0))

            raw_minutes = p_start * start_minutes + p_sub_in * sub_minutes
            expected_minutes = cap_projected_minutes(row, raw_minutes)
            if raw_minutes > 0 and expected_minutes < raw_minutes:
                scale = expected_minutes / raw_minutes
                start_minutes *= scale
                sub_minutes *= scale

            ext_mins = row.get("external_xmins")
            if ext_mins is not None and pd.notna(ext_mins):
                target_mins = max(0.0, float(ext_mins))
                p_dnp, p_start, p_sub_in, start_minutes, sub_minutes, p60_start, p60_sub = scale_states_to_target(
                    p_dnp,
                    p_start,
                    p_sub_in,
                    start_minutes,
                    sub_minutes,
                    p60_start,
                    p60_sub,
                    target_mins,
                )
                expected_minutes = target_mins

            position = _POS_CODE.get(int(_number(row, "position_id", 3.0)), "M")
            start_events = self._project_event_components(
                row,
                position,
                start_minutes,
                clean_sheet_minutes=start_minutes,
                p_sixty_mins=p60_start,
            )
            sub_events = self._project_event_components(
                row,
                position,
                sub_minutes,
                clean_sheet_minutes=sub_minutes,
                p_sixty_mins=p60_sub,
            )
            weighted_events = {
                key: p_start * float(start_events[key]) + p_sub_in * float(sub_events[key])
                for key in start_events
                if key not in {"eligible_bonus", "projected_points"}
            }
            xp_minutes = p_start * (1.0 + p60_start) + p_sub_in * (1.0 + p60_sub)
            weighted_points = (
                p_start * float(start_events["projected_points"])
                + p_sub_in * float(sub_events["projected_points"])
            )
            eligible_bonus = (
                (p_start if start_minutes >= 45.0 else 0.0)
                + (p_sub_in if sub_minutes >= 45.0 else 0.0)
            )
            index = len(components)
            components.append({
                "player_id": int(row["player_id"]),
                "gameweek_id": gameweek_id,
                "fixture_id": fixture_id,
                "projected_points": xp_minutes + weighted_points,
                "projected_minutes": expected_minutes,
                "xbps": weighted_events["xbps"],
                "xp_minutes": xp_minutes,
                "p_dnp": p_dnp,
                "p_start": p_start,
                "p_sub_in": p_sub_in,
                "xmins_if_start": start_minutes,
                "xmins_if_sub_in": sub_minutes,
                "p_60_if_start": p60_start,
                "p_60_if_sub_in": p60_sub,
                **weighted_events,
            })
            if eligible_bonus > 0 and fixture_id is not None and fixture_id >= 0:
                bonus_groups[fixture_id].append(index)

        self._allocate_bonus(components, bonus_groups)
        output = []
        for component in components:
            prediction = {
                "player_id": component["player_id"],
                "gameweek_id": component["gameweek_id"],
                "projected_points": component["projected_points"],
                "projected_minutes": component["projected_minutes"],
                **{column: component.get(column, 0.0) for column in component_columns},
                "p_dnp": component.get("p_dnp", 1.0),
                "p_start": component.get("p_start", 0.0),
                "p_sub_in": component.get("p_sub_in", 0.0),
                "xmins_if_start": component.get("xmins_if_start", 0.0),
                "xmins_if_sub_in": component.get("xmins_if_sub_in", 0.0),
                "p_60_if_start": component.get("p_60_if_start", 0.0),
                "p_60_if_sub_in": component.get("p_60_if_sub_in", 0.0),
            }
            if component["fixture_id"] is not None:
                prediction["fixture_id"] = component["fixture_id"]
            output.append(prediction)
        return pd.DataFrame(output)


def _soft_doubtful_mult(chance: float, step: int) -> float:
    s = min(max(step, 0), 5)
    if chance <= 0.0:
        return SOFT_DOUBTFUL_CURVES[0][1][s]
    if chance >= 100.0:
        return 1.0
    for (c_lo, cur_lo), (c_hi, cur_hi) in zip(SOFT_DOUBTFUL_CURVES, SOFT_DOUBTFUL_CURVES[1:]):
        if c_lo <= chance <= c_hi:
            w = (chance - c_lo) / max(1, c_hi - c_lo)
            return float(cur_lo[s] + w * (cur_hi[s] - cur_lo[s]))
    return 1.0


def _soft_shield_details(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    native_mins_map: Mapping[tuple[int, int], float],
    seed_perfs: pd.DataFrame | None,
    seed_players: pd.DataFrame | None,
    reference_date: date,
) -> tuple[dict[tuple[int, int], float], set[tuple[int, int]]]:
    """Build Soft Empirical Shield sparse overrides for flagged players only, plus hard-zero keys."""
    planning_gws = list(range(int(target_gw), int(target_gw) + max(1, int(horizon))))
    players = df_players[df_players["position_id"].isin((1, 2, 3, 4))].copy()
    players["id"] = players["id"].astype(int)
    players["club_id"] = players["club_id"].astype(int)
    players["position_id"] = players["position_id"].astype(int)

    hist = df_perfs[df_perfs["gameweek_id"] < int(target_gw)].copy() if not df_perfs.empty else pd.DataFrame()
    prior_starts_count: dict[int, int] = {}
    prior_start_median: dict[int, float] = {}
    if not hist.empty:
        started_rows = hist[pd.to_numeric(hist.get("starts", 0), errors="coerce").fillna(0) > 0]
        if not started_rows.empty:
            prior_starts_count = started_rows.groupby("player_id")["starts"].sum().astype(int).to_dict()
            prior_start_median = started_rows.groupby("player_id")["minutes"].median().astype(float).to_dict()

    seed_priors = _build_seed_priors(players, seed_perfs, seed_players)
    club_gw_fixtures, club_gw_first_date = _extract_club_schedule(df_fixtures, planning_gws)

    soft_map: dict[tuple[int, int], float] = {}
    hard_zero_keys: set[tuple[int, int]] = set()

    for _, row in players.iterrows():
        pid = int(row["id"])
        cid = int(row["club_id"])
        pos = int(row["position_id"])
        status = str(row.get("status", "a") or "a").lower()
        raw_ch = row.get("chance_of_playing_next_round")
        chance = 100.0 if raw_ch is None or pd.isna(raw_ch) else float(raw_ch)
        if status == "a" and chance >= 100.0:
            continue

        news = str(row.get("news") or "")
        ret_date = parse_fpl_return_date(news, reference_date)
        return_gw: int | None = None
        if ret_date is not None:
            for gw in planning_gws:
                k_date = club_gw_first_date.get((cid, gw))
                if k_date is not None and k_date >= ret_date:
                    return_gw = gw
                    break

        seed_rate, seed_mins, seed_starts = seed_priors.get(pid, (0.0, 0.0, 0))
        if pid in prior_start_median and prior_starts_count.get(pid, 0) >= 1:
            fit_mins = float(prior_start_median[pid])
        elif seed_starts >= 3 and seed_mins >= 55.0:
            fit_mins = seed_mins
        else:
            fit_mins = 89.0 if pos == 1 else (84.0 if pos == 2 else 78.0)
        fit_mins = float(np.clip(fit_mins, 60.0, 89.0))
        has_tenure = prior_starts_count.get(pid, 0) >= 2 or (seed_starts >= 5 and seed_rate >= 0.50)

        for gw in planning_gws:
            n_fix = len(club_gw_fixtures.get((cid, gw), []))
            if n_fix == 0:
                continue
            step = gw - int(target_gw)
            s_idx = min(max(step, 0), 5)
            native_m = float(native_mins_map.get((pid, gw), 0.0))

            if status == "u":
                soft_map[(pid, gw)] = 0.0
                hard_zero_keys.add((pid, gw))
            elif status == "n":
                if "parent club" in news.lower():
                    if step == 0:
                        soft_map[(pid, gw)] = 0.0
                        hard_zero_keys.add((pid, gw))
                else:
                    mult = SOFT_SUSPENDED_N_CURVE[s_idx]
                    if mult < 0.99:
                        val = native_m * mult
                        soft_map[(pid, gw)] = val
                        if val == 0.0:
                            hard_zero_keys.add((pid, gw))
            elif status == "s":
                if return_gw is not None:
                    if gw < return_gw:
                        soft_map[(pid, gw)] = 0.0
                        hard_zero_keys.add((pid, gw))
                    elif native_m < 45.0 * n_fix and has_tenure:
                        soft_map[(pid, gw)] = fit_mins * n_fix
                elif step == 0:
                    soft_map[(pid, gw)] = 0.0
                    hard_zero_keys.add((pid, gw))
            elif status == "i":
                if return_gw is not None:
                    if gw < return_gw:
                        soft_map[(pid, gw)] = 0.0
                        hard_zero_keys.add((pid, gw))
                    elif gw == return_gw:
                        if gw == int(target_gw) and chance <= 0.0:
                            soft_map[(pid, gw)] = 0.0
                            hard_zero_keys.add((pid, gw))
                        else:
                            soft_map[(pid, gw)] = min(20.0, fit_mins) * n_fix
                    elif gw == return_gw + 1:
                        soft_map[(pid, gw)] = min(65.0, fit_mins) * n_fix
                    elif native_m < 45.0 * n_fix and has_tenure:
                        soft_map[(pid, gw)] = fit_mins * n_fix
                else:
                    mult = SOFT_UNKNOWN_CURVE[s_idx]
                    val = native_m * mult
                    soft_map[(pid, gw)] = val
                    if val == 0.0:
                        hard_zero_keys.add((pid, gw))
            elif chance < 100.0:
                mult = 0.0 if (step == 0 and chance <= 0.0) else _soft_doubtful_mult(chance, step)
                if mult < 0.99:
                    val = native_m * mult
                    soft_map[(pid, gw)] = val
                    if val == 0.0:
                        hard_zero_keys.add((pid, gw))

    return soft_map, hard_zero_keys


def build_sparse_m1_map(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    native_mins_map: Mapping[tuple[int, int], float],
    seed_perfs: pd.DataFrame | None,
    seed_players: pd.DataFrame | None,
    reference_date: date,
) -> dict[tuple[int, int], float]:
    """Return M1 GKP role overrides ONLY for position_id == 1."""
    full_m1 = compute_internal_xmins_from_tables(
        df_players,
        df_fixtures,
        df_perfs,
        target_gw,
        horizon,
        native_mins_map=native_mins_map,
        seed_perfs=seed_perfs,
        seed_players=seed_players,
        reference_date=reference_date,
        config=M1_ONLY_CFG,
    )
    gk_ids = set(df_players[df_players["position_id"] == 1]["id"].astype(int))
    return {(pid, gw): val for (pid, gw), val in full_m1.items() if pid in gk_ids}


def build_sparse_m3_map(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    native_mins_map: Mapping[tuple[int, int], float],
    seed_perfs: pd.DataFrame | None,
    seed_players: pd.DataFrame | None,
    reference_date: date,
) -> dict[tuple[int, int], float]:
    """Return M3 availability & return ramp overrides ONLY for flagged players."""
    full_m3 = compute_internal_xmins_from_tables(
        df_players,
        df_fixtures,
        df_perfs,
        target_gw,
        horizon,
        native_mins_map=native_mins_map,
        seed_perfs=seed_perfs,
        seed_players=seed_players,
        reference_date=reference_date,
        config=M3_ONLY_CFG,
    )
    flagged_ids = {
        int(r["id"])
        for _, r in df_players.iterrows()
        if str(r.get("status", "a") or "a").lower() != "a"
        or (pd.notna(r.get("chance_of_playing_next_round")) and float(r["chance_of_playing_next_round"]) < 100.0)
    }
    return {(pid, gw): val for (pid, gw), val in full_m3.items() if pid in flagged_ids}


def _recompute_gkp_with_soft(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    soft_map: Mapping[tuple[int, int], float],
    m1_map: Mapping[tuple[int, int], float],
    seed_perfs: pd.DataFrame | None,
    seed_players: pd.DataFrame | None,
) -> dict[tuple[int, int], float]:
    """Merge M1 GKP role allocation with Soft Empirical Shield for flagged GKPs."""
    planning_gws = list(range(int(target_gw), int(target_gw) + max(1, int(horizon))))
    players = df_players[df_players["position_id"].isin((1, 2, 3, 4))].copy()
    players["id"] = players["id"].astype(int)
    players["club_id"] = players["club_id"].astype(int)
    players["position_id"] = players["position_id"].astype(int)
    hist = df_perfs[df_perfs["gameweek_id"] < int(target_gw)].copy() if not df_perfs.empty else pd.DataFrame()
    prior_starts: dict[int, int] = {}
    perf_lookup: dict[tuple[int, int], int] = {}
    if not hist.empty:
        starts_s = pd.to_numeric(hist.get("starts", 0), errors="coerce").fillna(0)
        for pid, fid, st in zip(hist["player_id"].astype(int), hist["fixture_id"].astype(int), starts_s):
            perf_lookup[(pid, fid)] = int(st)
        st_rows = hist[starts_s > 0]
        if not st_rows.empty:
            prior_starts = st_rows.groupby("player_id")["starts"].sum().astype(int).to_dict()

    seed_priors = _build_seed_priors(players, seed_perfs, seed_players)
    club_hist_fids = _build_club_fixture_history(df_fixtures, target_gw)
    club_gw_fixtures, _ = _extract_club_schedule(df_fixtures, planning_gws)

    out = dict(m1_map)
    gkps_by_club: dict[int, list[int]] = {}
    p_meta = {}
    for _, row in players[players["position_id"] == 1].iterrows():
        pid = int(row["id"])
        cid = int(row["club_id"])
        gkps_by_club.setdefault(cid, []).append(pid)
        p_meta[pid] = {
            "status": str(row.get("status", "a") or "a").lower(),
            "cost": float(row.get("now_cost", 45) or 45) / 10.0,
            "seed_starts": int(seed_priors.get(pid, (0.0, 0.0, 0))[2]),
        }

    for cid, gkps in gkps_by_club.items():
        hist_fids = club_hist_fids.get(cid, [])
        last2_fids = hist_fids[-2:] if len(hist_fids) >= 2 else []
        last6_fids = hist_fids[-6:]

        def gk_rank(pid: int) -> tuple[int, int, int, int, float]:
            handover = 1 if (last2_fids and all(perf_lookup.get((pid, f), 0) > 0 for f in last2_fids)) else 0
            s6 = sum(1 for f in last6_fids if perf_lookup.get((pid, f), 0) > 0)
            last1_missed = 1 if (
                len(last6_fids) >= 4
                and s6 >= 3
                and p_meta[pid]["status"] == "a"
                and perf_lookup.get((pid, last6_fids[-1]), 0) == 0
            ) else 0
            tot_s = prior_starts.get(pid, 0) + (int(p_meta[pid]["seed_starts"]) if len(hist_fids) < 3 else 0)
            return (handover, last1_missed, s6, tot_s, float(p_meta[pid]["cost"]))

        ranked = sorted(gkps, key=gk_rank, reverse=True)
        for gw in planning_gws:
            n_fix = len(club_gw_fixtures.get((cid, gw), []))
            if n_fix == 0:
                continue
            available = [pid for pid in ranked if soft_map.get((pid, gw), 89.0 * n_fix) > 0.0]
            for pid in gkps:
                out[(pid, gw)] = 0.0
            if available:
                gk1 = available[0]
                m1 = min(89.0 * n_fix, float(soft_map.get((gk1, gw), 89.0 * n_fix)))
                out[(gk1, gw)] = m1
                if len(available) > 1:
                    gk2 = available[1]
                    rem = max(1.0 * n_fix, 90.0 * n_fix - m1) if m1 < 88.5 * n_fix else 1.0 * n_fix
                    out[(gk2, gw)] = min(89.0 * n_fix, float(soft_map.get((gk2, gw), rem)), rem)
    return out


def build_soft_shield_m1_map(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    native_mins_map: Mapping[tuple[int, int], float],
    seed_perfs: pd.DataFrame | None,
    seed_players: pd.DataFrame | None,
    reference_date: date,
) -> dict[tuple[int, int], float]:
    """Sparse M1 GKP + Soft Empirical Shield on flagged outfield & flagged GKPs."""
    soft_map, _ = _soft_shield_details(
        df_players, df_fixtures, df_perfs, target_gw, horizon, native_mins_map, seed_perfs, seed_players, reference_date
    )
    m1_map = build_sparse_m1_map(
        df_players, df_fixtures, df_perfs, target_gw, horizon, native_mins_map, seed_perfs, seed_players, reference_date
    )
    gk_merged = _recompute_gkp_with_soft(
        df_players, df_fixtures, df_perfs, target_gw, horizon, soft_map, m1_map, seed_perfs, seed_players
    )
    return {**soft_map, **gk_merged}


def build_soft_m1_m3_m4_map(
    df_players: pd.DataFrame,
    df_fixtures: pd.DataFrame,
    df_perfs: pd.DataFrame,
    target_gw: int,
    horizon: int,
    native_mins_map: Mapping[tuple[int, int], float],
    seed_perfs: pd.DataFrame | None,
    seed_players: pd.DataFrame | None,
    reference_date: date,
) -> dict[tuple[int, int], float]:
    """Full-pool Soft Shield + M1 GKP + M4 capped outfield club reconciliation."""
    planning_gws = list(range(int(target_gw), int(target_gw) + max(1, int(horizon))))
    players = df_players[df_players["position_id"].isin((1, 2, 3, 4))].copy()
    players["id"] = players["id"].astype(int)
    players["club_id"] = players["club_id"].astype(int)
    players["position_id"] = players["position_id"].astype(int)

    soft_map, _ = _soft_shield_details(
        players, df_fixtures, df_perfs, target_gw, horizon, native_mins_map, seed_perfs, seed_players, reference_date
    )
    m1_map = build_sparse_m1_map(
        players, df_fixtures, df_perfs, target_gw, horizon, native_mins_map, seed_perfs, seed_players, reference_date
    )
    gk_merged = _recompute_gkp_with_soft(
        players, df_fixtures, df_perfs, target_gw, horizon, soft_map, m1_map, seed_perfs, seed_players
    )

    hist = df_perfs[df_perfs["gameweek_id"] < int(target_gw)].copy() if not df_perfs.empty else pd.DataFrame()
    prior_start_median: dict[int, float] = {}
    if not hist.empty:
        started_rows = hist[pd.to_numeric(hist.get("starts", 0), errors="coerce").fillna(0) > 0]
        if not started_rows.empty:
            prior_start_median = started_rows.groupby("player_id")["minutes"].median().astype(float).to_dict()

    club_gw_fixtures, _ = _extract_club_schedule(df_fixtures, planning_gws)
    club_players: dict[int, list[int]] = {}
    pos_of: dict[int, int] = {}
    flagged_pids: set[int] = set()
    for _, row in players.iterrows():
        pid = int(row["id"])
        cid = int(row["club_id"])
        pos_of[pid] = int(row["position_id"])
        club_players.setdefault(cid, []).append(pid)
        st = str(row.get("status", "a") or "a").lower()
        ch = row.get("chance_of_playing_next_round")
        if st != "a" or (pd.notna(ch) and float(ch) < 100.0):
            flagged_pids.add(pid)

    gw_totals: dict[tuple[int, int], float] = {(pid, gw): 0.0 for pid in pos_of for gw in planning_gws}
    cfg = FROZEN_CFG

    for cid, pids in club_players.items():
        outfield = [pid for pid in pids if pos_of[pid] in (2, 3, 4)]
        gkps = [pid for pid in pids if pos_of[pid] == 1]
        for gw in planning_gws:
            sched = club_gw_fixtures.get((cid, gw), [])
            n_fix = len(sched)
            if n_fix == 0:
                continue
            for pid in gkps:
                gw_totals[(pid, gw)] = float(gk_merged.get((pid, gw), 0.0))

            # Run capped outfield reconciliation per fixture, keeping Soft Shield rows fixed/capped
            fix_mins: dict[int, float] = {}
            for pid in outfield:
                if (pid, gw) in soft_map:
                    fix_mins[pid] = float(soft_map[(pid, gw)]) / n_fix
                else:
                    fix_mins[pid] = float(native_mins_map.get((pid, gw), 0.0)) / n_fix
                fix_mins[pid] = float(np.clip(fix_mins[pid], 0.0, 90.0))

            eligible = [
                pid for pid in outfield
                if pid not in flagged_pids and fix_mins[pid] >= cfg.reconcile_min_active_mins
            ]
            if eligible:
                caps = {}
                for pid in eligible:
                    pos_cap = cfg.outfield_cap_def if pos_of[pid] == 2 else cfg.outfield_cap_mid_fwd
                    p_med = prior_start_median.get(pid, pos_cap)
                    caps[pid] = min(90.0, max(pos_cap, p_med))
                fixed_sum = sum(fix_mins[pid] for pid in outfield if pid not in eligible)
                target_elig = max(0.0, cfg.outfield_club_target_mins - fixed_sum)
                cur_sum = sum(fix_mins[pid] for pid in eligible)
                if abs(target_elig - cur_sum) > 1.0:
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
                    for pid, val in vals.items():
                        fix_mins[pid] = val

            for pid in outfield:
                gw_totals[(pid, gw)] = fix_mins[pid] * n_fix

    return gw_totals


def _verify_state_preserving_parity() -> None:
    """Assert StatePreserving scaling exactness and <1e-9 unoverridden GW7 parity."""
    for tgt in (0.0, 10.0, 20.0, 45.0, 65.0, 72.0, 80.0, 89.0):
        pdnp, ps, psub, sm, subm, p60s, p60sub = scale_states_to_target(
            0.20, 0.65, 0.15, 78.0, 18.0, 0.85, 0.0, tgt
        )
        assert 0.0 <= pdnp <= 1.0 and 0.0 <= ps <= 1.0 and 0.0 <= psub <= 1.0
        assert abs(pdnp + ps + psub - 1.0) <= 1e-7
        assert 0.0 <= p60s <= 1.0 and 0.0 <= p60sub <= 1.0
        recovered = ps * sm + psub * subm
        assert abs(recovered - tgt) <= 0.05, f"tgt={tgt}, recovered={recovered}"

    parity_dir = CACHE_ROOT / "parity_check"
    parity_dir.mkdir(parents=True, exist_ok=True)
    try:
        manifest, seed_dir = stage_s1_inputs(parity_dir)
        deadlines = {int(o["gw"]): str(o["deadline_utc"]) for o in manifest["origins"]}
        gw7_dir = parity_dir / "verified_inputs/gw07"
        df_feat = build_features(
            gw7_dir,
            7,
            horizon=6,
            use_archive_seed=False,
            seed_processed_dir=seed_dir,
            as_of_gw=7,
            history_before_gw=7,
            target_deadline=deadlines[7],
            availability_snapshot_root=gw7_dir / "snapshots",
            season="2025-26",
            require_availability_snapshot=True,
            minutes_prior_source="seed_state",
        )
        hist = pd.read_parquet(gw7_dir / "player_performances.parquet")
        m_ref = DefXgShrinkChallengerModel()
        m_sp = StatePreservingDefXgShrinkModel()
        m_ref.fit(hist)
        m_sp.fit(hist)
        p_ref = m_ref.predict(df_feat, 6).sort_values(["player_id", "gameweek_id", "fixture_id"]).reset_index(drop=True)
        p_sp = m_sp.predict(df_feat, 6).sort_values(["player_id", "gameweek_id", "fixture_id"]).reset_index(drop=True)
        diff_pts = float((p_ref["projected_points"] - p_sp["projected_points"]).abs().max())
        diff_mins = float((p_ref["projected_minutes"] - p_sp["projected_minutes"]).abs().max())
        assert diff_pts < 1e-9, f"Points parity mismatch: {diff_pts}"
        assert diff_mins < 1e-9, f"Minutes parity mismatch: {diff_mins}"
        print(f"[parity check] PASS (max_abs_diff pts={diff_pts:.2e}, mins={diff_mins:.2e})", flush=True)
    finally:
        shutil.rmtree(parity_dir, ignore_errors=True)


def _apply_xmins_override(df_feat: pd.DataFrame, xmins_map: Mapping[tuple[int, int], float]) -> pd.DataFrame:
    out = df_feat.copy()
    valid_fix = out["fixture_id"].fillna(-1).astype(int) >= 0
    gw_fix_counts = out[valid_fix].groupby(["player_id", "gameweek_id"])["fixture_id"].transform("count")
    fix_count = pd.Series(1, index=out.index, dtype=int)
    fix_count.loc[valid_fix] = gw_fix_counts.astype(int)

    ext_vals: list[float] = []
    for pid, gw, fid, n_fix in zip(
        out["player_id"].astype(int),
        out["gameweek_id"].astype(int),
        out["fixture_id"].fillna(-1).astype(int),
        fix_count,
    ):
        if (pid, gw) in xmins_map:
            if fid < 0:
                ext_vals.append(0.0)
            else:
                per_fix = float(xmins_map[(pid, gw)]) / max(1, int(n_fix))
                ext_vals.append(min(90.0, max(0.0, per_fix)))
        else:
            ext_vals.append(float("nan"))
    out["external_xmins"] = ext_vals
    return out


def _bootstrap_meta_maps(season: str, gw: int) -> tuple[dict[int, str], dict[int, str]]:
    bp = ROOT / f"data/reports/empirical_mirrors/{season}/bootstraps/gw{gw:02d}.json.xz"
    payload = json.loads(lzma.open(bp, "rt", encoding="utf-8").read())
    news = {int(e["id"]): str(e.get("news") or "") for e in payload["elements"]}
    names = {int(e["id"]): str(e.get("web_name") or f"Player_{e['id']}") for e in payload["elements"]}
    return news, names


def _wide_from_long(wide_base: pd.DataFrame, projections: pd.DataFrame, targets: range) -> pd.DataFrame:
    wide = wide_base.copy()
    by_pg = projections.groupby(["player_id", "gameweek_id"])[["projected_points", "projected_minutes"]].sum()
    for target in targets:
        agg = by_pg.xs(target, level="gameweek_id")
        wide[f"{target}_Pts"] = wide["player_id"].map(agg["projected_points"]).astype(float)
        wide[f"{target}_xMins"] = wide["player_id"].map(agg["projected_minutes"]).astype(float)
        assert wide[f"{target}_Pts"].notna().all() and np.isfinite(wide[f"{target}_Pts"]).all()
        assert wide[f"{target}_xMins"].notna().all() and np.isfinite(wide[f"{target}_xMins"]).all()
    for col in ("player_id", "position_id", "club_id", "now_cost"):
        wide[col] = wide[col].astype(int)
    wide["purchase_eligible"] = wide["purchase_eligible"].astype(bool)
    return wide


def _build_gw_wide_arms(season: str, gw: int, deadline: str, seed_dir_str: str, arms: tuple[str, ...]) -> int:
    season_dir = CACHE_ROOT / season
    needed = [arm for arm in arms if not (season_dir / f"wide_{arm}" / f"gw{gw:02d}.parquet").is_file()]
    if not needed:
        return gw

    gw_dir = season_dir / "verified_inputs" / f"gw{gw:02d}"
    seed_dir = Path(seed_dir_str)
    horizon = min(DEFAULT_HORIZON, 39 - gw)
    targets = range(gw, gw + horizon)

    df_feat_base = build_features(
        gw_dir,
        gw,
        horizon,
        use_archive_seed=False,
        seed_processed_dir=seed_dir,
        as_of_gw=gw,
        history_before_gw=gw,
        target_deadline=deadline,
        availability_snapshot_root=gw_dir / "snapshots",
        season=season,
        require_availability_snapshot=True,
        minutes_prior_source="seed_state",
    )
    history = pd.read_parquet(gw_dir / "player_performances.parquet")
    if not history.empty:
        assert int(history["gameweek_id"].max()) < gw

    m_std = DefXgShrinkChallengerModel()
    m_std.fit(history)
    pred_l1 = m_std.predict(df_feat_base, horizon)
    agg_l1 = pred_l1.groupby(["player_id", "gameweek_id"])["projected_minutes"].sum()
    native_mins_map = {(int(pid), int(g)): float(val) for (pid, g), val in agg_l1.items()}

    m_sp = StatePreservingDefXgShrinkModel()
    if any(arm in SP_ARMS for arm in needed):
        m_sp.fit(history)

    snapshot = resolve_latest_snapshot(gw_dir / "snapshots", season, gw, deadline)
    assert snapshot is not None
    snap_players = cast(pd.DataFrame, snapshot["players"]).copy()
    snap_fixtures = cast(pd.DataFrame, snapshot["fixtures"]).copy()
    news_map, name_map = _bootstrap_meta_maps(season, gw)
    snap_players["news"] = snap_players["id"].astype(int).map(news_map).fillna("")
    snap_players["web_name"] = snap_players["id"].astype(int).map(name_map).fillna("Unknown")
    ref_date = datetime.fromisoformat(deadline).date()

    seed_perfs = pd.read_parquet(seed_dir / "player_performances.parquet")
    seed_players = pd.read_parquet(seed_dir / "players.parquet")

    wide_base = pd.read_parquet(
        gw_dir / "market.parquet",
        columns=["player_id", "position_id", "club_id", "now_cost", "purchase_eligible"],
    )

    m1_sparse: dict[tuple[int, int], float] | None = None
    m3_sparse: dict[tuple[int, int], float] | None = None
    soft_m1_map: dict[tuple[int, int], float] | None = None

    def get_m1() -> dict[tuple[int, int], float]:
        nonlocal m1_sparse
        if m1_sparse is None:
            m1_sparse = build_sparse_m1_map(
                snap_players, snap_fixtures, history, gw, horizon, native_mins_map, seed_perfs, seed_players, ref_date
            )
        return m1_sparse

    def get_m3() -> dict[tuple[int, int], float]:
        nonlocal m3_sparse
        if m3_sparse is None:
            m3_sparse = build_sparse_m3_map(
                snap_players, snap_fixtures, history, gw, horizon, native_mins_map, seed_perfs, seed_players, ref_date
            )
        return m3_sparse

    def get_soft_m1() -> dict[tuple[int, int], float]:
        nonlocal soft_m1_map
        if soft_m1_map is None:
            soft_m1_map = build_soft_shield_m1_map(
                snap_players, snap_fixtures, history, gw, horizon, native_mins_map, seed_perfs, seed_players, ref_date
            )
        return soft_m1_map

    for arm in needed:
        if arm == "L1_native":
            pred = pred_l1
        elif arm == "Sparse_M1_gkp":
            pred = m_std.predict(_apply_xmins_override(df_feat_base, get_m1()), horizon)
        elif arm == "Sparse_M1_M3":
            m3 = get_m3()
            m1 = get_m1()
            # M1 wins for GKPs unless M3 enforces hard 0.0
            merged = dict(m3)
            for k, v in m1.items():
                if k in m3 and m3[k] == 0.0:
                    merged[k] = 0.0
                else:
                    merged[k] = v
            pred = m_std.predict(_apply_xmins_override(df_feat_base, merged), horizon)
        elif arm == "Solo_M4_reconcile":
            m4_map = compute_internal_xmins_from_tables(
                snap_players, snap_fixtures, history, gw, horizon,
                native_mins_map=native_mins_map, seed_perfs=seed_perfs, seed_players=seed_players,
                reference_date=ref_date, config=M4_ONLY_CFG,
            )
            pred = m_std.predict(_apply_xmins_override(df_feat_base, m4_map), horizon)
        elif arm == "Soft_Shield_M1":
            pred = m_std.predict(_apply_xmins_override(df_feat_base, get_soft_m1()), horizon)
        elif arm == "SP_M1_M3_M4":
            sp_map = compute_internal_xmins_from_tables(
                snap_players, snap_fixtures, history, gw, horizon,
                native_mins_map=native_mins_map, seed_perfs=seed_perfs, seed_players=seed_players,
                reference_date=ref_date, config=FROZEN_CFG,
            )
            pred = m_sp.predict(_apply_xmins_override(df_feat_base, sp_map), horizon)
        elif arm == "SP_Soft_Shield_M1":
            pred = m_sp.predict(_apply_xmins_override(df_feat_base, get_soft_m1()), horizon)
        elif arm == "SP_Soft_M1_M3_M4":
            sp_soft_full = build_soft_m1_m3_m4_map(
                snap_players, snap_fixtures, history, gw, horizon, native_mins_map, seed_perfs, seed_players, ref_date
            )
            pred = m_sp.predict(_apply_xmins_override(df_feat_base, sp_soft_full), horizon)
        else:
            raise ValueError(f"Unknown arm: {arm}")

        out_path = season_dir / f"wide_{arm}" / f"gw{gw:02d}.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _wide_from_long(wide_base, pred, targets).to_parquet(out_path, index=False)

    return gw


def prepare_season(season: str, arms: tuple[str, ...]) -> dict[str, Any]:
    season_dir = CACHE_ROOT / season
    meta_path = season_dir / "meta.json"
    all_ready = meta_path.is_file() and all(
        (season_dir / f"wide_{arm}" / f"gw{gw:02d}.parquet").is_file()
        for arm in arms
        for gw in range(1, 39)
    )
    if all_ready:
        return json.loads(meta_path.read_text(encoding="utf-8"))

    season_dir.mkdir(parents=True, exist_ok=True)
    manifest, seed_dir = stage_s1_inputs(season_dir) if season == "2025-26" else stage_s2_inputs(season_dir)
    anchor = solve_ownership_anchor(
        pd.read_parquet(season_dir / "verified_inputs/gw01/market.parquet"),
        season,
        gameweek=1,
        anchor_type="opening",
        schema=UniverseSchema(eligibility_col="purchase_eligible"),
    )
    deadlines = {int(o["gw"]): str(o["deadline_utc"]) for o in manifest["origins"]}
    calendar = [[int(r["gameweek"]), str(r["chip"])] for r in manifest["shared_chip_calendar"]]

    max_workers = min(8, os.cpu_count() or 4)
    print(f"[{season}] Precomputing GW1-38 wide forecasts for {len(arms)} arm(s) (workers={max_workers})...", flush=True)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futs = [
            executor.submit(_build_gw_wide_arms, season, gw, deadlines[gw], str(seed_dir), arms)
            for gw in range(1, 39)
        ]
        done = 0
        for fut in as_completed(futs):
            fut.result()
            done += 1
            if done % 10 == 0 or done == 38:
                print(f"[{season}] Wide forecasts {done}/38 ready", flush=True)

    meta = {"season": season, "anchor": anchor.to_dict(), "chip_calendar": calendar}
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return meta


def compute_accuracy_from_wide(season: str, arm: str) -> dict[str, float]:
    """Compute t=0 and t=0..2 minutes & xP accuracy from wide forecasts against actuals."""
    season_dir = CACHE_ROOT / season
    proc = ROOT / f"data/archive/{season}/processed"
    perfs = pd.read_parquet(proc / "player_performances.parquet")
    actual = perfs.groupby(["player_id", "gameweek_id"], as_index=False).agg(
        act_mins=("minutes", "sum"),
        act_pts=("total_points", "sum"),
    )
    fixtures = pd.read_parquet(proc / "fixtures.parquet")
    club_active_gws: dict[int, set[int]] = defaultdict(set)
    for _, r in fixtures.iterrows():
        gw = int(r["gameweek_id"])
        club_active_gws[int(r["home_club_id"])].add(gw)
        club_active_gws[int(r["away_club_id"])].add(gw)

    t0_frames = []
    t02_frames = []
    for gw in range(1, 39):
        w = pd.read_parquet(season_dir / f"wide_{arm}" / f"gw{gw:02d}.parquet")
        horizon = min(DEFAULT_HORIZON, 39 - gw)
        for tgw in range(gw, min(gw + 3, gw + horizon)):
            active_clubs = {cid for cid, gws in club_active_gws.items() if tgw in gws}
            sub = w[w["club_id"].isin(active_clubs)][["player_id", f"{tgw}_xMins", f"{tgw}_Pts"]].copy()
            sub = sub.rename(columns={f"{tgw}_xMins": "pred_mins", f"{tgw}_Pts": "pred_pts"})
            act_sub = actual[actual["gameweek_id"] == tgw][["player_id", "act_mins", "act_pts"]]
            sub = sub.merge(act_sub, on="player_id", how="left")
            sub["act_mins"] = sub["act_mins"].fillna(0.0)
            sub["act_pts"] = sub["act_pts"].fillna(0.0)
            if tgw == gw:
                t0_frames.append(sub)
            t02_frames.append(sub)

    df0 = pd.concat(t0_frames, ignore_index=True)
    df02 = pd.concat(t02_frames, ignore_index=True)
    err0_m = df0["pred_mins"] - df0["act_mins"]
    err0_p = df0["pred_pts"] - df0["act_pts"]
    err02_m = df02["pred_mins"] - df02["act_mins"]
    return {
        "t0_mins_mae": float(np.mean(np.abs(err0_m))),
        "t0_mins_bias": float(np.mean(err0_m)),
        "t02_mins_mae": float(np.mean(np.abs(err02_m))),
        "t0_xp_mae": float(np.mean(np.abs(err0_p))),
        "t0_xp_rmse": float(np.sqrt(np.mean(err0_p ** 2))),
    }


def run_replay_task(season: str, arm: str) -> dict[str, Any]:
    season_dir = CACHE_ROOT / season
    meta = json.loads((season_dir / "meta.json").read_text(encoding="utf-8"))
    anchor = OwnershipAnchor.from_dict(meta["anchor"])
    calendar = tuple((int(g), str(c)) for g, c in meta["chip_calendar"])
    wide_by_gw = {gw: pd.read_parquet(season_dir / f"wide_{arm}" / f"gw{gw:02d}.parquet") for gw in range(1, 39)}
    outcomes_by_gw = {gw: _outcomes_for_gw(season, gw) for gw in range(1, 39)}

    cp_dir = season_dir / "checkpoints" / arm
    t0 = time.perf_counter()
    traj = run_rolling_replay(
        arm,
        season,
        anchor,
        lambda gw, _state: wide_by_gw[gw],
        lambda gw: outcomes_by_gw[gw],
        horizon=DEFAULT_HORIZON,
        end_gw=38,
        solve_fn=native_strategic_solve,
        policy=QualityPolicy(mode="certified", target_gap=0.0, time_limit_seconds=DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS),
        checkpoint_dir=cp_dir,
        model_version_hash=f"ablation-v1-{arm}",
        protocol_hash=f"{season}-strategic-h6",
        chip_calendar=cast(Any, calendar),
    )
    elapsed = round(time.perf_counter() - t0, 2)
    net_audit = traj.audit_reconstructed_net_score()
    assert len(traj.records) == 38
    assert all(r.execution_status == "SUCCESS" for r in traj.records)

    optimal_gws = sum(1 for r in traj.records if r.certificate.termination_status == "OPTIMAL")
    total_transfers = sum(len(r.decision.transfers) for r in traj.records)
    hit_count = sum(int(r.hit_penalty // 4) for r in traj.records)
    gw1_4_net = sum(r.net_points for r in traj.records if 1 <= r.deadline <= 4)
    gw5_19_net = sum(r.net_points for r in traj.records if 5 <= r.deadline <= 19)
    gw20_38_net = sum(r.net_points for r in traj.records if 20 <= r.deadline <= 38)

    acc = compute_accuracy_from_wide(season, arm)
    print(
        f"[{season} | {arm}] DONE in {elapsed:.1f}s | net={net_audit} (hits={traj.cumulative_hits}) "
        f"| t0_MAE={acc['t0_mins_mae']:.3f} t02_MAE={acc['t02_mins_mae']:.3f} | opt={optimal_gws}/38",
        flush=True,
    )
    return {
        "season": season,
        "arm": arm,
        "t0_mins_mae": round(acc["t0_mins_mae"], 4),
        "t0_mins_bias": round(acc["t0_mins_bias"], 4),
        "t02_mins_mae": round(acc["t02_mins_mae"], 4),
        "t0_xp_mae": round(acc["t0_xp_mae"], 4),
        "t0_xp_rmse": round(acc["t0_xp_rmse"], 4),
        "cumulative_gross": int(traj.cumulative_gross),
        "cumulative_hits": int(traj.cumulative_hits),
        "cumulative_net": int(net_audit),
        "total_transfers": int(total_transfers),
        "hit_count": int(hit_count),
        "final_bank": int(traj.final_bank),
        "gw1_4_net": int(gw1_4_net),
        "gw5_19_net": int(gw5_19_net),
        "gw20_38_net": int(gw20_38_net),
        "optimal_gws": int(optimal_gws),
        "runtime_seconds": elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2025-26", choices=("2025-26", "2024-25"))
    parser.add_argument("--arms", default=",".join(ALL_ARMS))
    parser.add_argument("--out-csv", default="")
    parser.add_argument("--keep-cache", action="store_true")
    parser.add_argument("--skip-parity", action="store_true")
    args = parser.parse_args()

    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    if not args.skip_parity:
        _verify_state_preserving_parity()

    prepare_season(args.season, arms)

    print(f"\n[{args.season}] Launching {len(arms)} certified 38-GW Strategic rolling replays (workers<=4)...", flush=True)
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as executor:
        futs = [executor.submit(run_replay_task, args.season, arm) for arm in arms]
        for fut in as_completed(futs):
            rows.append(fut.result())

    df = pd.DataFrame(rows)
    native_rows = df[df["arm"] == "L1_native"]
    native_net = int(native_rows.iloc[0]["cumulative_net"]) if not native_rows.empty else 0
    shield_net = int(SHIELD_REFERENCE_NET[args.season])
    df["delta_net_vs_native"] = df["cumulative_net"] - native_net
    df["delta_net_vs_shield"] = df["cumulative_net"] - shield_net

    arm_order = {a: i for i, a in enumerate(arms)}
    df["_ord"] = df["arm"].map(lambda a: arm_order.get(a, 999))
    df = df.sort_values("_ord").drop(columns=["_ord"]).reset_index(drop=True)

    cols = [
        "season", "arm", "t0_mins_mae", "t0_mins_bias", "t02_mins_mae", "t0_xp_mae", "t0_xp_rmse",
        "cumulative_gross", "cumulative_hits", "cumulative_net", "delta_net_vs_native", "delta_net_vs_shield",
        "total_transfers", "hit_count", "final_bank", "gw1_4_net", "gw5_19_net", "gw20_38_net",
        "optimal_gws", "runtime_seconds",
    ]
    df = df[cols]
    out_csv = Path(args.out_csv) if args.out_csv else (OUT_DIR / "s1_replay_ablation.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"\n=== {args.season} REPLAY ABLATION SUMMARY -> {out_csv} ===")
    print(df.to_string(index=False))

    if not args.keep_cache and CACHE_ROOT.exists():
        shutil.rmtree(CACHE_ROOT)


if __name__ == "__main__":
    main()
