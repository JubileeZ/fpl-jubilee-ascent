from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT31(DefXgShrinkChallengerModel):
    variant_name: str = ""
    k_t: float = 19.0
    rule: str = "geo"
    w_floor: float = 0.0

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._in_season_counts = {}
        if not history_df.empty and "opponent_club_id" in history_df.columns:
            counts = history_df.groupby("opponent_club_id")["gameweek_id"].nunique().to_dict()
            self._in_season_counts = {int(k): float(v) for k, v in counts.items()}

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "club_id" in feat.columns and "opponent_id" in feat.columns and "team_attack_strength" in feat.columns:
            club_means = feat.groupby("club_id")["team_attack_strength"].mean()
            promoted_clubs = set(club_means.nsmallest(3).index)

            w_ref = 19.0 / (19.0 + self.k_t)

            def get_w_hat(cids: pd.Series) -> np.ndarray:
                in_s = cids.map(self._in_season_counts).fillna(0.0).to_numpy()
                is_p = cids.isin(promoted_clubs).to_numpy()
                n = np.where(is_p, in_s, 19.0 + in_s)
                w = n / (n + self.k_t)
                return np.clip(w / max(w_ref, 1e-6), 0.0, 1.0)

            c_own = pd.to_numeric(feat["club_id"], errors="coerce").fillna(0).astype(int)
            c_opp = pd.to_numeric(feat["opponent_id"], errors="coerce").fillna(0).astype(int)

            w_own = get_w_hat(c_own)
            w_opp = get_w_hat(c_opp)

            if self.rule == "min":
                w_pair = np.minimum(w_own, w_opp)
            else:
                w_pair = np.sqrt(w_own * w_opp)

            if self.w_floor > 0.0:
                w_pair = np.maximum(self.w_floor, w_pair)

            if "attack_multiplier" in feat.columns:
                m_att = pd.to_numeric(feat["attack_multiplier"], errors="coerce").fillna(1.0).to_numpy()
                feat["attack_multiplier"] = 1.0 + w_pair * (m_att - 1.0)

            if "defence_multiplier" in feat.columns:
                m_def = pd.to_numeric(feat["defence_multiplier"], errors="coerce").fillna(1.0).to_numpy()
                feat["defence_multiplier"] = 1.0 + w_pair * (m_def - 1.0)

        return super().predict(feat, horizon)


def _make_variant(name: str, k_t: float, rule: str, w_floor: float) -> type[_BaseEXT31]:
    return type(name, (_BaseEXT31,), {"variant_name": name, "k_t": float(k_t), "rule": str(rule), "w_floor": float(w_floor)})


_GRID = (
    ("ext_31_k10", 10.0, "geo", 0.0),
    ("ext_31_k19", 19.0, "geo", 0.0),
    ("ext_31_k38", 38.0, "geo", 0.0),
    ("ext_31_k19_min", 19.0, "min", 0.0),
    ("ext_31_k38_min", 38.0, "min", 0.0),
    ("ext_31_k19_f25", 19.0, "geo", 0.25),
)

PROTOTYPES = {name: _make_variant(name, k, r, f) for name, k, r, f in _GRID}
_MANIFEST = (
    "history.opponent_club_id",
    "history.gameweek_id",
    "features.club_id",
    "features.opponent_id",
    "features.team_attack_strength",
    "features.attack_multiplier",
    "features.defence_multiplier",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
