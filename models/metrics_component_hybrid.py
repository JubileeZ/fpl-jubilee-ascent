"""Calibrated event-component projection model.

The model predicts event quantities/probabilities and reconstructs points through
the scoring matrix. ``fit`` is optional and must receive only pre-cutoff history.
"""

import math
from collections import defaultdict

import numpy as np
import pandas as pd

from models.base import BaseModel, iter_feature_rows
from models.scoring_matrix import event_points

_POS_CODE = {1: "GK", 2: "D", 3: "M", 4: "F"}
_CLEAN_SHEET_POINTS = {"GK": 4.0, "D": 4.0, "M": 1.0, "F": 0.0}
_DEFAULT_GOAL_WEIGHTS = np.array([0.75, 0.25])
_DEFAULT_ASSIST_WEIGHTS = np.array([0.75, 0.25])


def _number(row: pd.Series, column: str, default: float) -> float:
    value = row.get(column, default)
    return default if value is None or pd.isna(value) else float(value)


def _optional_number(row: pd.Series, column: str) -> float | None:
    value = row.get(column)
    return None if value is None or pd.isna(value) else float(value)


def _poisson_pmf(k: int, lmbda: float) -> float:
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    return (lmbda**k) * math.exp(-lmbda) / math.factorial(k)


def _poisson_cdf_complement(threshold: int, lmbda: float) -> float:
    """Return P(X >= threshold) for X ~ Poisson(lmbda)."""
    if lmbda <= 0:
        return 0.0
    cdf = sum(_poisson_pmf(k, lmbda) for k in range(threshold))
    return min(max(1.0 - cdf, 0.0), 1.0)


def _expected_poisson_floor(lmbda: float, divisor: int) -> float:
    """Return E[floor(X / divisor)] for a Poisson random variable."""
    if lmbda <= 0:
        return 0.0
    max_k = max(40, int(math.ceil(lmbda + 12.0 * math.sqrt(lmbda + 1.0))))
    return sum(math.floor(k / divisor) * _poisson_pmf(k, lmbda) for k in range(max_k + 1))


def _probability_sixty_minutes(expected_minutes: float) -> float:
    if expected_minutes <= 0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-(expected_minutes - 60.0) / 8.0))


def _fit_metric_weights(
    history_df: pd.DataFrame,
    target_column: str,
    metric_column: str,
    secondary_column: str,
    defaults: np.ndarray,
) -> np.ndarray:
    required = {target_column, metric_column, secondary_column, "minutes"}
    if not required.issubset(history_df.columns):
        return defaults.copy()

    minutes = pd.to_numeric(history_df["minutes"], errors="coerce")
    target = pd.to_numeric(history_df[target_column], errors="coerce") / minutes * 90.0
    metric = pd.to_numeric(history_df[metric_column], errors="coerce") / minutes * 90.0
    secondary = pd.to_numeric(history_df[secondary_column], errors="coerce") / minutes * 0.9
    values = pd.DataFrame({"target": target, "metric": metric, "secondary": secondary}).replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    values = values[minutes.loc[values.index] > 0]
    if len(values) < 20:
        return defaults.copy()

    design = values[["metric", "secondary"]].to_numpy()
    fitted, _, _, _ = np.linalg.lstsq(design, values["target"].to_numpy(), rcond=None)
    fitted = np.clip(fitted, 0.0, 2.0)
    weight = len(values) / (len(values) + 100.0)
    return (weight * fitted + (1.0 - weight) * defaults).astype(float)


