from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT25(DefXgShrinkChallengerModel):
    variant_name: str = ""
    xi_modality: float = 0.12
    k_modality: float = 360.0

    @property
    def name(self) -> str:
        return self.variant_name

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        xg = pd.to_numeric(feat.get("per90_xg", 0.0), errors="coerce").fillna(0.0)
        xa = pd.to_numeric(feat.get("per90_xa", 0.0), errors="coerce").fillna(0.0)
        tot = xg + xa + 1e-6
        theta = (xg / tot).clip(0.0, 1.0)
        diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
        contrast = (theta - 0.5) * ((3.0 - diff) / 2.0)
        feat["per90_xg"] = xg * (1.0 + self.xi_modality * np.clip(2.0 * contrast, -1.0, 1.0))
        feat["per90_xa"] = xa * (1.0 - self.xi_modality * np.clip(2.0 * contrast, -1.0, 1.0))
        return super().predict(feat, horizon)


def _make_variant(name: str, xi_modality: float, k_modality: float) -> type[_BaseEXT25]:
    return type(name, (_BaseEXT25,), {"variant_name": name, "xi_modality": float(xi_modality), "k_modality": float(k_modality)})


_GRID = (
    ("ext_25_x08_k360", 0.08, 360.0),
    ("ext_25_x12_k360", 0.12, 360.0),
    ("ext_25_x16_k360", 0.16, 360.0),
    ("ext_25_x10_k540", 0.10, 540.0),
    ("ext_25_x14_k540", 0.14, 540.0),
    ("ext_25_x18_k540", 0.18, 540.0),
)

PROTOTYPES = {name: _make_variant(name, x, k) for name, x, k in _GRID}
_MANIFEST = ("features.per90_xg", "features.per90_xa", "features.difficulty")
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
