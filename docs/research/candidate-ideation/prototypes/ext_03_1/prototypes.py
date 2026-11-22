"""EXT-03_1: club substitution timing contrast for unfamiliar reserves."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_APPEARANCE_KEY = ["player_id", "fixture_id"]
_FIXTURE_FIELDS = ["player_id", "fixture_id", "gameweek_id", "opponent_club_id"]
_HISTORY_COLUMNS = [*_FIXTURE_FIELDS, "starts", "minutes"]
_OUTFIELD_POSITIONS = frozenset({2, 3, 4})
_SHRINK_CLUB_CAMEOS = 12.0
_SHRINK_PLAYER_CAMEOS = 4.0


def _recover_club_cameos(history_df: pd.DataFrame) -> pd.DataFrame:
    """Recover historical own_club from complete two-sided fixtures, then filter cameos."""
    if history_df.empty or not set(_HISTORY_COLUMNS).issubset(history_df.columns):
        return pd.DataFrame(columns=[*_HISTORY_COLUMNS, "club_id"])

    history = history_df[_HISTORY_COLUMNS].apply(pd.to_numeric, errors="coerce")
    history = history.replace([np.inf, -np.inf], np.nan)
    valid_keys = history[_FIXTURE_FIELDS].fillna(0).gt(0).all(axis=1)
    history = history.loc[valid_keys].drop_duplicates().reset_index(drop=True)
    if history.empty:
        return pd.DataFrame(columns=[*_HISTORY_COLUMNS, "club_id"])

    # Recover own_club across all completed rows before filtering cameos.
    appearances = history.groupby(_APPEARANCE_KEY)["opponent_club_id"]
    conflicting_sides = appearances.transform("nunique").gt(1)
    conflicting_fixtures = history.loc[conflicting_sides, "fixture_id"]
    fixtures = history.groupby("fixture_id")
    sides = fixtures["opponent_club_id"]
    complete = (
        sides.transform("nunique").eq(2)
        & fixtures["gameweek_id"].transform("nunique").eq(1)
        & ~history["fixture_id"].isin(conflicting_fixtures)
    )
    lower_club = sides.transform("min")
    own_club = sides.transform("max").where(
        history["opponent_club_id"].eq(lower_club), lower_club
    )
    recovered = history.loc[complete].assign(club_id=own_club)
    unique_rows = recovered.drop_duplicates(subset=_APPEARANCE_KEY, keep=False)
    cameos = unique_rows.loc[
        unique_rows["starts"].eq(0)
        & unique_rows["minutes"].gt(0)
        & unique_rows["minutes"].le(90)
    ].copy()
    return cameos.reset_index(drop=True)


def _group_sum_count(
    frame: pd.DataFrame, keys: list[str]
) -> dict[object, tuple[float, int]]:
    grouped = frame.groupby(keys)["minutes"]
    sums = grouped.sum()
    counts = grouped.count()
    return {
        key: (float(sums.at[key]), int(counts.at[key])) for key in sums.index
    }


class ClubSubstitutionTimingReservesModel(DefXgShrinkChallengerModel):
    """Adjust xmins_if_sub_in via leave-player-out club cameo timing contrast."""

    variant_name: str = "ext_03_1_a05"
    a: float = 0.5

    def __init__(self) -> None:
        super().__init__()
        self._cameo_hist: pd.DataFrame = pd.DataFrame(
            columns=[*_HISTORY_COLUMNS, "club_id"]
        )

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._cameo_hist = _recover_club_cameos(history_df)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if (
            features_df.empty
            or self._cameo_hist.empty
            or not {
                "player_id",
                "club_id",
                "position_id",
                "xmins_if_sub_in",
                "p_60_if_sub_in",
            }.issubset(features_df.columns)
        ):
            return super().predict(features_df, horizon)

        target_gw = resolve_asof_target_gw(features_df, self._raw_history)
        prior_cameos = self._cameo_hist.loc[
            self._cameo_hist["gameweek_id"].lt(target_gw)
        ]
        if prior_cameos.empty:
            return super().predict(features_df, horizon)

        feat_meta = features_df[["player_id", "position_id"]].copy()
        feat_meta["player_id"] = pd.to_numeric(feat_meta["player_id"], errors="coerce")
        feat_meta["position_id"] = pd.to_numeric(
            feat_meta["position_id"], errors="coerce"
        )
        feat_meta = feat_meta.dropna(
            subset=["player_id", "position_id"]
        ).drop_duplicates(subset=["player_id"])
        positions = {
            int(pid): int(pos)
            for pid, pos in zip(
                feat_meta["player_id"], feat_meta["position_id"], strict=True
            )
            if pos in _OUTFIELD_POSITIONS
        }
        if not positions:
            return super().predict(features_df, horizon)

        cameos = prior_cameos.assign(
            player_id=prior_cameos["player_id"].astype(int),
            club_id=prior_cameos["club_id"].astype(int),
        )
        cameos["position_id"] = cameos["player_id"].map(positions)
        cameos = cameos.dropna(subset=["position_id"]).copy()
        if cameos.empty:
            return super().predict(features_df, horizon)
        cameos["position_id"] = cameos["position_id"].astype(int)

        pos_stats = _group_sum_count(cameos, ["position_id"])
        club_pos_stats = _group_sum_count(cameos, ["club_id", "position_id"])
        player_pos_stats = _group_sum_count(cameos, ["player_id", "position_id"])
        player_club_pos_stats = _group_sum_count(
            cameos, ["player_id", "club_id", "position_id"]
        )

        features = features_df.copy()
        u_vals = pd.to_numeric(features["xmins_if_sub_in"], errors="coerce").to_numpy(
            dtype=float
        )
        q_vals = pd.to_numeric(features["p_60_if_sub_in"], errors="coerce").to_numpy(
            dtype=float
        )
        pid_vals = pd.to_numeric(features["player_id"], errors="coerce").to_numpy(
            dtype=float
        )
        cid_vals = pd.to_numeric(features["club_id"], errors="coerce").to_numpy(
            dtype=float
        )
        pos_vals = pd.to_numeric(features["position_id"], errors="coerce").to_numpy(
            dtype=float
        )
        out_u = features["xmins_if_sub_in"].tolist()

        for row_idx in range(len(features)):
            raw_pid = pid_vals[row_idx]
            raw_cid = cid_vals[row_idx]
            raw_pos = pos_vals[row_idx]
            u_val = float(u_vals[row_idx])
            q_val = float(q_vals[row_idx])
            if (
                not (
                    math.isfinite(raw_pid)
                    and math.isfinite(raw_cid)
                    and math.isfinite(raw_pos)
                    and math.isfinite(u_val)
                    and math.isfinite(q_val)
                )
                or not 0.0 <= q_val <= 1.0
            ):
                continue
            pid = int(raw_pid)
            cid = int(raw_cid)
            pos = int(raw_pos)
            if pos not in _OUTFIELD_POSITIONS:
                continue

            low = 1.0 + 59.0 * q_val
            high = 59.0 + 31.0 * q_val
            if not (low <= u_val <= high):
                continue

            p_sum, p_cnt = pos_stats.get(pos, (0.0, 0))
            cp_sum, cp_cnt = club_pos_stats.get((cid, pos), (0.0, 0))
            ip_sum, ip_cnt = player_pos_stats.get((pid, pos), (0.0, 0))
            icp_sum, icp_cnt = player_club_pos_stats.get((pid, cid, pos), (0.0, 0))

            n = cp_cnt - icp_cnt
            l_cnt = p_cnt - cp_cnt - (ip_cnt - icp_cnt)
            if n <= 0 or l_cnt <= 0:
                continue

            t_sum = cp_sum - icp_sum
            l_sum = p_sum - cp_sum - (ip_sum - icp_sum)
            l_mean = l_sum / float(l_cnt)
            d = (t_sum - float(n) * l_mean) / (float(n) + _SHRINK_CLUB_CAMEOS)
            if not math.isfinite(d) or d == 0.0:
                continue

            h = float(icp_cnt)
            shift = self.a * d * (_SHRINK_PLAYER_CAMEOS / (_SHRINK_PLAYER_CAMEOS + h))
            out_u[row_idx] = min(high, max(low, u_val + shift))

        features["xmins_if_sub_in"] = out_u
        return super().predict(features, horizon)


_GRID = (("ext_03_1_a05", 0.5), ("ext_03_1_a10", 1.0))
PROTOTYPES = {
    name: type(
        name,
        (ClubSubstitutionTimingReservesModel,),
        {"variant_name": name, "a": a},
    )
    for name, a in _GRID
}
_MANIFEST = (
    "features.player_id",
    "features.club_id",
    "features.position_id",
    "features.xmins_if_sub_in",
    "features.p_60_if_sub_in",
    "history.player_id",
    "history.fixture_id",
    "history.gameweek_id",
    "history.opponent_club_id",
    "history.starts",
    "history.minutes",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
COMPONENTS = {name: "xp_minutes" for name in PROTOTYPES}
