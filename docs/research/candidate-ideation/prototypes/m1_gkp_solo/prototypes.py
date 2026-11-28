"""Pure point-in-time history M1 GKP solo Layer 1 prototype (zero API status/chance/news).

Applies discrete club GKP #1/#2 (89m/1m) role allocation with 2-start available-rival
handover and 1-game incumbent retention strictly from `< target_gw` match history and
as-of player metadata (`now_cost`, `n_starts_historical`), routing target minutes via
`scale_states_to_target` while leaving all outfielders identical to `DefXgShrinkChallengerModel`.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.face_value_challenger import FaceValueChallengerModel
from models.learned_start_challenger import (
    blend_states,
    learned_start_probabilities,
    target_start_probabilities,
)
from models.metrics_component_hybrid import _number
from models.participation_state_hybrid import (
    _validate_oracle_state_columns,
    scale_states_to_target,
)

_GKP_POS = 1
_APPEARANCE_KEY = ["player_id", "fixture_id"]
_FIXTURE_FIELDS = ["player_id", "fixture_id", "gameweek_id", "opponent_club_id"]
_HISTORY_COLUMNS = [*_FIXTURE_FIELDS, "starts", "minutes"]
_REQUIRED_FEATURE_COLUMNS = frozenset({"player_id", "club_id", "position_id", "fixture_id", "gameweek_id"})
_RECENT_WINDOW = 6
_SEED_FALLBACK_FIXTURES = 3


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _recover_causal_club_history(
    history_df: pd.DataFrame,
    target_gw: int,
) -> tuple[
    dict[int, list[int]],
    dict[tuple[int, int], tuple[float, int]],
    dict[int, int],
    dict[int, int],
]:
    """Recover ordered club fixture IDs and prior GKP/player counts strictly before `target_gw`."""
    if history_df.empty or not set(_HISTORY_COLUMNS).issubset(history_df.columns):
        return {}, {}, {}, {}

    hist = history_df[_HISTORY_COLUMNS].apply(pd.to_numeric, errors="coerce")
    hist = hist.replace([np.inf, -np.inf], np.nan)
    valid = hist[_FIXTURE_FIELDS].fillna(0).gt(0).all(axis=1) & hist["gameweek_id"].lt(int(target_gw))
    hist = hist.loc[valid].drop_duplicates().reset_index(drop=True)
    if hist.empty:
        return {}, {}, {}, {}

    hist["minutes"] = hist["minutes"].fillna(0.0).clip(lower=0.0)
    hist["starts"] = hist["starts"].fillna(0.0).clip(lower=0.0)

    # Deduplicate per (player_id, fixture_id) before indexing prior performances.
    appearances = hist.groupby(_APPEARANCE_KEY)["opponent_club_id"]
    conflicting_sides = appearances.transform("nunique").gt(1)
    conflicting_fixtures = hist.loc[conflicting_sides, "fixture_id"]
    unique_rows = hist.loc[~hist["fixture_id"].isin(conflicting_fixtures)].drop_duplicates(
        subset=_APPEARANCE_KEY, keep="last"
    )

    perf_lookup: dict[tuple[int, int], tuple[float, int]] = {}
    prior_starts_count: dict[int, int] = {}
    current_apps_count: dict[int, int] = {}
    for row in unique_rows.itertuples(index=False):
        pid = int(row.player_id)
        fid = int(row.fixture_id)
        mins = float(row.minutes)
        st = int(row.starts > 0)
        perf_lookup[(pid, fid)] = (mins, st)
        if st > 0:
            prior_starts_count[pid] = prior_starts_count.get(pid, 0) + st
        if mins > 0.0:
            current_apps_count[pid] = current_apps_count.get(pid, 0) + 1

    fixtures = unique_rows.groupby("fixture_id")
    sides = fixtures["opponent_club_id"]
    complete = sides.transform("nunique").eq(2) & fixtures["gameweek_id"].transform("nunique").eq(1)
    recovered = unique_rows.loc[complete]
    if recovered.empty:
        return {}, perf_lookup, prior_starts_count, current_apps_count

    lower_club = recovered.groupby("fixture_id")["opponent_club_id"].transform("min")
    own_club = recovered.groupby("fixture_id")["opponent_club_id"].transform("max").where(
        recovered["opponent_club_id"].eq(lower_club), lower_club
    )
    club_fx = (
        recovered.assign(club_id=own_club)[["club_id", "gameweek_id", "fixture_id"]]
        .drop_duplicates()
        .sort_values(["club_id", "gameweek_id", "fixture_id"], kind="stable")
    )
    club_hist_fids: dict[int, list[int]] = {}
    for row in club_fx.itertuples(index=False):
        club_hist_fids.setdefault(int(row.club_id), []).append(int(row.fixture_id))
    return club_hist_fids, perf_lookup, prior_starts_count, current_apps_count


def _rank_club_gkps_pure_history(
    gkps: list[int],
    hist_fids: list[int],
    perf_lookup: dict[tuple[int, int], tuple[float, int]],
    prior_starts_count: dict[int, int],
    seed_starts_map: dict[int, int],
    cost_map: dict[int, float],
    handover_starts: int,
) -> list[int]:
    """Order club GKPs by 2-start handover, 1-game retention, 6-GW form, cumulative starts, price."""
    last2_fids = hist_fids[-handover_starts:] if handover_starts > 0 and len(hist_fids) >= handover_starts else []
    last6_fids = hist_fids[-_RECENT_WINDOW:]

    def rank_key(pid: int) -> tuple[int, int, int, int, float, int]:
        handover = 1 if (last2_fids and all(perf_lookup.get((pid, f), (0.0, 0))[1] > 0 for f in last2_fids)) else 0
        s6 = sum(1 for f in last6_fids if perf_lookup.get((pid, f), (0.0, 0))[1] > 0)
        last1_missed = (
            1
            if (len(last6_fids) >= 4 and s6 >= 3 and perf_lookup.get((pid, last6_fids[-1]), (0.0, 0))[1] == 0)
            else 0
        )
        tot_s = prior_starts_count.get(pid, 0) + (
            seed_starts_map.get(pid, 0) if len(hist_fids) < _SEED_FALLBACK_FIXTURES else 0
        )
        return (handover, last1_missed, s6, tot_s, cost_map.get(pid, 4.5), -pid)

    return sorted(gkps, key=rank_key, reverse=True)


def _compute_pure_history_gkp_targets(
    features_df: pd.DataFrame,
    history_df: pd.DataFrame,
    target_gw: int,
    *,
    clear_starter_mins: float,
    backup_mins: float,
    handover_starts: int,
) -> dict[int, float]:
    """Return `player_id -> discrete target minutes` (`89/1/0`) for all club GKPs."""
    gkp_mask = pd.to_numeric(features_df["position_id"], errors="coerce").eq(_GKP_POS)
    gkp_rows = features_df.loc[gkp_mask]
    if gkp_rows.empty:
        return {}

    min_feat_gw = int(pd.to_numeric(features_df["gameweek_id"]).min())
    cutoff_gw = min(int(target_gw), min_feat_gw)
    club_hist_fids, perf_lookup, prior_starts_count, current_apps_count = _recover_causal_club_history(
        history_df, cutoff_gw
    )

    gkps_by_club: dict[int, list[int]] = {}
    seed_starts_map: dict[int, int] = {}
    cost_map: dict[int, float] = {}
    seen_pids: set[int] = set()
    for _, row in gkp_rows.iterrows():
        raw_pid = row["player_id"]
        raw_cid = row["club_id"]
        if pd.isna(raw_pid) or pd.isna(raw_cid):
            continue
        pid = int(raw_pid)
        if pid in seen_pids:
            continue
        seen_pids.add(pid)
        cid = int(raw_cid)
        gkps_by_club.setdefault(cid, []).append(pid)

        raw_cost = _number(row, "now_cost", 45.0)
        cost_map[pid] = float(raw_cost) / 10.0 if math.isfinite(raw_cost) else 4.5
        n_hist = _number(row, "n_starts_historical", 0.0)
        curr_apps = float(current_apps_count.get(pid, 0))
        seed_starts_map[pid] = max(0, round(max(0.0, n_hist) - curr_apps))

    targets: dict[int, float] = {}
    for cid, pids in gkps_by_club.items():
        ranked = _rank_club_gkps_pure_history(
            pids,
            club_hist_fids.get(cid, []),
            perf_lookup,
            prior_starts_count,
            seed_starts_map,
            cost_map,
            handover_starts,
        )
        for rank_idx, pid in enumerate(ranked):
            if rank_idx == 0:
                targets[pid] = float(clear_starter_mins)
            elif rank_idx == 1:
                targets[pid] = float(backup_mins)
            else:
                targets[pid] = 0.0
    return targets


class PureHistoryM1GkpModel(DefXgShrinkChallengerModel):
    """Confirmed Champion plus pure point-in-time history M1 GKP solo allocation via `scale_states_to_target`."""

    variant_name: str = "m1_gkp_solo"
    clear_starter_mins: float = 89.0
    backup_mins: float = 1.0
    handover_starts: int = 2

    def __init__(self) -> None:
        super().__init__()
        self._m1_gkp_states: dict[tuple[int, int], tuple[float, float, float]] = {}

    @property
    def name(self) -> str:
        return self.variant_name

    def _state_probabilities(self, row: pd.Series) -> tuple[float, float, float]:
        if self._m1_gkp_states and int(_number(row, "position_id", 0.0)) == _GKP_POS:
            fixture = row.get("fixture_id")
            if fixture is not None and not pd.isna(fixture):
                override = self._m1_gkp_states.get((int(row["player_id"]), int(fixture)))
                if override is not None:
                    return override
        return super()._state_probabilities(row)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if (
            features_df.empty
            or _validate_oracle_state_columns(features_df)
            or not _REQUIRED_FEATURE_COLUMNS.issubset(features_df.columns)
        ):
            return super().predict(features_df, horizon)

        target_gw = resolve_asof_target_gw(features_df, self._raw_history)
        gkp_targets = _compute_pure_history_gkp_targets(
            features_df,
            self._raw_history,
            target_gw,
            clear_starter_mins=self.clear_starter_mins,
            backup_mins=self.backup_mins,
            handover_starts=self.handover_starts,
        )
        if not gkp_targets:
            return super().predict(features_df, horizon)

        p_target_map = target_start_probabilities(
            features_df,
            learned_start_probabilities(self._raw_history, features_df),
            target_gw=target_gw,
        )

        features = features_df.copy()
        for col, default in (
            ("xmins_if_start", 78.0),
            ("xmins_if_sub_in", 18.0),
            ("p_60_if_start", 1.0),
            ("p_60_if_sub_in", 0.0),
        ):
            if col not in features.columns:
                features[col] = default
            else:
                features[col] = pd.to_numeric(features[col], errors="coerce").astype(float)

        gkp_states: dict[tuple[int, int], tuple[float, float, float]] = {}
        for idx, row in features.iterrows():
            if int(_number(row, "position_id", 0.0)) != _GKP_POS:
                continue
            raw_fid = row.get("fixture_id")
            if raw_fid is None or pd.isna(raw_fid):
                continue
            fid = int(raw_fid)
            if fid < 0:
                continue
            pid = int(row["player_id"])
            if pid not in gkp_targets:
                continue

            p_dnp, p_start, p_sub = FaceValueChallengerModel._state_probabilities(row)
            p_learn = p_target_map.get((pid, fid))
            if p_learn is not None:
                p_dnp, p_start, p_sub = blend_states(p_dnp, p_start, p_sub, p_learn)

            start_mins = max(0.0, _number(row, "xmins_if_start", 78.0))
            sub_mins = max(0.0, _number(row, "xmins_if_sub_in", 18.0))
            p60_s = _clamp01(_number(row, "p_60_if_start", (start_mins - 45.0) / 30.0))
            p60_sub = _clamp01(_number(row, "p_60_if_sub_in", (sub_mins - 45.0) / 30.0))

            s_dnp, s_start, s_sub, s_sm, s_subm, s_p60s, s_p60sub = scale_states_to_target(
                p_dnp,
                p_start,
                p_sub,
                start_mins,
                sub_mins,
                p60_s,
                p60_sub,
                gkp_targets[pid],
            )
            gkp_states[(pid, fid)] = (s_dnp, s_start, s_sub)
            features.at[idx, "xmins_if_start"] = s_sm
            features.at[idx, "xmins_if_sub_in"] = s_subm
            features.at[idx, "p_60_if_start"] = s_p60s
            features.at[idx, "p_60_if_sub_in"] = s_p60sub

        self._m1_gkp_states = gkp_states
        try:
            return super().predict(features, horizon)
        finally:
            self._m1_gkp_states = {}


PROTOTYPES = {
    "m1_gkp_solo": PureHistoryM1GkpModel,
}
FEATURES = {
    "m1_gkp_solo": (
        "features.player_id",
        "features.club_id",
        "features.position_id",
        "features.fixture_id",
        "features.gameweek_id",
        "features.now_cost",
        "features.n_starts_historical",
        "features.p_start",
        "features.p_sub_in",
        "features.p_dnp",
        "features.xmins_if_start",
        "features.xmins_if_sub_in",
        "features.p_60_if_start",
        "features.p_60_if_sub_in",
        "history.player_id",
        "history.fixture_id",
        "history.gameweek_id",
        "history.opponent_club_id",
        "history.starts",
        "history.minutes",
    ),
}
COMPONENTS = {
    "m1_gkp_solo": "xp_minutes",
}
