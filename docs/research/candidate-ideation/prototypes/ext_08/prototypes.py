from __future__ import annotations

import math

import numpy as np
import pandas as pd

from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel
from models.base import resolve_asof_target_gw
from models.ml_panel_features import positional_price_tier_prior
from models.scoring_matrix import event_points


def joint_factors(
    goals: float,
    assists: float,
    exposure: float,
    prior_goals: float,
    prior_assists: float,
    k_mix: float,
    alpha: float,
) -> tuple[float, float]:
    prior_total = prior_goals + prior_assists
    if prior_total <= 0.0 or exposure <= 0.0:
        return 1.0, 1.0
    total = goals + assists
    rate = (12.0 * prior_total + total) / (12.0 + exposure)
    share = (k_mix * prior_goals / prior_total + goals) / (k_mix + total)
    joint = (rate * share, rate * (1.0 - share))
    independent = ((12.0 * prior_goals + goals) / (12.0 + exposure),
                   (12.0 * prior_assists + assists) / (12.0 + exposure))
    bound = math.log(1.10)
    factors: list[float] = []
    for coupled, reference in zip(joint, independent, strict=True):
        if not math.isfinite(coupled) or not math.isfinite(reference) or coupled <= 0.0 or reference <= 0.0:
            factors.append(1.0)
        else:
            factors.append(math.exp(alpha * 0.25 * float(np.clip(math.log(coupled / reference), -bound, bound))))
    return factors[0], factors[1]


class JointAllocationModel(AdaptiveCausalChallengerModel):
    k_mix: float = 2.0

    def __init__(self) -> None:
        super().__init__()
        self._joint_history = pd.DataFrame()
        self._joint_factors: dict[tuple[int, int], tuple[float, float]] = {}

    @property
    def name(self) -> str:
        return f"ext_08_k{int(self.k_mix)}"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        columns = ["player_id", "fixture_id", "gameweek_id", "minutes", "expected_goals", "expected_assists", "price"]
        if not set(columns).issubset(history_df.columns):
            self._joint_history = pd.DataFrame()
            return
        self._joint_history = history_df[columns].apply(pd.to_numeric, errors="coerce").copy()

    def _factor_cache(self, features_df: pd.DataFrame) -> dict[tuple[int, int], tuple[float, float]]:
        if features_df.empty or self._joint_history.empty:
            return {}
        cutoff = resolve_asof_target_gw(features_df, self._joint_history)
        if cutoff < 20:
            return {}
        history = self._joint_history
        prior = history[history["gameweek_id"] < cutoff].drop_duplicates(["player_id", "fixture_id"])
        alpha = float(np.clip((len(prior) - 3500.0) / 4000.0, 0.0, 1.0))
        if alpha <= 0.0:
            return {}
        played = prior[(prior["minutes"] > 0.0)].dropna()
        if played.empty:
            return {}
        weight = np.power(0.95, cutoff - 1.0 - played["gameweek_id"].to_numpy())
        weighted = played.assign(
            weighted_xg=played["expected_goals"].clip(lower=0.0).to_numpy() * weight,
            weighted_xa=played["expected_assists"].clip(lower=0.0).to_numpy() * weight,
            exposure90=played["minutes"].to_numpy() / 90.0 * weight,
        )
        sums = weighted.groupby("player_id")[["weighted_xg", "weighted_xa", "exposure90"]].sum()
        prices = prior.sort_values(["gameweek_id", "fixture_id"]).drop_duplicates("player_id").set_index("player_id")["price"]
        factors: dict[tuple[int, int], tuple[float, float]] = {}
        for row in features_df.itertuples(index=False):
            player = int(row.player_id)
            position = int(row.position_id)
            fixture = int(row.fixture_id)
            if position not in (3, 4) or fixture < 0 or player not in sums.index or player not in prices.index:
                continue
            price = float(prices.loc[player])
            if not math.isfinite(price):
                continue
            totals = sums.loc[player]
            factors[(player, fixture)] = joint_factors(
                float(totals["weighted_xg"]), float(totals["weighted_xa"]), float(totals["exposure90"]),
                positional_price_tier_prior(position, price, metric="xg90"),
                positional_price_tier_prior(position, price, metric="xa90"), self.k_mix, alpha,
            )
        return factors

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._joint_factors = self._factor_cache(features_df)
        return super().predict(features_df, horizon)

    def _project_event_components(
        self, row: pd.Series, position: str, expected_minutes: float,
        *, clean_sheet_minutes: float, p_sixty_mins: float,
    ) -> dict[str, float]:
        components = super()._project_event_components(
            row, position, expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes, p_sixty_mins=p_sixty_mins,
        )
        factors = self._joint_factors.get((int(row["player_id"]), int(row["fixture_id"])))
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


class JointAllocationK4Model(JointAllocationModel):
    k_mix = 4.0


class JointAllocationK8Model(JointAllocationModel):
    k_mix = 8.0


class JointAllocationK16Model(JointAllocationModel):
    k_mix = 16.0


PROTOTYPES = {
    "ext_08_k2": JointAllocationModel,
    "ext_08_k4": JointAllocationK4Model,
    "ext_08_k8": JointAllocationK8Model,
    "ext_08_k16": JointAllocationK16Model,
}
_MANIFEST = (
    "features.player_id", "features.fixture_id", "features.gameweek_id", "features.position_id",
    "history.player_id", "history.fixture_id", "history.gameweek_id", "history.minutes",
    "history.expected_goals", "history.expected_assists", "history.price",
    "history.weighted_xg", "history.weighted_xa", "history.exposure90", "local.xbps",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
