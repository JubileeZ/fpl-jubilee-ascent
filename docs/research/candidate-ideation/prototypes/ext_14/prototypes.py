from __future__ import annotations

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel, _BASE_K, _POSITION_K, shrunk_xg_rates
from models.multi_feature_assist_challenger import _club_fixture_table
from models.native_scoring_context import native_scoring_row
from models.scoring_matrix import event_points

_DECAY = 0.95
_HIST_COLS = (
    "player_id",
    "fixture_id",
    "gameweek_id",
    "opponent_club_id",
    "was_home",
    "minutes",
    "expected_goals",
    "expected_goals_conceded",
    "threat",
    "creativity",
)


def _shrunk_col_rates(hist: pd.DataFrame, positions: pd.Series, col: str, k_val: float = _BASE_K) -> pd.Series:
    pos = hist["player_id"].map(positions).fillna(3)
    by_pos = hist.groupby(pos)[[col, "minutes"]].sum()
    pos_rate = by_pos[col] / by_pos["minutes"].clip(lower=1.0) * 90.0
    last = hist.groupby("player_id")["gameweek_id"].transform("max")
    weight = _DECAY ** (last - hist["gameweek_id"])
    sums = pd.DataFrame(
        {"events": hist[col] * weight, "mins": hist["minutes"] * weight, "player_id": hist["player_id"]}
    ).groupby("player_id").sum()
    player_pos = positions.reindex(sums.index).fillna(3)
    prior = player_pos.map(pos_rate.to_dict()).fillna(0.0)
    return (sums["events"] + k_val * prior / 90.0) / (sums["mins"] + k_val) * 90.0


