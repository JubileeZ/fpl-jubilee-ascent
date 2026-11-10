from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_REQUIRED_HIST_COLS = {"fixture_id", "opponent_club_id", "expected_goals", "gameweek_id", "minutes"}


class _BaseEXT23(DefXgShrinkChallengerModel):
    variant_name: str = ""
    alpha_cs: float = 0.16
    k_cs: float = 4.0

    def __init__(self, alpha_cs: float | None = None, k_cs: float | None = None, **kwargs: object) -> None:
        super().__init__()
        if alpha_cs is not None:
            self.alpha_cs = float(alpha_cs)
        if k_cs is not None:
            self.k_cs = float(k_cs)
        self._club_lambda: dict[int, float] = {}
        self._club_matches: dict[int, int] = {}
        self._league_mean_xg: float = 1.35

    @property
    def name(self) -> str:
        return self.variant_name

    @staticmethod
    def _apply_hard_fixture_defence(feat: pd.DataFrame) -> pd.DataFrame:
        """Bypass inherited hard fixture penalty; replaced by asymmetric log-linear decay."""
        return feat

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._club_lambda = {}
        self._club_matches = {}
        self._league_mean_xg = 1.35
        if history_df.empty or not _REQUIRED_HIST_COLS.issubset(history_df.columns):
            return

        hist = history_df[list(_REQUIRED_HIST_COLS)].copy()
        for col in _REQUIRED_HIST_COLS:
            hist[col] = pd.to_numeric(hist[col], errors="coerce").fillna(0.0)

        sides = hist.groupby("fixture_id")["opponent_club_id"].agg(["min", "max"])
        min_side = hist["fixture_id"].map(sides.iloc[:, 0])
        max_side = hist["fixture_id"].map(sides.iloc[:, 1])
        two_sided = min_side != max_side

        hist = hist.loc[two_sided].copy()
        if hist.empty:
            return
        hist["club"] = (min_side.loc[two_sided] + max_side.loc[two_sided] - hist["opponent_club_id"]).astype(int)

        club_fx = hist.groupby(["fixture_id", "club"], as_index=False)["expected_goals"].sum()
        if club_fx.empty:
            return

        total_xg = float(club_fx["expected_goals"].sum())
        total_matches = len(club_fx)
        league_mean = total_xg / total_matches if total_matches > 0 else 1.35
        self._league_mean_xg = league_mean if np.isfinite(league_mean) and league_mean > 0 else 1.35

        sum_xg = club_fx.groupby("club")["expected_goals"].sum()
        cnt_matches = club_fx.groupby("club")["expected_goals"].count()

        for c, n_c in cnt_matches.items():
            cid = int(c)
            n_val = int(n_c)
            s_val = float(sum_xg.get(c, 0.0))
            shrunk_lambda = (s_val + self.k_cs * self._league_mean_xg) / (n_val + self.k_cs)
            self._club_lambda[cid] = shrunk_lambda
            self._club_matches[cid] = n_val

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "per90_goals_conceded" in feat.columns:
            diff = pd.to_numeric(feat.get("difficulty", 3.0), errors="coerce").fillna(3.0)
            z_fdr = (diff - 3.0) / 1.5

            if "opponent_id" in feat.columns:
                opp_ids = pd.to_numeric(feat["opponent_id"], errors="coerce")
            elif "opponent_club_id" in feat.columns:
                opp_ids = pd.to_numeric(feat["opponent_club_id"], errors="coerce")
            else:
                opp_ids = pd.Series(np.nan, index=feat.index)

            z = z_fdr.copy()
            if self._club_lambda and not opp_ids.isna().all():
                opp_lambda = opp_ids.map(self._club_lambda)
                opp_n = opp_ids.map(self._club_matches).fillna(0.0)
                valid = opp_lambda.notna() & (opp_n > 0)
                if valid.any():
                    z_opp = (opp_lambda.loc[valid] - self._league_mean_xg) / self._league_mean_xg
                    w = opp_n.loc[valid] / (opp_n.loc[valid] + self.k_cs)
                    z.loc[valid] = (1.0 - w) * z_fdr.loc[valid] + z_opp

            hazard_mult = np.exp(self.alpha_cs * z)
            feat["per90_goals_conceded"] = (
                pd.to_numeric(feat["per90_goals_conceded"], errors="coerce").fillna(1.2) * hazard_mult
            )
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
_MANIFEST = (
    "features.per90_goals_conceded",
    "features.difficulty",
    "features.opponent_id",
    "features.opponent_club_id",
    "history.fixture_id",
    "history.opponent_club_id",
    "history.expected_goals",
    "history.gameweek_id",
    "history.minutes",
    "local.club",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
