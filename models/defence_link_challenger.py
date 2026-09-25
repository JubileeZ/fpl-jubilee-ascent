"""Defence-link Model Candidate (wayfinder #117 / #118).

Subclass of ``goals_path_challenger``: keeps goals levers; after parent
``predict``, scales ``xp_clean_sheet`` by ``_CS_SCALE`` and ``xp_conceded`` by
``_GC_SCALE`` (post-link only; λ / NegBin / ``_DEF_RELAX`` untouched).
Recalibrate via ``docs/research/champion-component-gap/calibrate_defence_k.py``.
"""

from __future__ import annotations

import pandas as pd

from models.goals_path_challenger import GoalsPathChallengerModel

# Set by calibrate_defence_k.py from 2025-26 mins_60 CS ALL / GC GKP+DEF (τ=0.05).
_CS_SCALE = 1.296903
_GC_SCALE = 1.145226


class DefenceLinkChallengerModel(GoalsPathChallengerModel):
    """Goals-path Candidate plus post-link CS / conceded scales."""

    @property
    def name(self) -> str:
        return "defence_link_challenger"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        out = super().predict(features_df, horizon).copy()
        cs = pd.to_numeric(out["xp_clean_sheet"], errors="coerce").fillna(0.0)
        gc = pd.to_numeric(out["xp_conceded"], errors="coerce").fillna(0.0)
        k_cs = float(_CS_SCALE)
        k_gc = float(_GC_SCALE)
        out["projected_points"] = (
            pd.to_numeric(out["projected_points"], errors="coerce").fillna(0.0)
            + (k_cs - 1.0) * cs
            + (k_gc - 1.0) * gc
        )
        out["xp_clean_sheet"] = cs * k_cs
        out["xp_conceded"] = gc * k_gc
        return out
