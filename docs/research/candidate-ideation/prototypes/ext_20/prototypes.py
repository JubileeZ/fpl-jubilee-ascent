"""EXT-20 prototypes: Endogenous Attacking-Role Stratification & Threat-Adaptive Shrinkage for Out-of-Position Defenders."""

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


class _BaseThreatAdaptiveDefenderModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion + threat-adaptive K and prior elevation for OOP/attacking defenders."""

    variant_name: str = ""
    tau_threat: float = 22.0
    k_oop: float = 600.0
    gamma_oop: float = 0.25

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

        # Identify OOP / Attacking Defenders (position_id == 2 and shrunk_threat >= tau_threat)
        is_def = player_pos.eq(2)
        is_oop = is_def & (shrunk_threat >= self.tau_threat)

        # Prior elevation for OOP defenders
        def_threat_mean = pos_threat_rate.get(2, 10.0)
        rel_threat = np.clip((shrunk_threat - def_threat_mean) / max(def_threat_mean, 1.0), 0.0, 2.5)
        adj_prior = np.where(is_oop, base_xg_prior * (1.0 + self.gamma_oop * rel_threat), base_xg_prior)

        # Adaptive K: K_OOP for attacking defenders; K_DEF=2400 for traditional defenders; 360 for MID/FWD
        k_vec = np.where(is_oop, self.k_oop, np.where(is_def, _POSITION_K[2], _BASE_K))

        new_rates = (sums["xg"] + k_vec * adj_prior / 90.0) / (sums["mins"] + k_vec) * 90.0
        old_rates = shrunk_xg_rates(self._xg_hist, positions, {})
        ratio = (new_rates / old_rates.where(old_rates > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)

        features = features_df.copy()
        features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()
        return super(DefXgShrinkChallengerModel, self).predict(features, horizon)


def _make_variant(name: str, tau_threat: float, k_oop: float, gamma_oop: float) -> type[_BaseThreatAdaptiveDefenderModel]:
    return type(
        name,
        (_BaseThreatAdaptiveDefenderModel,),
        {"variant_name": name, "tau_threat": float(tau_threat), "k_oop": float(k_oop), "gamma_oop": float(gamma_oop)},
    )


_GRID = (
    ("ext_20_t12_k1600", 12.0, 1600.0, 0.15),
    ("ext_20_t12_k1200", 12.0, 1200.0, 0.15),
    ("ext_20_t15_k1200", 15.0, 1200.0, 0.20),
    ("ext_20_t15_k800", 15.0, 800.0, 0.20),
    ("ext_20_t18_k1200", 18.0, 1200.0, 0.25),
    ("ext_20_t18_k800", 18.0, 800.0, 0.25),
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

PROTOTYPES = {name: _make_variant(name, tau, k, g) for name, tau, k, g in _GRID}
FEATURES = {name: _MANIFEST_ENTRIES for name, _, _, _ in _GRID}
