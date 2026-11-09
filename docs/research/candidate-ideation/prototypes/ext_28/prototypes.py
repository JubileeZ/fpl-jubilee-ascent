from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import (
    DefXgShrinkChallengerModel,
    _POSITION_K,
    _RATIO_CLIP,
    shrunk_xg_rates,
)

_DEFENDER = 2
_MIDFIELDER = 3
_FORWARD = 4


class _BaseEXT28(DefXgShrinkChallengerModel):
    variant_name: str = ""
    phi: float = 0.75
    mode: str = "all"

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        cols = ["player_id", "gameweek_id", "minutes", "expected_goals", "opponent_club_id"]
        if not history_df.empty and set(cols).issubset(history_df.columns):
            hist = history_df[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
            self._xg_hist = hist[hist["minutes"] > 0]

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._xg_hist.empty:
            return super().predict(features_df, horizon)

        hist = self._xg_hist.copy()
        if "opponent_club_id" in hist.columns and "expected_goals" in hist.columns:
            tot_xg = hist["expected_goals"].sum()
            tot_mins = hist["minutes"].sum()
            league_mean = (tot_xg / max(tot_mins, 1.0)) * 90.0

            opp_stats = hist.groupby("opponent_club_id")[["expected_goals", "minutes"]].sum()
            opp_rates = (opp_stats["expected_goals"] / opp_stats["minutes"].clip(lower=90.0)) * 90.0
            opp_mult = (opp_rates / max(league_mean, 1e-6)).clip(0.6, 1.6)

            m_att = hist["opponent_club_id"].map(opp_mult).fillna(1.0).to_numpy()
            de_factor = np.clip(1.0 + self.phi * (m_att - 1.0), 0.5, 2.0)

            if self.mode == "in_season_only":
                is_target = (hist["gameweek_id"] > 0).to_numpy()
                de_factor = np.where(is_target, de_factor, 1.0)

            if self.mode in ("all", "xg_only", "in_season_only"):
                hist["expected_goals"] = hist["expected_goals"] / de_factor

        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        new = shrunk_xg_rates(hist, positions, _POSITION_K)
        old = shrunk_xg_rates(self._xg_hist, positions, {})
        ratio = (new / old.where(old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)

        def_new = shrunk_xg_rates(self._xg_hist, positions, _POSITION_K)
        def_old = shrunk_xg_rates(self._xg_hist, positions, {})
        def_ratio = (def_new / def_old.where(def_old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)

        features = features_df.copy()
        is_mid_fwd = features["position_id"].isin([_MIDFIELDER, _FORWARD])
        applied_ratio = np.where(
            is_mid_fwd,
            features["player_id"].map(ratio).fillna(1.0),
            features["player_id"].map(def_ratio).fillna(1.0),
        )
        features["per90_xg"] = features["per90_xg"] * applied_ratio

        if self.mode in ("all", "xa_only"):
            features["per90_xa"] = features["per90_xa"] * applied_ratio

        return super(DefXgShrinkChallengerModel, self).predict(features, horizon)


def _make_variant(name: str, phi: float, mode: str) -> type[_BaseEXT28]:
    return type(name, (_BaseEXT28,), {"variant_name": name, "phi": float(phi), "mode": str(mode)})


_GRID = (
    ("ext_28_phi050", 0.50, "all"),
    ("ext_28_phi075", 0.75, "all"),
    ("ext_28_phi100", 1.00, "all"),
    ("ext_28_phi075_xg", 0.75, "xg_only"),
    ("ext_28_phi075_xa", 0.75, "xa_only"),
    ("ext_28_phi075_in", 0.75, "in_season_only"),
)

PROTOTYPES = {name: _make_variant(name, p, m) for name, p, m in _GRID}
_MANIFEST = (
    "history.opponent_club_id",
    "history.expected_goals",
    "history.minutes",
    "history.gameweek_id",
    "history.player_id",
    "features.player_id",
    "features.position_id",
    "features.per90_xg",
    "features.per90_xa",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
