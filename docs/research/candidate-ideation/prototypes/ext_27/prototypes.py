from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT27(DefXgShrinkChallengerModel):
    variant_name: str = ""
    eta: float = 0.75
    scope: str = "all"

    def __init__(self, eta: float | None = None, scope: str | None = None, **kwargs: object) -> None:
        super().__init__()
        if eta is not None:
            self.eta = float(eta)
        if scope is not None:
            self.scope = str(scope)
        self._h_hat = 0.08

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if {"team_h_score", "team_a_score"}.issubset(history_df.columns) and not history_df.empty:
            df = history_df
            if "fixture_id" in df.columns:
                df = df.drop_duplicates(subset=["fixture_id"])
            scores = df[["team_h_score", "team_a_score"]].apply(pd.to_numeric, errors="coerce").dropna()
            if not scores.empty:
                gh = float(scores["team_h_score"].sum())
                ga = float(scores["team_a_score"].sum())
                h0 = 0.08
                g0 = 300.0
                hat_h = (gh - ga + g0 * h0) / (gh + ga + g0)
                self._h_hat = float(np.clip(hat_h, 0.02, 0.20))
            else:
                self._h_hat = 0.08
        else:
            self._h_hat = 0.08

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        is_home = feat["is_home"].astype(bool) if "is_home" in feat.columns else pd.Series(True, index=feat.index)
        h_home = 1.0 + self.eta * self._h_hat
        h_away = 1.0 - self.eta * self._h_hat
        mult_att = np.where(is_home, h_home, h_away)
        mult_def = np.where(is_home, 1.0 - self.eta * self._h_hat, 1.0 + self.eta * self._h_hat)

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
_MANIFEST = (
    "features.is_home",
    "features.attack_multiplier",
    "features.defence_multiplier",
    "history.team_h_score",
    "history.team_a_score",
    "history.fixture_id",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
