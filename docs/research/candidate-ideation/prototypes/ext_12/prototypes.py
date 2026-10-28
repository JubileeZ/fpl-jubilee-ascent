from __future__ import annotations

import math

import numpy as np
import pandas as pd

from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel
from models.base import resolve_asof_target_gw
from models.ml_panel_features import positional_price_tier_prior
from models.scoring_matrix import event_points

_Z_GRID = np.linspace(-2.5, 2.5, 21)
_PRIOR_W0 = np.exp(-0.5 * _Z_GRID**2)
_PRIOR_W0 /= _PRIOR_W0.sum()
_BOUND_LOG110 = math.log(1.10)


def compute_change_factors(
    played_history: pd.DataFrame,
    mu_prior_g: float,
    mu_prior_a: float,
    change_hazard: float,
    dispersion: float,
    alpha: float,
    horizon_step: int,
) -> tuple[float, float]:
    if mu_prior_g <= 0.0 or mu_prior_a <= 0.0 or played_history.empty:
        return 1.0, 1.0
    exposure_sum = float(played_history["minutes"].sum()) / 90.0
    if exposure_sum <= 0.0:
        return 1.0, 1.0
    s_i = exposure_sum / (exposure_sum + 12.0)

    factors: list[float] = []
    for metric, mu_0 in (("expected_goals", mu_prior_g), ("expected_assists", mu_prior_a)):
        m0 = math.log(mu_0) - 0.125
        theta_grid = m0 + _Z_GRID * 0.5
        w_cp = _PRIOR_W0.copy()
        w_stat = _PRIOR_W0.copy()

        for row in played_history.itertuples(index=False):
            v_t = float(row.minutes) / 90.0
            y_t = max(float(getattr(row, metric)), 0.0)
            if v_t <= 0.0:
                continue
            pred_cp = (1.0 - change_hazard) * w_cp + change_hazard * _PRIOR_W0
            pred_stat = w_stat

            term1 = v_t * np.exp(0.5 * theta_grid)
            term2 = y_t * np.exp(-0.5 * theta_grid) if y_t > 0.0 else 0.0
            term3 = 2.0 * math.sqrt(v_t * y_t) if y_t > 0.0 else 0.0
            ll = -(2.0 / dispersion) * (term1 + term2 - term3)
            ll -= np.max(ll)
            l_weights = np.exp(ll)

            post_cp = pred_cp * l_weights
            denom_cp = post_cp.sum()
            w_cp = post_cp / denom_cp if denom_cp > 0.0 else pred_cp

            post_stat = pred_stat * l_weights
            denom_stat = post_stat.sum()
            w_stat = post_stat / denom_stat if denom_stat > 0.0 else pred_stat

        q_cp = float(np.sum(((1.0 - change_hazard) * w_cp + change_hazard * _PRIOR_W0) * np.exp(theta_grid)))
        q_stat = float(np.sum(w_stat * np.exp(theta_grid)))
        decay = (1.0 - change_hazard) ** horizon_step
        rate_forecast = decay * q_cp + (1.0 - decay) * mu_0

        if q_stat <= 0.0 or rate_forecast <= 0.0 or not math.isfinite(rate_forecast) or not math.isfinite(q_stat):
            factors.append(1.0)
        else:
            log_ratio = math.log(rate_forecast / q_stat)
            clipped = float(np.clip(log_ratio, -_BOUND_LOG110, _BOUND_LOG110))
            factors.append(math.exp(alpha * s_i * 0.25 * clipped))

    return factors[0], factors[1]