class MetricsComponentHybridModel(BaseModel):
    def __init__(self) -> None:
        self.goal_weights = _DEFAULT_GOAL_WEIGHTS.copy()
        self.assist_weights = _DEFAULT_ASSIST_WEIGHTS.copy()

    @property
    def name(self) -> str:
        return "metrics_component_hybrid"

    def fit(self, history_df: pd.DataFrame) -> None:
        """Calibrate attack mappings using history strictly before prediction."""
        self.goal_weights = _fit_metric_weights(
            history_df,
            "goals_scored",
            "expected_goals",
            "threat",
            _DEFAULT_GOAL_WEIGHTS,
        )
        self.assist_weights = _fit_metric_weights(
            history_df,
            "assists",
            "expected_assists",
            "creativity",
            _DEFAULT_ASSIST_WEIGHTS,
        )

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        components: list[dict[str, object]] = []
        bonus_groups: defaultdict[int, list[int]] = defaultdict(list)

        for row, gameweek_id, fixture_id in iter_feature_rows(features_df, horizon):
            if fixture_id is not None and fixture_id < 0:
                components.append({
                    "player_id": int(row["player_id"]),
                    "gameweek_id": gameweek_id,
                    "fixture_id": fixture_id,
                    "projected_points": 0.0,
                    "projected_minutes": 0.0,
                    "xbps": 0.0,
                })
                continue

            availability = min(max(_number(row, "chance_of_playing", 100.0) / 100.0, 0.0), 1.0)
            average_minutes = _number(row, "avg_mins_3gw", 0.0)
            expected_minutes = average_minutes * availability
            diff = _number(row, "difficulty", 3.0)
            fdr_multiplier = max(0.2, (6.0 - diff) / 3.0)
            attack_input = _optional_number(row, "attack_multiplier")
            defence_input = _optional_number(row, "defence_multiplier")
            attack_multiplier = fdr_multiplier if attack_input is None else attack_input
            defence_multiplier = fdr_multiplier if defence_input is None else defence_input
            pos = _POS_CODE.get(int(_number(row, "position_id", 3.0)), "M")

            xg_per90 = _number(row, "per90_xg", 0.0)
            threat_per90 = _number(row, "per90_threat", 0.0)
            raw_goals_per90 = _number(row, "per90_goals", 0.0)
            if xg_per90 > 0 or threat_per90 > 0:
                expected_goals_per90 = (
                    self.goal_weights[0] * xg_per90
                    + self.goal_weights[1] * threat_per90 / 100.0
                )
            else:
                expected_goals_per90 = raw_goals_per90
            expected_goals = expected_goals_per90 * expected_minutes / 90.0 * attack_multiplier

            xa_per90 = _number(row, "per90_xa", 0.0)
            creativity_per90 = _number(row, "per90_creativity", 0.0)
            raw_assists_per90 = _number(row, "per90_assists", 0.0)
            if xa_per90 > 0 or creativity_per90 > 0:
                expected_assists_per90 = (
                    self.assist_weights[0] * xa_per90
                    + self.assist_weights[1] * creativity_per90 / 100.0
                )
            else:
                expected_assists_per90 = raw_assists_per90
            expected_assists = expected_assists_per90 * expected_minutes / 90.0 * attack_multiplier

            gc_per90 = _number(row, "per90_goals_conceded", 1.2)
            lmbda_conceded = max(0.05, gc_per90 * expected_minutes / 90.0 * defence_multiplier)
            prob_clean_sheet = math.exp(-lmbda_conceded) * _probability_sixty_minutes(expected_minutes)
            xp_clean_sheet = prob_clean_sheet * _CLEAN_SHEET_POINTS[pos]
            xp_conceded = -_expected_poisson_floor(lmbda_conceded, 2) if pos in ("GK", "D") else 0.0

            defcon_per90 = _number(row, "per90_defensive_contribution", 0.0)
            lmbda_defcon = max(0.0, defcon_per90 * expected_minutes / 90.0)
            defcon_threshold = 10 if pos == "D" else 12
            prob_defcon = (
                _poisson_cdf_complement(defcon_threshold, lmbda_defcon)
                if pos != "GK"
                else 0.0
            )
            xp_defcon = event_points("defensive_contributions", pos, prob_defcon)

            saves_per90 = _number(row, "per90_saves", 0.0)
            expected_saves = saves_per90 * expected_minutes / 90.0 if pos == "GK" else 0.0
            xp_saves = _expected_poisson_floor(expected_saves, 3)

            yellow_per90 = _number(row, "per90_yellow_cards", 0.0)
            red_per90 = _number(row, "per90_red_cards", 0.0)
            xp_cards = (-yellow_per90 - 3.0 * red_per90) * expected_minutes / 90.0
            penalties_saved = _number(row, "per90_penalties_saved", 0.0) * expected_minutes / 90.0
            penalties_missed = _number(row, "per90_penalties_missed", 0.0) * expected_minutes / 90.0
            own_goals = _number(row, "per90_own_goals", 0.0) * expected_minutes / 90.0
            xp_rare = (
                event_points("penalties_saved", pos, penalties_saved)
                + event_points("penalties_missed", pos, penalties_missed)
                + event_points("own_goals", pos, own_goals)
            )

            p_play = availability if average_minutes > 0 else 0.0
            xp_minutes = p_play * (1.0 + _probability_sixty_minutes(expected_minutes))
            xp_attack = event_points("goals", pos, expected_goals) + event_points("assists", pos, expected_assists)
            xp_total = xp_minutes + xp_attack + xp_clean_sheet + xp_conceded + xp_defcon + xp_saves + xp_cards + xp_rare

            eligible_bonus = expected_minutes >= 45.0
            xbps = (
                expected_minutes * 0.1
                + expected_goals * 24.0
                + expected_assists * 12.0
                + prob_clean_sheet * 12.0
                + prob_defcon * 6.0
                + expected_saves * 2.0
            )
            index = len(components)
            components.append({
                "player_id": int(row["player_id"]),
                "gameweek_id": gameweek_id,
                "fixture_id": fixture_id,
                "projected_points": float(xp_total),
                "projected_minutes": float(expected_minutes),
                "xbps": float(xbps),
            })
            if eligible_bonus and fixture_id is not None and fixture_id >= 0:
                bonus_groups[fixture_id].append(index)

        for indices in bonus_groups.values():
            logits = np.array([float(components[index]["xbps"]) for index in indices]) / 5.0
            logits -= logits.max()
            weights = np.exp(logits)
            probabilities = weights / weights.sum()
            for index, probability in zip(indices, probabilities, strict=True):
                components[index]["projected_points"] = float(
                    components[index]["projected_points"] + 3.0 * probability
                )

        output = []
        for component in components:
            prediction = {
                "player_id": component["player_id"],
                "gameweek_id": component["gameweek_id"],
                "projected_points": component["projected_points"],
                "projected_minutes": component["projected_minutes"],
            }
            if component["fixture_id"] is not None:
                prediction["fixture_id"] = component["fixture_id"]
            output.append(prediction)
        return pd.DataFrame(output)
