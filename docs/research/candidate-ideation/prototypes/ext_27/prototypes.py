from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT27(DefXgShrinkChallengerModel):
    variant_name: str = ""
    eta: float = 0.75
    scope: str = "all"

    @property
    def name(self) -> str:
        return self.variant_name

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        is_home = feat.get("is_home", True).astype(bool)
        h_hat = 0.12
        v_h = 1.10
        v_a = 0.90
        h_home = (1.0 + self.eta * h_hat) / v_h
        h_away = (1.0 - self.eta * h_hat) / v_a
        mult_att = np.where(is_home, h_home, h_away)
        mult_def = np.where(is_home, 1.0 / h_home, 1.0 / h_away)

        if self.scope in ("all", "goals_assists_only"):
            if "attack_multiplier" in feat.columns:
                feat["attack_multiplier"] = (
                    pd.to_numeric(feat["attack_multiplier"], errors="coerce").fillna(1.0) * mult_att
                ).clip(0.4, 2.0)

        if self.scope in ("all", "cs_gc_only"):
            if "defence_multiplier" in feat.columns:
                feat["defence_multiplier"] = (
                    pd.to_numeric(feat["defence_multiplier"], errors="coerce").fillna(1.0) * mult_def
                ).clip(0.4, 2.0)

        return super().predict(feat, horizon)


def _make_variant(name: str, eta: float, scope: str) -> type[_BaseEXT27]:
    return type(name, (_BaseEXT27,), {"variant_name": name, "eta": float(eta), "scope": str(scope)})


_GRID = (
    ("ext_27_e50_all", 0.50, "all"),
    ("ext_27_e75_all", 0.75, "all"),
    ("ext_27_e100_all", 1.00, "all"),
    ("ext_27_e75_att", 0.75, "goals_assists_only"),
    ("ext_27_e75_def", 0.75, "cs_gc_only"),
    ("ext_27_e100_att", 1.00, "goals_assists_only"),
)

PROTOTYPES = {name: _make_variant(name, e, s) for name, e, s in _GRID}
_MANIFEST = ("features.is_home", "features.attack_multiplier", "features.defence_multiplier")
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
