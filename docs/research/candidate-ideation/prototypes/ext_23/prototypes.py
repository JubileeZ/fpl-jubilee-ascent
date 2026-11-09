from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT23(DefXgShrinkChallengerModel):
    variant_name: str = ""
    alpha_cs: float = 0.16
    k_cs: float = 4.0

    @property
    def name(self) -> str:
        return self.variant_name

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "per90_goals_conceded" in feat.columns:
            diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
            hazard_mult = np.exp(self.alpha_cs * (diff - 3.0) / 1.5)
            feat["per90_goals_conceded"] = pd.to_numeric(feat["per90_goals_conceded"], errors="coerce").fillna(1.2) * hazard_mult
        return super().predict(feat, horizon)


def _make_variant(name: str, alpha_cs: float, k_cs: float) -> type[_BaseEXT23]:
    return type(name, (_BaseEXT23,), {"variant_name": name, "alpha_cs": float(alpha_cs), "k_cs": float(k_cs)})


_GRID = (
    ("ext_23_a12_k4", 0.12, 4.0),
    ("ext_23_a16_k4", 0.16, 4.0),
    ("ext_23_a20_k4", 0.20, 4.0),
    ("ext_23_a15_k6", 0.15, 6.0),
    ("ext_23_a18_k6", 0.18, 6.0),
    ("ext_23_a24_k6", 0.24, 6.0),
)

PROTOTYPES = {name: _make_variant(name, a, k) for name, a, k in _GRID}
_MANIFEST = ("features.per90_goals_conceded", "features.difficulty")
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
