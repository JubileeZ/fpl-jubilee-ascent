from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

POSITION_DEFAULT_XG_SHARE: dict[int, float] = {1: 0.0, 2: 0.03, 3: 0.14, 4: 0.26}
POSITION_DEFAULT_XA_SHARE: dict[int, float] = {1: 0.01, 2: 0.07, 3: 0.18, 4: 0.14}


class _BaseEXT31(DefXgShrinkChallengerModel):
    variant_name: str = ""
    k_t: float = 19.0
    rule: str = "geo"
    w_floor: float = 0.0

    def __init__(self) -> None:
        super().__init__()
        self._promoted_clubs: set[int] = set()
        self._in_season_counts: dict[int, float] = {}
        self._opp_xgc: dict[int, float] = {}
        self._opp_xg: dict[int, float] = {}
        self._league_xg: float = 0.0
        self._league_xgc: float = 0.0

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._in_season_counts = {}
        self._opp_xgc = {}
        self._opp_xg = {}
        self._league_xg = 0.0
        self._league_xgc = 0.0

        if history_df.empty:
            self._promoted_clubs = set()
            return

        if "opponent_club_id" in history_df.columns:
            if "fixture_id" in history_df.columns:
                counts = history_df.groupby("opponent_club_id")["fixture_id"].nunique().to_dict()
            else:
                counts = history_df.groupby("opponent_club_id")["gameweek_id"].nunique().to_dict()
            self._in_season_counts = {int(k): float(v) for k, v in counts.items()}

        required_cols = {"fixture_id", "opponent_club_id", "expected_goals", "expected_goals_conceded"}
        if required_cols.issubset(history_df.columns):
            work = history_df.copy()
            work["expected_goals"] = pd.to_numeric(work["expected_goals"], errors="coerce").fillna(0.0)
            work["expected_goals_conceded"] = pd.to_numeric(work["expected_goals_conceded"], errors="coerce").fillna(0.0)
            work["opponent_club_id"] = pd.to_numeric(work["opponent_club_id"], errors="coerce").fillna(0).astype(int)
            work["fixture_id"] = pd.to_numeric(work["fixture_id"], errors="coerce").fillna(0).astype(int)

            f_xgc = work.groupby(["fixture_id", "opponent_club_id"])["expected_goals"].sum().reset_index()
            opp_xgc_s = f_xgc.groupby("opponent_club_id")["expected_goals"].mean()
            self._opp_xgc = {int(k): float(v) for k, v in opp_xgc_s.items()}
            self._league_xgc = float(f_xgc["expected_goals"].mean()) if not f_xgc.empty else 0.0

            f_xg = work.groupby(["fixture_id", "opponent_club_id"])["expected_goals_conceded"].max().reset_index()
            opp_xg_s = f_xg.groupby("opponent_club_id")["expected_goals_conceded"].mean()
            self._opp_xg = {int(k): float(v) for k, v in opp_xg_s.items()}
            self._league_xg = float(f_xg["expected_goals_conceded"].mean()) if not f_xg.empty else 0.0

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        feat = features_df.copy()
        if "club_id" in feat.columns and "opponent_id" in feat.columns:
            if not self._promoted_clubs:
                if "has_prior_seed" in feat.columns and feat["has_prior_seed"].max() > 0.0:
                    seed_means = feat.groupby("club_id")["has_prior_seed"].mean()
                    cand = set(seed_means[seed_means < 0.20].index)
                    if len(cand) == 3:
                        self._promoted_clubs = {int(c) for c in cand}
                if not self._promoted_clubs and "n_starts_historical" in feat.columns:
                    if feat["n_starts_historical"].max() > 0.0:
                        starts_means = feat.groupby("club_id")["n_starts_historical"].mean()
                        if starts_means.nunique() > 3:
                            self._promoted_clubs = {int(c) for c in starts_means.nsmallest(3).index}

            w_ref = 19.0 / (19.0 + self.k_t)

            def get_w_hat(cids: pd.Series) -> np.ndarray:
                in_s = cids.map(self._in_season_counts).fillna(0.0).to_numpy(dtype=float)
                is_p = cids.isin(self._promoted_clubs).to_numpy(dtype=bool)
                n = np.where(is_p, in_s, 19.0 + in_s)
                w = n / (n + self.k_t)
                return np.clip(w / max(w_ref, 1e-6), 0.0, 1.0)

            c_own = pd.to_numeric(feat["club_id"], errors="coerce").fillna(0).astype(int)
            c_opp = pd.to_numeric(feat["opponent_id"], errors="coerce").fillna(0).astype(int)

            w_own = get_w_hat(c_own)
            w_opp = get_w_hat(c_opp)

            if self.rule == "min":
                w_pair = np.minimum(w_own, w_opp)
            else:
                w_pair = np.sqrt(w_own * w_opp)

            if self.w_floor > 0.0:
                w_pair = np.maximum(self.w_floor, w_pair)

            if "attack_multiplier" in feat.columns:
                m_att = pd.to_numeric(feat["attack_multiplier"], errors="coerce").fillna(1.0).to_numpy(dtype=float)
                feat["attack_multiplier"] = 1.0 + w_pair * (m_att - 1.0)

            if "defence_multiplier" in feat.columns:
                m_def = pd.to_numeric(feat["defence_multiplier"], errors="coerce").fillna(1.0).to_numpy(dtype=float)
                feat["defence_multiplier"] = 1.0 + w_pair * (m_def - 1.0)

            if self._opp_xgc:
                opp_xgc_arr = c_opp.map(self._opp_xgc).fillna(self._league_xgc).to_numpy(dtype=float)
                opp_xg_arr = c_opp.map(self._opp_xg).fillna(self._league_xg).to_numpy(dtype=float)
                delta_att = opp_xgc_arr - self._league_xgc
                delta_def = opp_xg_arr - self._league_xg

                pos = (
                    pd.to_numeric(feat["position_id"], errors="coerce").fillna(3).astype(int)
                    if "position_id" in feat.columns
                    else pd.Series(3, index=feat.index)
                )
                share_xg = pos.map(POSITION_DEFAULT_XG_SHARE).fillna(0.14).to_numpy(dtype=float)
                share_xa = pos.map(POSITION_DEFAULT_XA_SHARE).fillna(0.14).to_numpy(dtype=float)

                addon_g = 0.40 * share_xg * delta_att
                addon_a = 0.40 * share_xa * delta_att
                addon_gc = 0.40 * delta_def

                if "per90_xg" in feat.columns:
                    cur_xg = pd.to_numeric(feat["per90_xg"], errors="coerce").fillna(0.0)
                    feat["per90_xg"] = (cur_xg - (1.0 - w_pair) * addon_g).clip(lower=0.0)

                if "per90_xa" in feat.columns:
                    cur_xa = pd.to_numeric(feat["per90_xa"], errors="coerce").fillna(0.0)
                    feat["per90_xa"] = (cur_xa - (1.0 - w_pair) * addon_a).clip(lower=0.0)

                if "per90_goals_conceded" in feat.columns:
                    cur_gc = pd.to_numeric(feat["per90_goals_conceded"], errors="coerce").fillna(1.2)
                    feat["per90_goals_conceded"] = (cur_gc - (1.0 - w_pair) * addon_gc).clip(lower=0.05)

        return super().predict(feat, horizon)


