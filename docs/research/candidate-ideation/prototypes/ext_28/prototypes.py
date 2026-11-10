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
_COLS = ("player_id", "gameweek_id", "minutes", "expected_goals", "expected_assists", "opponent_club_id")


class _BaseEXT28(DefXgShrinkChallengerModel):
    variant_name: str = ""
    phi: float = 0.75
    mode: str = "all"

    def __init__(self) -> None:
        super().__init__()
        self._xg_hist = pd.DataFrame(columns=list(_COLS))
        self._orig_history = pd.DataFrame()

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if not history_df.empty and set(_COLS).issubset(history_df.columns):
            hist = history_df[list(_COLS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)
            self._xg_hist = hist[hist["minutes"] > 0].copy()
        else:
            self._xg_hist = pd.DataFrame(columns=list(_COLS))
        self._orig_history = self._history.copy() if hasattr(self, "_history") and isinstance(self._history, pd.DataFrame) else pd.DataFrame()

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._xg_hist.empty:
            return super().predict(features_df, horizon)

        hist = self._xg_hist.copy()
        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        hist_pos = hist["player_id"].map(positions).fillna(_MIDFIELDER)
        is_mid_fwd_hist = hist_pos.isin([_MIDFIELDER, _FORWARD]).to_numpy()

        opp_mult = pd.Series(dtype=float)
        if "opponent_club_id" in hist.columns and "expected_goals" in hist.columns:
            tot_xg = hist["expected_goals"].sum()
            tot_mins = hist["minutes"].sum()
            league_mean = (tot_xg / max(tot_mins, 1.0)) * 90.0

            opp_stats = hist.groupby("opponent_club_id")[["expected_goals", "minutes"]].sum()
            opp_rates = (opp_stats["expected_goals"] / opp_stats["minutes"].clip(lower=1.0)) * 90.0
            opp_mult = (opp_rates / max(league_mean, 1e-6)).clip(0.6, 1.6)

            m_att = hist["opponent_club_id"].map(opp_mult).fillna(1.0).to_numpy()
            de_factor = np.clip(1.0 + self.phi * (m_att - 1.0), 0.5, 2.0)

            if self.mode == "in_season_only":
                is_target = (hist["gameweek_id"] > 0).to_numpy()
                de_factor = np.where(is_target, de_factor, 1.0)

            eff_de_factor = np.where(is_mid_fwd_hist, de_factor, 1.0)

            if self.mode in ("all", "xg_only", "in_season_only"):
                hist["expected_goals"] = hist["expected_goals"] / eff_de_factor

            if self.mode in ("all", "xa_only", "in_season_only") and "expected_assists" in hist.columns:
                hist["expected_assists"] = hist["expected_assists"] / eff_de_factor

        if self.mode in ("all", "xg_only", "in_season_only"):
            new_xg = shrunk_xg_rates(hist, positions, {})
            old_xg = shrunk_xg_rates(self._xg_hist, positions, {})
            ratio_xg = (new_xg / old_xg.where(old_xg > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)
        else:
            ratio_xg = pd.Series(1.0, index=positions.index)

        def_new = shrunk_xg_rates(self._xg_hist, positions, _POSITION_K)
        def_old = shrunk_xg_rates(self._xg_hist, positions, {})
        def_ratio = (def_new / def_old.where(def_old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)

        features = features_df.copy()
        is_mid_fwd = features["position_id"].isin([_MIDFIELDER, _FORWARD])
        is_def = features["position_id"] == _DEFENDER

        applied_ratio_xg = np.where(
            is_mid_fwd,
            features["player_id"].map(ratio_xg).fillna(1.0),
            np.where(
                is_def,
                features["player_id"].map(def_ratio).fillna(1.0),
                1.0,
            ),
        )
        features["per90_xg"] = features["per90_xg"] * applied_ratio_xg

        if self.mode in ("all", "xa_only", "in_season_only") and "expected_assists" in hist.columns:
            hist_xa = hist[["player_id", "gameweek_id", "minutes", "expected_assists"]].rename(
                columns={"expected_assists": "expected_goals"}
            )
            raw_hist_xa = self._xg_hist[["player_id", "gameweek_id", "minutes", "expected_assists"]].rename(
                columns={"expected_assists": "expected_goals"}
            )
            new_xa = shrunk_xg_rates(hist_xa, positions, {})
            old_xa = shrunk_xg_rates(raw_hist_xa, positions, {})
            ratio_xa = (new_xa / old_xa.where(old_xa > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)

            applied_ratio_xa = np.where(
                is_mid_fwd,
                features["player_id"].map(ratio_xa).fillna(1.0),
                1.0,
            )
            features["per90_xa"] = features["per90_xa"] * applied_ratio_xa

            if hasattr(self, "_orig_history") and isinstance(self._orig_history, pd.DataFrame) and not self._orig_history.empty:
                self._history = self._orig_history.copy()
                if "expected_assists" in self._history.columns and "opponent_club_id" in self._history.columns and not opp_mult.empty:
                    m_att_h = self._history["opponent_club_id"].map(opp_mult).fillna(1.0).to_numpy()
                    de_h = np.clip(1.0 + self.phi * (m_att_h - 1.0), 0.5, 2.0)
                    if self.mode == "in_season_only":
                        is_tgt_h = (self._history["gameweek_id"] > 0).to_numpy()
                        de_h = np.where(is_tgt_h, de_h, 1.0)
                    pos_h = self._history["player_id"].map(positions).fillna(_MIDFIELDER)
                    is_mf_h = pos_h.isin([_MIDFIELDER, _FORWARD]).to_numpy()
                    eff_de_h = np.where(is_mf_h, de_h, 1.0)
                    self._history["expected_assists"] = self._history["expected_assists"] / eff_de_h
        else:
            if hasattr(self, "_orig_history") and isinstance(self._orig_history, pd.DataFrame) and not self._orig_history.empty:
                self._history = self._orig_history.copy()

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
    "history.expected_assists",
    "history.minutes",
    "history.gameweek_id",
    "history.player_id",
    "features.player_id",
    "features.position_id",
    "features.per90_xg",
    "features.per90_xa",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