class AttackChangeDetectionModel(AdaptiveCausalChallengerModel):
    change_hazard: float = 1.0 / 48.0
    dispersion: float = 1.0

    def __init__(self) -> None:
        super().__init__()
        self._change_history = pd.DataFrame()
        self._change_factors: dict[tuple[int, int], tuple[float, float]] = {}

    @property
    def name(self) -> str:
        h_tag = "h48" if abs(self.change_hazard - (1.0 / 48.0)) < 1e-4 else "h24"
        d_tag = "phi05" if abs(self.dispersion - 0.5) < 1e-4 else "phi10"
        return f"ext_12_{h_tag}_{d_tag}"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        columns = ["player_id", "fixture_id", "gameweek_id", "minutes", "expected_goals", "expected_assists", "price"]
        if not set(columns).issubset(history_df.columns):
            self._change_history = pd.DataFrame()
            return
        self._change_history = history_df[columns].apply(pd.to_numeric, errors="coerce").copy()

    def _factor_cache(self, features_df: pd.DataFrame) -> dict[tuple[int, int], tuple[float, float]]:
        if features_df.empty or self._change_history.empty:
            return {}
        cutoff = resolve_asof_target_gw(features_df, self._change_history)
        if cutoff < 20:
            return {}
        history = self._change_history
        prior = history[history["gameweek_id"] < cutoff].drop_duplicates(["player_id", "fixture_id"])
        alpha = float(np.clip((len(prior) - 3500.0) / 4000.0, 0.0, 1.0))
        if alpha <= 0.0:
            return {}
        played = prior[(prior["minutes"] > 0.0)].dropna()
        if played.empty:
            return {}

        prices = prior.sort_values(["gameweek_id", "fixture_id"]).drop_duplicates("player_id").set_index("player_id")["price"]
        played_grouped = {pid: df.sort_values(["gameweek_id", "fixture_id"]) for pid, df in played.groupby("player_id")}

        factors: dict[tuple[int, int], tuple[float, float]] = {}
        for row in features_df.itertuples(index=False):
            player = int(row.player_id)
            position = int(row.position_id)
            fixture = int(row.fixture_id)
            gw = int(row.gameweek_id)
            if position not in (3, 4) or fixture < 0 or player not in played_grouped or player not in prices.index:
                continue
            price = float(prices.loc[player])
            if not math.isfinite(price):
                continue
            player_history = played_grouped[player]
            horizon_step = max(gw - cutoff, 0)
            mu_g = positional_price_tier_prior(position, price, metric="xg90")
            mu_a = positional_price_tier_prior(position, price, metric="xa90")
            factors[(player, fixture)] = compute_change_factors(
                player_history, mu_g, mu_a, self.change_hazard, self.dispersion, alpha, horizon_step,
            )
        return factors

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._change_factors = self._factor_cache(features_df)
        return super().predict(features_df, horizon)

    def _project_event_components(
        self, row: pd.Series, position: str, expected_minutes: float,
        *, clean_sheet_minutes: float, p_sixty_mins: float,
    ) -> dict[str, float]:
        components = super()._project_event_components(
            row, position, expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes, p_sixty_mins=p_sixty_mins,
        )
        factors = self._change_factors.get((int(row["player_id"]), int(row["fixture_id"])))
        if factors is None:
            return components
        goal_unit = event_points("goals", position, 1.0)
        old_goals = components["xp_goals"] / goal_unit
        old_assists = components["xp_assists"] / 3.0
        delta_goals = old_goals * (factors[0] - 1.0)
        delta_assists = old_assists * (factors[1] - 1.0)
        delta_points = goal_unit * delta_goals + 3.0 * delta_assists
        components["xp_goals"] += goal_unit * delta_goals
        components["xp_assists"] += 3.0 * delta_assists
        components["projected_points"] += delta_points
        components["xbps"] += 24.0 * delta_goals + 12.0 * delta_assists
        return components


class ChangeH48Phi05Model(AttackChangeDetectionModel):
    change_hazard = 1.0 / 48.0
    dispersion = 0.5


class ChangeH48Phi10Model(AttackChangeDetectionModel):
    change_hazard = 1.0 / 48.0
    dispersion = 1.0


class ChangeH24Phi05Model(AttackChangeDetectionModel):
    change_hazard = 1.0 / 24.0
    dispersion = 0.5


class ChangeH24Phi10Model(AttackChangeDetectionModel):
    change_hazard = 1.0 / 24.0
    dispersion = 1.0


PROTOTYPES = {
    "ext_12_h48_phi05": ChangeH48Phi05Model,
    "ext_12_h48_phi10": ChangeH48Phi10Model,
    "ext_12_h24_phi05": ChangeH24Phi05Model,
    "ext_12_h24_phi10": ChangeH24Phi10Model,
}

_MANIFEST = (
    "features.player_id", "features.fixture_id", "features.gameweek_id", "features.position_id",
    "history.player_id", "history.fixture_id", "history.gameweek_id", "history.minutes",
    "history.expected_goals", "history.expected_assists", "history.price",
    "local.xbps",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
