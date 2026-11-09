from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT26(DefXgShrinkChallengerModel):
    variant_name: str = ""
    psi_margin: float = 2.5
    tau_margin: float = 0.5

    @property
    def name(self) -> str:
        return self.variant_name

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "team_attack_strength" in feat.columns and "opponent_defence_strength" in feat.columns:
            atk = pd.to_numeric(feat["team_attack_strength"], errors="coerce").fillna(1000.0) / 100.0
            opp_def = pd.to_numeric(feat["opponent_defence_strength"], errors="coerce").fillna(1000.0) / 100.0
            margin = (atk - opp_def).clip(lower=0.0)
            excess = np.maximum(0.0, margin - self.tau_margin)
            offset = -self.psi_margin * excess
            if "xmins_if_start" in feat.columns:
                feat["xmins_if_start"] = (pd.to_numeric(feat["xmins_if_start"], errors="coerce").fillna(78.0) + offset).clip(lower=60.0)
        return super().predict(feat, horizon)


def _make_variant(name: str, psi_margin: float, tau_margin: float) -> type[_BaseEXT26]:
    return type(name, (_BaseEXT26,), {"variant_name": name, "psi_margin": float(psi_margin), "tau_margin": float(tau_margin)})


_GRID = (
    ("ext_26_p15_t05", 1.5, 0.5),
    ("ext_26_p25_t05", 2.5, 0.5),
    ("ext_26_p35_t05", 3.5, 0.5),
    ("ext_26_p20_t075", 2.0, 0.75),
    ("ext_26_p30_t075", 3.0, 0.75),
    ("ext_26_p40_t10", 4.0, 1.0),
)

PROTOTYPES = {name: _make_variant(name, p, t) for name, p, t in _GRID}
_MANIFEST = ("features.team_attack_strength", "features.opponent_defence_strength", "features.xmins_if_start")
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