class _BaseExt14Model(DefXgShrinkChallengerModel):
    alpha_tempo: float = 0.14
    beta_trans: float = 0.10
    club_k: float = 6.0
    n_min: float = 3500.0
    n_full: float = 7500.0
    variant_name: str = "ext_14_base"

    def __init__(self) -> None:
        super().__init__()
        self._tempo_hist = pd.DataFrame()
        self._eta_map: dict[tuple[int, int], float] = {}

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_HIST_COLS).issubset(history_df.columns):
            self._tempo_hist = pd.DataFrame()
            return
        hist = history_df[list(_HIST_COLS)].copy()
        num_cols = [c for c in _HIST_COLS if c != "was_home"]
        hist[num_cols] = hist[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        self._tempo_hist = hist

    def _compute_eta_map(self, features_df: pd.DataFrame) -> dict[tuple[int, int], float]:
        if self._tempo_hist.empty or features_df.empty:
            return {}
        target_gw = resolve_asof_target_gw(features_df, self._tempo_hist)
        prior = self._tempo_hist[self._tempo_hist["gameweek_id"] < target_gw]
        if prior.empty:
            return {}

        n_seed = float(
            pd.to_numeric(
                features_df.drop_duplicates(subset=["player_id"]).get("n_starts_historical", pd.Series(0.0)),
                errors="coerce",
            )
            .fillna(0.0)
            .sum()
        )
        n_eff = 0.5 * n_seed + float((prior["minutes"] > 0).sum())
        omega = float(np.clip((n_eff - self.n_min) / max(1.0, self.n_full - self.n_min), 0.0, 1.0))
        if omega <= 1e-6:
            return {}

        club_fx = _club_fixture_table(prior).copy()
        if club_fx.empty:
            return {}
        w_m = _DECAY ** np.maximum(0.0, float(target_gw - 1) - club_fx["gameweek_id"].to_numpy(float))
        club_fx["w"] = w_m
        club_fx["w_xg_f"] = club_fx["xg_for"].to_numpy(float) * w_m
        club_fx["w_xg_a"] = club_fx["xg_against"].to_numpy(float) * w_m
        league_xg = max(0.5, float(club_fx["w_xg_f"].sum() / max(1e-9, club_fx["w"].sum())))
        grp = club_fx.groupby("club").agg(w_sum=("w", "sum"), xg_f=("w_xg_f", "sum"), xg_a=("w_xg_a", "sum"))
        tempo_map = ((grp["xg_f"] + grp["xg_a"] + self.club_k * 2.0 * league_xg) / (grp["w_sum"] + self.club_k)).to_dict()
        att_map = ((grp["xg_f"] + self.club_k * league_xg) / (grp["w_sum"] + self.club_k)).to_dict()

        feat = features_df.copy()
        positions = feat.drop_duplicates(subset=["player_id"]).set_index("player_id")["position_id"]
        played = prior[prior["minutes"] > 0]
        if not played.empty:
            tau_s = _shrunk_col_rates(played, positions, "threat", _BASE_K)
            kap_s = _shrunk_col_rates(played, positions, "creativity", _BASE_K)
            thr_f = pd.to_numeric(feat["per90_threat"], errors="coerce").fillna(0.0).to_numpy(float)
            cre_f = pd.to_numeric(feat["per90_creativity"], errors="coerce").fillna(0.0).to_numpy(float)
            thr = feat["player_id"].map(tau_s).fillna(pd.Series(thr_f, index=feat.index)).to_numpy(float)
            cre = feat["player_id"].map(kap_s).fillna(pd.Series(cre_f, index=feat.index)).to_numpy(float)
        else:
            thr = pd.to_numeric(feat["per90_threat"], errors="coerce").fillna(0.0).to_numpy(float)
            cre = pd.to_numeric(feat["per90_creativity"], errors="coerce").fillna(0.0).to_numpy(float)

        raw_dir = np.log((np.maximum(0.0, thr) + 10.0) / (np.maximum(0.0, cre) + 10.0))
        pos_arr = pd.to_numeric(feat["position_id"], errors="coerce").fillna(3).to_numpy(int)
        directness = np.zeros(len(feat), dtype=float)
        for p in (2, 3, 4):
            mask = pos_arr == p
            if mask.any():
                vals = raw_dir[mask]
                mu_p = float(np.mean(vals))
                sd_p = max(1e-6, float(np.std(vals)))
                directness[mask] = np.tanh((vals - mu_p) / sd_p)

        own_t = feat["club_id"].map(tempo_map).fillna(2.0 * league_xg).to_numpy(float)
        opp_t = feat["opponent_id"].map(tempo_map).fillna(2.0 * league_xg).to_numpy(float)
        opp_att = feat["opponent_id"].map(att_map).fillna(league_xg).to_numpy(float)
        tempo_idx = (0.5 * (own_t + opp_t) - 2.0 * league_xg) / (2.0 * league_xg)

        eta = omega * (
            self.alpha_tempo * tempo_idx
            + self.beta_trans * np.maximum(0.0, directness) * ((opp_att - league_xg) / league_xg)
        )
        eta_map: dict[tuple[int, int], float] = {}
        fids = pd.to_numeric(feat["fixture_id"], errors="coerce").fillna(-1).to_numpy(int)
        pids = pd.to_numeric(feat["player_id"], errors="coerce").fillna(-1).to_numpy(int)
        gws = pd.to_numeric(feat["gameweek_id"], errors="coerce").fillna(target_gw).to_numpy(int)
        outfield = np.isin(pos_arr, [2, 3, 4]) & (fids >= 0)

        for gw in np.unique(gws):
            gw_out = outfield & (gws == gw)
            if not gw_out.any():
                continue
            mean_eta = float(np.mean(eta[gw_out]))
            eta_c = np.clip(eta[gw_out] - mean_eta, -0.18, 0.18)
            for pid, fid, val in zip(pids[gw_out], fids[gw_out], eta_c):
                eta_map[(int(pid), int(fid))] = float(val)
        return eta_map

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._eta_map = self._compute_eta_map(features_df)
        if self._xg_hist.empty or features_df.empty:
            return super().predict(features_df, horizon)
        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        new = shrunk_xg_rates(self._xg_hist, positions, _POSITION_K)
        old = shrunk_xg_rates(self._xg_hist, positions, {})
        ratio = (new / old.where(old > 1e-9)).fillna(1.0).clip(0.1, 10.0)
        features = features_df.copy()
        features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()
        return super(DefXgShrinkChallengerModel, self).predict(features, horizon)

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float,
    ) -> dict[str, float]:
        components = super()._project_event_components(
            row, position, expected_minutes, clean_sheet_minutes=clean_sheet_minutes, p_sixty_mins=p_sixty_mins
        )
        fixture = row.get("fixture_id")
        if fixture is None or pd.isna(fixture) or expected_minutes <= 0.0:
            return components
        pid = int(row["player_id"])
        fid = int(fixture)
        eta_val = self._eta_map.get((pid, fid))
        if eta_val is None or abs(eta_val) <= 1e-12:
            return components

        rules_version = native_scoring_row(row)
        unit_goal_pts = event_points("goals", position, 1.0, rules_version=rules_version)
        old_goals = components["xp_goals"] / max(1.0, unit_goal_pts)
        new_goals = old_goals * float(np.exp(eta_val))
        new_goal_pts = event_points("goals", position, new_goals, rules_version=rules_version)
        components["projected_points"] += new_goal_pts - components["xp_goals"]
        components["xbps"] += 24.0 * (new_goals - old_goals)
        components["xp_goals"] = new_goal_pts

        old_assists = components["xp_assists"] / 3.0
        new_assists = old_assists * float(np.exp(0.75 * eta_val))
        new_assist_pts = event_points("assists", position, new_assists, rules_version=rules_version)
        components["projected_points"] += new_assist_pts - components["xp_assists"]
        components["xbps"] += 12.0 * (new_assists - old_assists)
        components["xp_assists"] = new_assist_pts
        return components


