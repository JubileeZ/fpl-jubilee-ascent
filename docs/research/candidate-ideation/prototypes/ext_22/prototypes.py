from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT22(DefXgShrinkChallengerModel):
    variant_name: str = ""
    beta_venue: float = 0.09
    k_venue: float = 4.0

    @property
    def name(self) -> str:
        return self.variant_name

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        is_home = feat.get("is_home", True).astype(bool)
        v_mult = np.where(is_home, np.exp(self.beta_venue), np.exp(-self.beta_venue))
        for col in ("per90_xg", "per90_xa"):
            if col in feat.columns:
                feat[col] = pd.to_numeric(feat[col], errors="coerce").fillna(0.0) * v_mult
        return super().predict(feat, horizon)


def _make_variant(name: str, beta_venue: float, k_venue: float) -> type[_BaseEXT22]:
    return type(name, (_BaseEXT22,), {"variant_name": name, "beta_venue": float(beta_venue), "k_venue": float(k_venue)})


_GRID = (
    ("ext_22_b06_k4", 0.06, 4.0),
    ("ext_22_b09_k4", 0.09, 4.0),
    ("ext_22_b12_k4", 0.12, 4.0),
    ("ext_22_b08_k6", 0.08, 6.0),
    ("ext_22_b10_k6", 0.10, 6.0),
    ("ext_22_b14_k8", 0.14, 8.0),
)

PROTOTYPES = {name: _make_variant(name, b, k) for name, b, k in _GRID}
_MANIFEST = ("features.is_home", "features.per90_xg", "features.per90_xa")
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
