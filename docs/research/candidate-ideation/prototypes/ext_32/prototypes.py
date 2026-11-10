"""EXT-32 prototypes: Smooth Continuous Threat-Adaptive Defender Shrinkage."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import (
    _BASE_K,
    _DECAY,
    _MIDFIELDER,
    _POSITION_K,
    _RATIO_CLIP,
    DefXgShrinkChallengerModel,
    shrunk_xg_rates,
)

_THREAT_HIST_COLS = ("player_id", "gameweek_id", "minutes", "expected_goals", "threat")


class _BaseSmoothThreatAdaptiveDefenderModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion + smooth continuous sigmoid threat-adaptive K and prior elevation."""

    variant_name: str = ""
    tau_threat: float = 15.0
    k_oop: float = 800.0
    gamma_oop: float = 0.20
    m_zero: float = 360.0
    s_threat: float = 3.0

    def __init__(self) -> None:
        super().__init__()
        self._threat_hist = pd.DataFrame(columns=list(_THREAT_HIST_COLS))

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_THREAT_HIST_COLS).issubset(history_df.columns):
            self._threat_hist = pd.DataFrame(columns=list(_THREAT_HIST_COLS))
            return
        hist = history_df[list(_THREAT_HIST_COLS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        self._threat_hist = hist[hist["minutes"] > 0]

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._threat_hist.empty or features_df.empty:
            return super().predict(features_df, horizon)

        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        hist = self._threat_hist
        pos = hist["player_id"].map(positions).fillna(_MIDFIELDER)

        by_pos = hist.groupby(pos)[["expected_goals", "threat", "minutes"]].sum()
        pos_xg_rate = (by_pos["expected_goals"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()
        pos_threat_rate = (by_pos["threat"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()

        last = hist.groupby("player_id")["gameweek_id"].transform("max")
        weight = _DECAY ** (last - hist["gameweek_id"])
        sums = pd.DataFrame({
            "xg": hist["expected_goals"] * weight,
            "threat": hist["threat"] * weight,
            "mins": hist["minutes"] * weight,
            "player_id": hist["player_id"],
        }).groupby("player_id").sum()

        player_pos = positions.reindex(sums.index).fillna(_MIDFIELDER)
        base_xg_prior = player_pos.map(pos_xg_rate).fillna(0.0)
        base_threat_prior = player_pos.map(pos_threat_rate).fillna(10.0)

        # Shrunk threat per 90 (K=360 pseudo-minutes)
        shrunk_threat = (sums["threat"] + 360.0 * base_threat_prior / 90.0) / (sums["mins"] + 360.0) * 90.0

        # Continuous sigmoid attacking-role transition conditioned on shrunk threat and minute reliability
        is_def = player_pos.eq(2)
        rel_minutes = sums["mins"] / (sums["mins"] + self.m_zero)
        z_threat = (shrunk_threat - self.tau_threat) / max(self.s_threat, 0.1)
        sigmoid_threat = 1.0 / (1.0 + np.exp(-np.clip(z_threat, -10.0, 10.0)))
        sigma_oop = np.where(is_def, rel_minutes * sigmoid_threat, 0.0)

        # Prior elevation for attacking defenders scaled smoothly by sigma_oop
        def_threat_mean = pos_threat_rate.get(2, 10.0)
        rel_threat = np.clip((shrunk_threat - def_threat_mean) / max(def_threat_mean, 1.0), 0.0, 2.5)
        adj_prior = np.where(
            is_def,
            base_xg_prior * (1.0 + sigma_oop * self.gamma_oop * rel_threat),
            base_xg_prior,
        )

        # Smoothly interpolate shrinkage constant K: K_DEF=2400 for sigma=0, K_OOP for sigma=1
        k_def = _POSITION_K.get(2, 2400.0)
        k_vec = np.where(
            is_def,
            (1.0 - sigma_oop) * k_def + sigma_oop * self.k_oop,
            _BASE_K,
        )

        new_rates = (sums["xg"] + k_vec * adj_prior / 90.0) / (sums["mins"] + k_vec) * 90.0
        old_rates = shrunk_xg_rates(self._xg_hist, positions, {})
        ratio = (new_rates / old_rates.where(old_rates > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)

        features = features_df.copy()
        features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()
        return super(DefXgShrinkChallengerModel, self).predict(features, horizon)


def _make_variant(
    name: str,
    tau_threat: float,
    k_oop: float,
    m_zero: float,
    gamma_oop: float,
    s_threat: float,
) -> type[_BaseSmoothThreatAdaptiveDefenderModel]:
    return type(
        name,
        (_BaseSmoothThreatAdaptiveDefenderModel,),
        {
            "variant_name": name,
            "tau_threat": float(tau_threat),
            "k_oop": float(k_oop),
            "m_zero": float(m_zero),
            "gamma_oop": float(gamma_oop),
            "s_threat": float(s_threat),
        },
    )


_GRID = (
    ("ext_32_t15_k800_m360", 15.0, 800.0, 360.0, 0.20, 3.0),
    ("ext_32_t15_k600_m360", 15.0, 600.0, 360.0, 0.25, 3.0),
    ("ext_32_t15_k1000_m450", 15.0, 1000.0, 450.0, 0.20, 3.0),
    ("ext_32_t18_k800_m360", 18.0, 800.0, 360.0, 0.25, 3.0),
    ("ext_32_t18_k600_m450", 18.0, 600.0, 450.0, 0.25, 3.5),
    ("ext_32_t14_k800_m360", 14.0, 800.0, 360.0, 0.20, 2.5),
)

_MANIFEST_ENTRIES = (
    "features.player_id",
    "features.position_id",
    "features.per90_xg",
    "history.player_id",
    "history.gameweek_id",
    "history.minutes",
    "history.expected_goals",
    "history.threat",
    "local.xg",
    "local.threat",
    "local.mins",
)

PROTOTYPES = {name: _make_variant(name, tau, k, m, g, s) for name, tau, k, m, g, s in _GRID}
FEATURES = {name: _MANIFEST_ENTRIES for name, _, _, _, _, _ in _GRID}
COMPONENTS = {name: "xp_goals" for name in PROTOTYPES}
