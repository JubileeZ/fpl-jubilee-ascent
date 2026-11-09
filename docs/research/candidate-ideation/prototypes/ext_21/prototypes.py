from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT21(DefXgShrinkChallengerModel):
    variant_name: str = ""
    gamma_fix: float = 0.15
    kappa_scale: float = 1.0

    @property
    def name(self) -> str:
        return self.variant_name

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "per90_xg" in feat.columns:
            xg = pd.to_numeric(feat["per90_xg"], errors="coerce").fillna(0.0)
            diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
            delta_norm = (3.0 - diff) / 1.5
            m_open = 1.0 + self.gamma_fix * np.tanh(self.kappa_scale * delta_norm)
            feat["per90_xg"] = xg * m_open
        return super().predict(feat, horizon)


def _make_variant(name: str, gamma_fix: float, kappa_scale: float) -> type[_BaseEXT21]:
    return type(name, (_BaseEXT21,), {"variant_name": name, "gamma_fix": float(gamma_fix), "kappa_scale": float(kappa_scale)})


_GRID = (
    ("ext_21_g10_k08", 0.10, 0.8),
    ("ext_21_g15_k10", 0.15, 1.0),
    ("ext_21_g20_k10", 0.20, 1.0),
    ("ext_21_g15_k12", 0.15, 1.2),
    ("ext_21_g18_k08", 0.18, 0.8),
    ("ext_21_g22_k12", 0.22, 1.2),
)

PROTOTYPES = {name: _make_variant(name, g, k) for name, g, k in _GRID}
_MANIFEST = ("features.per90_xg", "features.difficulty")
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