class Ext14A10B08Model(_BaseExt14Model):
    alpha_tempo = 0.10
    beta_trans = 0.08
    variant_name = "ext_14_a10_b08"


class Ext14A14B10Model(_BaseExt14Model):
    alpha_tempo = 0.14
    beta_trans = 0.10
    variant_name = "ext_14_a14_b10"


class Ext14A18B12Model(_BaseExt14Model):
    alpha_tempo = 0.18
    beta_trans = 0.12
    variant_name = "ext_14_a18_b12"


class Ext14A12B15Model(_BaseExt14Model):
    alpha_tempo = 0.12
    beta_trans = 0.15
    variant_name = "ext_14_a12_b15"


class Ext14A08B12Model(_BaseExt14Model):
    alpha_tempo = 0.08
    beta_trans = 0.12
    variant_name = "ext_14_a08_b12"


class Ext14A15B06Model(_BaseExt14Model):
    alpha_tempo = 0.15
    beta_trans = 0.06
    variant_name = "ext_14_a15_b06"


_COMMON_FEATURES: tuple[str, ...] = (
    "features.player_id",
    "features.club_id",
    "features.opponent_id",
    "features.position_id",
    "features.fixture_id",
    "features.gameweek_id",
    "features.n_starts_historical",
    "features.per90_xg",
    "features.per90_xa",
    "features.per90_threat",
    "features.per90_creativity",
    "history.player_id",
    "history.fixture_id",
    "history.gameweek_id",
    "history.opponent_club_id",
    "history.was_home",
    "history.minutes",
    "history.expected_goals",
    "history.expected_goals_conceded",
    "history.threat",
    "history.creativity",
    "local.events",
    "local.mins",
    "local.w",
    "local.w_xg_f",
    "local.w_xg_a",
    "local.club",
    "local.w_sum",
    "local.xg_f",
    "local.xg_a",
    "local.xg_for",
    "local.xg_against",
    "local.xbps",
)

PROTOTYPES = {
    "ext_14_a10_b08": Ext14A10B08Model,
    "ext_14_a14_b10": Ext14A14B10Model,
    "ext_14_a18_b12": Ext14A18B12Model,
    "ext_14_a12_b15": Ext14A12B15Model,
    "ext_14_a08_b12": Ext14A08B12Model,
    "ext_14_a15_b06": Ext14A15B06Model,
}

FEATURES = {name: _COMMON_FEATURES for name in PROTOTYPES}