def _make_variant(name: str, k_t: float, rule: str, w_floor: float) -> type[_BaseEXT31]:
    return type(
        name,
        (_BaseEXT31,),
        {"variant_name": name, "k_t": float(k_t), "rule": str(rule), "w_floor": float(w_floor)},
    )


_GRID = (
    ("ext_31_k10", 10.0, "geo", 0.0),
    ("ext_31_k19", 19.0, "geo", 0.0),
    ("ext_31_k38", 38.0, "geo", 0.0),
    ("ext_31_k19_min", 19.0, "min", 0.0),
    ("ext_31_k38_min", 38.0, "min", 0.0),
    ("ext_31_k19_f25", 19.0, "geo", 0.25),
)

PROTOTYPES = {name: _make_variant(name, k, r, f) for name, k, r, f in _GRID}
_MANIFEST = (
    "history.opponent_club_id",
    "history.fixture_id",
    "history.gameweek_id",
    "history.expected_goals",
    "history.expected_goals_conceded",
    "features.club_id",
    "features.opponent_id",
    "features.position_id",
    "features.has_prior_seed",
    "features.n_starts_historical",
    "features.attack_multiplier",
    "features.defence_multiplier",
    "features.per90_xg",
    "features.per90_xa",
    "features.per90_goals_conceded",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
COMPONENTS = {name: "xp_goals" for name in PROTOTYPES}
