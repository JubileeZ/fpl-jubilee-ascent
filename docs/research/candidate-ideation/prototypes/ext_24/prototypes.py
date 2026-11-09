from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT24(DefXgShrinkChallengerModel):
    variant_name: str = ""
    gamma_budget: float = 0.22
    cost_cutoff: float = 55.0

    @property
    def name(self) -> str:
        return self.variant_name

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        pos = feat.get("position_id", 3)
        is_attacker = pos.isin([3, 4])
        cost = pd.to_numeric(feat.get("now_cost", 100.0), errors="coerce").fillna(100.0)
        diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
        price_weight = np.maximum(0.0, (self.cost_cutoff - cost) / 15.0)
        mult = 1.0 + np.where(is_attacker, self.gamma_budget * price_weight * ((3.0 - diff) / 2.0), 0.0)
        for col in ("per90_xg", "per90_xa"):
            if col in feat.columns:
                feat[col] = pd.to_numeric(feat[col], errors="coerce").fillna(0.0) * mult
        return super().predict(feat, horizon)


def _make_variant(name: str, gamma_budget: float, cost_cutoff: float) -> type[_BaseEXT24]:
    return type(name, (_BaseEXT24,), {"variant_name": name, "gamma_budget": float(gamma_budget), "cost_cutoff": float(cost_cutoff)})


_GRID = (
    ("ext_24_g15_c55", 0.15, 55.0),
    ("ext_24_g22_c55", 0.22, 55.0),
    ("ext_24_g30_c55", 0.30, 55.0),
    ("ext_24_g20_c60", 0.20, 60.0),
    ("ext_24_g28_c60", 0.28, 60.0),
    ("ext_24_g35_c60", 0.35, 60.0),
)

PROTOTYPES = {name: _make_variant(name, g, c) for name, g, c in _GRID}
_MANIFEST = ("features.position_id", "features.now_cost", "features.difficulty", "features.per90_xg", "features.per90_xa")
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
