from __future__ import annotations

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import _DECAY, DefXgShrinkChallengerModel

_GK_HIST_COLS = ("player_id", "fixture_id", "gameweek_id", "opponent_club_id", "minutes", "saves", "threat")


class _BaseExt19Model(DefXgShrinkChallengerModel):
    """DefXgShrink Champion + EB goalkeeper save shrinkage + opponent threat-volume save elasticity."""

    k_gk: float = 720.0
    xi_saves: float = 0.35
    club_k: float = 6.0
    n_min: float = 3500.0
    n_full: float = 7500.0
    variant_name: str = "ext_19_base"

    def __init__(self) -> None:
        super().__init__()
        self._gk_hist = pd.DataFrame()

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_GK_HIST_COLS).issubset(history_df.columns):
            self._gk_hist = pd.DataFrame()
            return
        self._gk_hist = history_df[list(_GK_HIST_COLS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._gk_hist.empty or features_df.empty or "per90_saves" not in features_df.columns:
            return super().predict(features_df, horizon)
        target_gw = resolve_asof_target_gw(features_df, self._gk_hist)
        prior = self._gk_hist[(self._gk_hist["gameweek_id"] < target_gw) & (self._gk_hist["minutes"] > 0)]
        if prior.empty:
            return super().predict(features_df, horizon)

        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        gk_prior = prior[prior["player_id"].map(positions).eq(1)]
        if gk_prior.empty:
            return super().predict(features_df, horizon)

        gk_mean = float(gk_prior["saves"].sum() / max(1.0, float(gk_prior["minutes"].sum())) * 90.0)
        last = gk_prior.groupby("player_id")["gameweek_id"].transform("max")
        w = _DECAY ** (last - gk_prior["gameweek_id"])
        sums = pd.DataFrame({
            "saves": gk_prior["saves"] * w,
            "mins": gk_prior["minutes"] * w,
            "player_id": gk_prior["player_id"],
        }).groupby("player_id").sum()

        rate_k = (sums["saves"] + self.k_gk * gk_mean / 90.0) / (sums["mins"] + self.k_gk) * 90.0
        rate_360 = (sums["saves"] + 360.0 * gk_mean / 90.0) / (sums["mins"] + 360.0) * 90.0
        eb_ratio = (rate_k / rate_360.where(rate_360 > 1e-6)).fillna(1.0).clip(0.5, 2.0)

        sides = prior.groupby("fixture_id")["opponent_club_id"].agg(["min", "max"])
        fx = prior.join(sides, on="fixture_id")
        fx = fx[fx["min"] != fx["max"]]
        fx = fx.assign(club_id=fx["min"] + fx["max"] - fx["opponent_club_id"])
        club_thr = fx.groupby(["fixture_id", "club_id"], as_index=False)["threat"].sum()
        league_thr = max(10.0, float(club_thr["threat"].mean())) if not club_thr.empty else 120.0
        t_grp = club_thr.groupby("club_id").agg(n=("threat", "size"), thr=("threat", "sum"))
        thr_map = ((t_grp["thr"] + self.club_k * league_thr) / (t_grp["n"] + self.club_k)).to_dict()

        n_seed = float(features_df.drop_duplicates("player_id").get("n_starts_historical", pd.Series(0.0)).sum())
        n_eff = 0.5 * n_seed + float(len(prior))
        omega = float(np.clip((n_eff - self.n_min) / max(1.0, self.n_full - self.n_min), 0.0, 1.0))

        feat = features_df.copy()
        opp_thr = feat["opponent_id"].map(thr_map).fillna(league_thr).to_numpy(float)
        opp_mult = np.clip(1.0 + omega * self.xi_saves * ((opp_thr - league_thr) / league_thr), 0.75, 1.30)
        is_gk = (feat["position_id"] == 1) & (feat["fixture_id"] >= 0)
        gk_eb = feat["player_id"].map(eb_ratio).fillna(1.0).to_numpy(float)
        feat["per90_saves"] = (
            pd.to_numeric(feat["per90_saves"], errors="coerce").fillna(0.0).to_numpy(float)
            * np.where(is_gk, gk_eb * opp_mult, 1.0)
        )
        return super().predict(feat, horizon)


class Ext19K720Xi030(_BaseExt19Model):
    k_gk = 720.0
    xi_saves = 0.30
    variant_name = "ext_19_k720_xi030"


class Ext19K720Xi045(_BaseExt19Model):
    k_gk = 720.0
    xi_saves = 0.45
    variant_name = "ext_19_k720_xi045"


class Ext19K900Xi035(_BaseExt19Model):
    k_gk = 900.0
    xi_saves = 0.35
    variant_name = "ext_19_k900_xi035"


class Ext19K900Xi050(_BaseExt19Model):
    k_gk = 900.0
    xi_saves = 0.50
    variant_name = "ext_19_k900_xi050"


class Ext19K540Xi035(_BaseExt19Model):
    k_gk = 540.0
    xi_saves = 0.35
    variant_name = "ext_19_k540_xi035"


class Ext19K1080Xi040(_BaseExt19Model):
    k_gk = 1080.0
    xi_saves = 0.40
    variant_name = "ext_19_k1080_xi040"


_COMMON_FEATURES: tuple[str, ...] = (
    "features.player_id",
    "features.club_id",
    "features.opponent_id",
    "features.position_id",
    "features.fixture_id",
    "features.gameweek_id",
    "features.per90_saves",
    "features.n_starts_historical",
    "history.player_id",
    "history.fixture_id",
    "history.gameweek_id",
    "history.opponent_club_id",
    "history.minutes",
    "history.saves",
    "history.threat",
    "local.min",
    "local.max",
    "local.thr",
    "local.n",
    "local.mins",
)

PROTOTYPES: dict[str, type[_BaseExt19Model]] = {
    "ext_19_k720_xi030": Ext19K720Xi030,
    "ext_19_k720_xi045": Ext19K720Xi045,
    "ext_19_k900_xi035": Ext19K900Xi035,
    "ext_19_k900_xi050": Ext19K900Xi050,
    "ext_19_k540_xi035": Ext19K540Xi035,
    "ext_19_k1080_xi040": Ext19K1080Xi040,
}

FEATURES: dict[str, tuple[str, ...]] = {name: _COMMON_FEATURES for name in PROTOTYPES}
