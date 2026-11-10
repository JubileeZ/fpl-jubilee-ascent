"""EXT-34 prototypes: Unified Fullback Attacking-Role and Matchup Clean-Sheet Hazard."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import (
    _BASE_K,
    _DECAY,
    _MIDFIELDER,
    _POSITION_K,
    _RATIO_CLIP,
    DefXgShrinkChallengerModel,
    shrunk_xg_rates,
)

_THREAT_HIST_COLS = ("player_id", "gameweek_id", "minutes", "expected_goals", "threat")
_FIXTURE_HIST_COLS = ("fixture_id", "opponent_club_id", "expected_goals", "gameweek_id", "minutes")


class _BaseEXT34(DefXgShrinkChallengerModel):
    """Unified smooth threat-adaptive defender shrinkage + asymmetric convex clean sheet hazard."""

    variant_name: str = ""
    tau_threat: float = 15.0
    k_oop: float = 800.0
    gamma_oop: float = 0.20
    m_zero: float = 360.0
    s_threat: float = 3.0
    alpha_cs: float = 0.20
    rho_cs: float = 0.25
    k_cs: float = 8.0

    def __init__(
        self,
        tau_threat: float | None = None,
        k_oop: float | None = None,
        alpha_cs: float | None = None,
        m_zero: float | None = None,
        gamma_oop: float | None = None,
        s_threat: float | None = None,
        rho_cs: float | None = None,
        k_cs: float | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__()
        if tau_threat is not None:
            self.tau_threat = float(tau_threat)
        if k_oop is not None:
            self.k_oop = float(k_oop)
        if alpha_cs is not None:
            self.alpha_cs = float(alpha_cs)
        if m_zero is not None:
            self.m_zero = float(m_zero)
        if gamma_oop is not None:
            self.gamma_oop = float(gamma_oop)
        if s_threat is not None:
            self.s_threat = float(s_threat)
        if rho_cs is not None:
            self.rho_cs = float(rho_cs)
        if k_cs is not None:
            self.k_cs = float(k_cs)

        self._threat_hist = pd.DataFrame(columns=list(_THREAT_HIST_COLS))
        self._club_lambda: dict[int, float] = {}
        self._club_matches: dict[int, int] = {}
        self._league_mean_xg: float = 1.35

    @property
    def name(self) -> str:
        return self.variant_name

    @staticmethod
    def _apply_hard_fixture_defence(feat: pd.DataFrame) -> pd.DataFrame:
        """Bypass inherited hard fixture penalty; replaced by asymmetric hazard decay."""
        return feat

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._club_lambda = {}
        self._club_matches = {}
        self._league_mean_xg = 1.35

        # Ingest threat history for attacking defender shrinkage
        if not history_df.empty and set(_THREAT_HIST_COLS).issubset(history_df.columns):
            hist_threat = history_df[list(_THREAT_HIST_COLS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)
            self._threat_hist = hist_threat[hist_threat["minutes"] > 0]
        else:
            self._threat_hist = pd.DataFrame(columns=list(_THREAT_HIST_COLS))

        # Ingest fixture match history for opponent attack strength
        if not history_df.empty and set(_FIXTURE_HIST_COLS).issubset(history_df.columns):
            hist_fix = history_df[list(_FIXTURE_HIST_COLS)].copy()
            for col in _FIXTURE_HIST_COLS:
                hist_fix[col] = pd.to_numeric(hist_fix[col], errors="coerce").fillna(0.0)

            sides = hist_fix.groupby("fixture_id")["opponent_club_id"].agg(["min", "max"])
            min_side = hist_fix["fixture_id"].map(sides.iloc[:, 0])
            max_side = hist_fix["fixture_id"].map(sides.iloc[:, 1])
            two_sided = min_side != max_side

            hist_fix = hist_fix.loc[two_sided].copy()
            if not hist_fix.empty:
                hist_fix["club"] = (min_side.loc[two_sided] + max_side.loc[two_sided] - hist_fix["opponent_club_id"]).astype(int)
                club_fx = hist_fix.groupby(["fixture_id", "club"], as_index=False)["expected_goals"].sum()
                if not club_fx.empty:
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
        if features_df.empty:
            return super(DefXgShrinkChallengerModel, self).predict(features_df, horizon)

        feat = features_df.copy()

        # Step 1: Smooth Continuous Threat-Adaptive Defender Shrinkage
        if not self._threat_hist.empty and "per90_xg" in feat.columns:
            positions = feat.drop_duplicates("player_id").set_index("player_id")["position_id"]
            hist = self._threat_hist
            pos = hist["player_id"].map(positions).fillna(_MIDFIELDER)

            by_pos = hist.groupby(pos)[["expected_goals", "threat", "minutes"]].sum()
            pos_xg_rate = (by_pos["expected_goals"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()
            pos_threat_rate = (by_pos["threat"] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()

            last = hist.groupby("player_id")["gameweek_id"].transform("max")
            weight = _DECAY ** (last - hist["gameweek_id"])

            sums = pd.DataFrame({
                "xg": hist["expected_goals"] * weight,
                "threat": hist["threat"] * weight,
                "mins": hist["minutes"] * weight,
                "player_id": hist["player_id"],
            }).groupby("player_id").sum()

            player_pos = positions.reindex(sums.index).fillna(_MIDFIELDER)
            base_xg_prior = player_pos.map(pos_xg_rate).fillna(0.0)
            base_threat_prior = player_pos.map(pos_threat_rate).fillna(10.0)

            shrunk_threat = (sums["threat"] + 360.0 * base_threat_prior / 90.0) / (sums["mins"] + 360.0) * 90.0

            is_def = player_pos.eq(2)
            rel_minutes = sums["mins"] / (sums["mins"] + self.m_zero)
            z_threat = (shrunk_threat - self.tau_threat) / max(self.s_threat, 0.1)
            sigmoid_threat = 1.0 / (1.0 + np.exp(-np.clip(z_threat, -10.0, 10.0)))
            sigma_oop = np.where(is_def, rel_minutes * sigmoid_threat, 0.0)

            def_threat_mean = pos_threat_rate.get(2, 10.0)
            rel_threat = np.clip((shrunk_threat - def_threat_mean) / max(def_threat_mean, 1.0), 0.0, 2.5)
            adj_prior = np.where(
                is_def,
                base_xg_prior * (1.0 + sigma_oop * self.gamma_oop * rel_threat),
                base_xg_prior,
            )

            k_def = _POSITION_K.get(2, 2400.0)
            k_vec = np.where(
                is_def,
                (1.0 - sigma_oop) * k_def + sigma_oop * self.k_oop,
                _BASE_K,
            )

            new_rates = (sums["xg"] + k_vec * adj_prior / 90.0) / (sums["mins"] + k_vec) * 90.0
            old_rates = shrunk_xg_rates(self._xg_hist, positions, {})
            ratio = (new_rates / old_rates.where(old_rates > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)
            feat["per90_xg"] = feat["per90_xg"] * feat["player_id"].map(ratio).fillna(1.0).to_numpy()

        # Step 2: Truly Asymmetric Convex-Balanced Clean Sheet Hazard
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
                    z.loc[valid] = (1.0 - w) * z_fdr.loc[valid] + w * z_opp

            beta_cs = self.rho_cs * self.alpha_cs
            hazard_mult = np.where(
                z >= 0.0,
                np.exp(np.clip(self.alpha_cs * z, 0.0, 0.60)),
                np.exp(np.clip(beta_cs * z, -0.30, 0.0)),
            )

            feat["per90_goals_conceded"] = (
                pd.to_numeric(feat["per90_goals_conceded"], errors="coerce").fillna(1.2) * hazard_mult
            )

        return super(DefXgShrinkChallengerModel, self).predict(feat, horizon)


def _make_variant(
    name: str,
    tau_threat: float,
    k_oop: float,
    alpha_cs: float,
) -> type[_BaseEXT34]:
    return type(
        name,
        (_BaseEXT34,),
        {
            "variant_name": name,
            "tau_threat": float(tau_threat),
            "k_oop": float(k_oop),
            "alpha_cs": float(alpha_cs),
            "m_zero": 360.0,
            "gamma_oop": 0.20 if tau_threat <= 15.0 else 0.25,
            "s_threat": 3.0,
            "rho_cs": 0.25,
            "k_cs": 8.0,
        },
    )


_GRID = (
    ("ext_34_t15_k800_a18", 15.0, 800.0, 0.18),
    ("ext_34_t15_k800_a22", 15.0, 800.0, 0.22),
    ("ext_34_t15_k600_a22", 15.0, 600.0, 0.22),
    ("ext_34_t18_k800_a18", 18.0, 800.0, 0.18),
    ("ext_34_t18_k800_a22", 18.0, 800.0, 0.22),
    ("ext_34_t18_k600_a22", 18.0, 600.0, 0.22),
)

_MANIFEST = (
    "features.player_id",
    "features.position_id",
    "features.per90_xg",
    "features.per90_goals_conceded",
    "features.difficulty",
    "features.opponent_id",
    "features.opponent_club_id",
    "history.player_id",
    "history.gameweek_id",
    "history.minutes",
    "history.expected_goals",
    "history.threat",
    "history.fixture_id",
    "history.opponent_club_id",
    "local.xg",
    "local.threat",
    "local.mins",
    "local.club",
)

PROTOTYPES = {name: _make_variant(name, tau, k, a) for name, tau, k, a in _GRID}
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
COMPONENTS = {name: "xp_goals" for name in PROTOTYPES}
