"""EXT-18 prototypes: Starter-Role Conditioning & Set-Piece Share Persistence for Budget Enablers."""

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

_ROLE_HIST_COLS = ("player_id", "gameweek_id", "minutes", "expected_goals", "creativity")


class _BaseBudgetRolePriorModel(DefXgShrinkChallengerModel):
    """DefXgShrink Champion (DEF K=2400) + role-conditioned creative-share xG shrinkage for MID/FWD."""

    variant_name: str = ""
    k_atk: float = 540.0
    gamma_role: float = 0.18

    def __init__(self) -> None:
        super().__init__()
        self._role_hist = pd.DataFrame(columns=list(_ROLE_HIST_COLS))

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_ROLE_HIST_COLS).issubset(history_df.columns):
            self._role_hist = pd.DataFrame(columns=list(_ROLE_HIST_COLS))
            return
        hist = history_df[list(_ROLE_HIST_COLS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        self._role_hist = hist[hist["minutes"] > 0]

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._role_hist.empty or features_df.empty:
            return super().predict(features_df, horizon)
        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        hist = self._role_hist
        pos = hist["player_id"].map(positions).fillna(_MIDFIELDER)
        by_pos = hist.groupby(pos)[["expected_goals", "creativity", "minutes"]].sum()
        pos_xg_rate = (by_pos["expected_goals"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()
        pos_cre_rate = (by_pos["creativity"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()

        last = hist.groupby("player_id")["gameweek_id"].transform("max")
        weight = _DECAY ** (last - hist["gameweek_id"])
        sums = pd.DataFrame({
            "xg": hist["expected_goals"] * weight,
            "cre": hist["creativity"] * weight,
            "mins": hist["minutes"] * weight,
            "player_id": hist["player_id"],
        }).groupby("player_id").sum()

        player_pos = positions.reindex(sums.index).fillna(_MIDFIELDER)
        base_prior = player_pos.map(pos_xg_rate).fillna(0.0)
        cre_prior = player_pos.map(pos_cre_rate).fillna(10.0)
        shrunk_cre = (sums["cre"] + 360.0 * cre_prior / 90.0) / (sums["mins"] + 360.0) * 90.0
        rel_cre = np.clip((shrunk_cre - cre_prior) / cre_prior.clip(lower=1.0), -0.5, 1.5)

        is_atk = player_pos.isin([3, 4])
        adj_prior = np.where(is_atk, base_prior * (1.0 + self.gamma_role * rel_cre), base_prior)
        k_map = {2: _POSITION_K[2], 3: self.k_atk, 4: self.k_atk}
        k_vec = player_pos.map(k_map).fillna(_BASE_K)
        new_rates = (sums["xg"] + k_vec * adj_prior / 90.0) / (sums["mins"] + k_vec) * 90.0
        old_rates = shrunk_xg_rates(self._xg_hist, positions, {})
        ratio = (new_rates / old_rates.where(old_rates > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)

        features = features_df.copy()
        features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()
        return super(DefXgShrinkChallengerModel, self).predict(features, horizon)


def _make_variant(name: str, k_atk: float, gamma_role: float) -> type[_BaseBudgetRolePriorModel]:
    return type(
        name,
        (_BaseBudgetRolePriorModel,),
        {"variant_name": name, "k_atk": float(k_atk), "gamma_role": float(gamma_role)},
    )


_GRID = (
    ("ext_18_k540_g015", 540.0, 0.15),
    ("ext_18_k540_g022", 540.0, 0.22),
    ("ext_18_k630_g018", 630.0, 0.18),
    ("ext_18_k720_g020", 720.0, 0.20),
    ("ext_18_k450_g015", 450.0, 0.15),
    ("ext_18_k630_g012", 630.0, 0.12),
)

_MANIFEST_ENTRIES = (
    "features.player_id",
    "features.position_id",
    "features.per90_xg",
    "history.player_id",
    "history.gameweek_id",
    "history.minutes",
    "history.expected_goals",
    "history.creativity",
    "local.xg",
    "local.cre",
    "local.mins",
)

PROTOTYPES = {name: _make_variant(name, k, g) for name, k, g in _GRID}
FEATURES = {name: _MANIFEST_ENTRIES for name, _, _ in _GRID}
