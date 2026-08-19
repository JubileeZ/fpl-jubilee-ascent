"""Calibrated event-component projection model (Event-Level Empirical Bayes).

The model predicts event quantities/probabilities and reconstructs points through
the scoring matrix. ``fit`` is optional and must receive only pre-cutoff history.
"""

import math
from collections import defaultdict

import numpy as np
import pandas as pd

from models.base import BaseModel, cap_projected_minutes, iter_feature_rows
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


def _negbin_pmf(k: int, lmbda: float, r: float = 3.0) -> float:
    """Return P(X = k) for X ~ NegativeBinomial(mean=lmbda, dispersion=r)."""
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    p = r / (r + lmbda)
    coeff = 1.0
    for j in range(k):
        coeff *= (j + r) / (j + 1)
    return coeff * (p**r) * ((1.0 - p)**k)


def _negbin_cdf_complement(threshold: int, lmbda: float, r: float = 7.5) -> float:
    """Return P(X >= threshold) for X ~ NegativeBinomial(mean=lmbda, dispersion=r)."""
    if lmbda <= 0:
        return 0.0
    cdf = sum(_negbin_pmf(k, lmbda, r) for k in range(threshold))
    return min(max(1.0 - cdf, 0.0), 1.0)


def _expected_negbin_conceded_penalty(lmbda: float, r: float = 3.0) -> float:
    """Return expected goals conceded penalty points E[floor(X / 2)] under NB(lmbda, r)."""
    if lmbda <= 0:
        return 0.0
    max_k = max(30, int(math.ceil(lmbda + 10.0 * math.sqrt(lmbda + 1.0))))
    return sum(math.floor(k / 2) * _negbin_pmf(k, lmbda, r) for k in range(max_k + 1))


def _expected_poisson_floor(lmbda: float, divisor: int) -> float:
    """Return E[floor(X / divisor)] for a Poisson random variable."""
    if lmbda <= 0:
        return 0.0
    max_k = max(40, int(math.ceil(lmbda + 12.0 * math.sqrt(lmbda + 1.0))))
    return sum(math.floor(k / divisor) * _poisson_pmf(k, lmbda) for k in range(max_k + 1))


def _fit_metric_weights(
    history_df: pd.DataFrame,
    target_column: str,
    metric_column: str,
    secondary_column: str,
    defaults: np.ndarray,
) -> tuple[np.ndarray, dict[int, float]]:
    required = {target_column, metric_column, secondary_column, "minutes"}
    if not required.issubset(history_df.columns):
        return defaults.copy(), {}

    minutes = pd.to_numeric(history_df["minutes"], errors="coerce")
    target = pd.to_numeric(history_df[target_column], errors="coerce")
    metric = pd.to_numeric(history_df[metric_column], errors="coerce")
    secondary = pd.to_numeric(history_df[secondary_column], errors="coerce")

    valid = minutes > 0
    if not valid.any():
        return defaults.copy(), {}

    df = pd.DataFrame({
        "minutes": minutes[valid],
        "target": target[valid],
        "metric": metric[valid],
        "secondary": secondary[valid],
    }).dropna()
    if "player_id" in history_df.columns:
        df["player_id"] = history_df.loc[df.index, "player_id"]

    if len(df) < 20:
        return defaults.copy(), {}

    rate_target = df["target"] / df["minutes"] * 90.0
    rate_metric = df["metric"] / df["minutes"] * 90.0
    rate_sec = df["secondary"] / df["minutes"] * 0.9
    weights = np.sqrt(df["minutes"].to_numpy())

    X = np.column_stack([rate_metric, rate_sec])
    y = rate_target.to_numpy()

    XtW = X.T * weights
    XtWX = XtW @ X
    lam = 20.0
    A = XtWX + lam * np.eye(2)
    b = XtW @ y + lam * defaults
    try:
        fitted = np.linalg.solve(A, b)
        fitted = np.maximum(fitted, 0.0)
    except np.linalg.LinAlgError:
        fitted = defaults.copy()

    player_offsets: dict[int, float] = {}
    if "player_id" in df.columns:
        pred_rates = X @ fitted
        df["residual"] = rate_target - pred_rates
        for pid, grp in df.groupby("player_id"):
            n = len(grp)
            mean_res = float(grp["residual"].mean())
            shrunk = (n / (n + 15.0)) * mean_res
            player_offsets[int(pid)] = shrunk

    return fitted.astype(float), player_offsets


class MetricsComponentHybridModel(BaseModel):
    def __init__(self) -> None:
        self.goal_weights = _DEFAULT_GOAL_WEIGHTS.copy()
        self.assist_weights = _DEFAULT_ASSIST_WEIGHTS.copy()
        self.goal_offsets: dict[int, float] = {}
        self.assist_offsets: dict[int, float] = {}

    @property
    def name(self) -> str:
        return "metrics_component_hybrid"

    def fit(self, history_df: pd.DataFrame) -> None:
        """Calibrate attack mappings using history strictly before prediction."""
        self.goal_weights, self.goal_offsets = _fit_metric_weights(
            history_df,
            "goals_scored",
            "expected_goals",
            "threat",
            _DEFAULT_GOAL_WEIGHTS,
        )
        self.assist_weights, self.assist_offsets = _fit_metric_weights(
            history_df,
            "assists",
            "expected_assists",
            "creativity",
            _DEFAULT_ASSIST_WEIGHTS,
        )

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float,
    ) -> dict[str, float]:
        """Project non-minute events conditional on a participation state."""
        pid = int(row["player_id"])
        diff = _number(row, "difficulty", 3.0)
        fdr_attack = max(0.2, (6.0 - diff) / 3.0)
        fdr_defence = max(0.2, diff / 3.0)
        attack_input = _optional_number(row, "attack_multiplier")
        defence_input = _optional_number(row, "defence_multiplier")
        attack_multiplier = fdr_attack if attack_input is None else attack_input
        defence_multiplier = fdr_defence if defence_input is None else defence_input

        xg_per90 = _number(row, "per90_xg", 0.0)
        threat_per90 = _number(row, "per90_threat", 0.0)
        raw_goals_per90 = _number(row, "per90_goals", 0.0)
        if xg_per90 > 0 or threat_per90 > 0:
            expected_goals_per90 = (
                self.goal_weights[0] * xg_per90
                + self.goal_weights[1] * threat_per90 / 100.0
                + self.goal_offsets.get(pid, 0.0)
            )
        else:
            expected_goals_per90 = raw_goals_per90 + self.goal_offsets.get(pid, 0.0)
        expected_goals = max(0.0, expected_goals_per90) * expected_minutes / 90.0 * attack_multiplier

        xa_per90 = _number(row, "per90_xa", 0.0)
        creativity_per90 = _number(row, "per90_creativity", 0.0)
        raw_assists_per90 = _number(row, "per90_assists", 0.0)
        if xa_per90 > 0 or creativity_per90 > 0:
            expected_assists_per90 = (
                self.assist_weights[0] * xa_per90
                + self.assist_weights[1] * creativity_per90 / 100.0
                + self.assist_offsets.get(pid, 0.0)
            )
        else:
            expected_assists_per90 = raw_assists_per90 + self.assist_offsets.get(pid, 0.0)
        expected_assists = max(0.0, expected_assists_per90) * expected_minutes / 90.0 * attack_multiplier

        gc_per90 = _number(row, "per90_goals_conceded", 1.2)
        lmbda_team_90 = max(0.05, gc_per90 * defence_multiplier)
        lmbda_player = lmbda_team_90 * expected_minutes / 90.0
        p_sixty_mins = min(max(p_sixty_mins, 0.0), 1.0)
        lmbda_pitch = lmbda_team_90 * max(clean_sheet_minutes, 0.0) / 90.0
        prob_clean_sheet_on_pitch = math.exp(-lmbda_pitch)
        prob_clean_sheet = prob_clean_sheet_on_pitch * p_sixty_mins

        defcon_per90 = _number(row, "per90_defensive_contribution", 0.0)
        lmbda_defcon = max(0.0, defcon_per90 * expected_minutes / 90.0 * defence_multiplier)
        defcon_threshold = 10 if position == "D" else 12
        defcon_r = 8.5 if position == "D" else 7.0
        prob_defcon = (
            _negbin_cdf_complement(defcon_threshold, lmbda_defcon, r=defcon_r)
            if position != "GK"
            else 0.0
        )

        saves_per90 = _number(row, "per90_saves", 0.0)
        expected_saves = (
            saves_per90 * expected_minutes / 90.0 * defence_multiplier if position == "GK" else 0.0
        )
        yellow_cards = _number(row, "per90_yellow_cards", 0.0) * expected_minutes / 90.0
        red_cards = _number(row, "per90_red_cards", 0.0) * expected_minutes / 90.0
        penalties_saved = _number(row, "per90_penalties_saved", 0.0) * expected_minutes / 90.0
        penalties_missed = _number(row, "per90_penalties_missed", 0.0) * expected_minutes / 90.0
        own_goals = _number(row, "per90_own_goals", 0.0) * expected_minutes / 90.0

        components = {
            "xp_goals": event_points("goals", position, expected_goals),
            "xp_assists": event_points("assists", position, expected_assists),
            "xp_clean_sheet": prob_clean_sheet * _CLEAN_SHEET_POINTS[position],
            "xp_conceded": (
                -_expected_negbin_conceded_penalty(lmbda_player, r=3.0)
                if position in ("GK", "D")
                else 0.0
            ),
            "xp_defcon": event_points("defensive_contributions", position, prob_defcon),
            "xp_saves": _expected_poisson_floor(expected_saves, 3),
            "xp_yellow_cards": event_points("yellow_cards", position, yellow_cards),
            "xp_red_cards": event_points("red_cards", position, red_cards),
            "xp_penalties_saved": event_points("penalties_saved", position, penalties_saved),
            "xp_penalties_missed": event_points("penalties_missed", position, penalties_missed),
            "xp_own_goals": event_points("own_goals", position, own_goals),
            "xp_bonus": 0.0,
            "xbps": (
                expected_minutes * 0.1
                + expected_goals * 24.0
                + expected_assists * 12.0
                + prob_clean_sheet * 12.0
                + prob_defcon * 6.0
                + expected_saves * 2.0
            ),
        }
        components["projected_points"] = sum(
            value
            for key, value in components.items()
            if key.startswith("xp_") and key != "xp_bonus"
        )
        components["eligible_bonus"] = float(expected_minutes >= 45.0)
        return components

    @staticmethod
    def _allocate_bonus(
        components: list[dict[str, object]],
        bonus_groups: defaultdict[int, list[int]],
    ) -> None:
        """Allocate expected +3/+2/+1 bonus points within each fixture."""
        for indices in bonus_groups.values():
            xbps_values = np.array([float(components[index]["xbps"]) for index in indices])
            logits = xbps_values / 6.0
            logits -= logits.max()
            exp_logits = np.exp(logits)
            first = exp_logits / exp_logits.sum()
            second = np.zeros(len(indices))
            third = np.zeros(len(indices))

            for i in range(len(indices)):
                remaining = np.ones(len(indices), dtype=bool)
                remaining[i] = False
                if not remaining.any():
                    continue
                second_probs = exp_logits[remaining] / exp_logits[remaining].sum()
                remaining_indices = np.flatnonzero(remaining)
                for second_index, player_index in enumerate(remaining_indices):
                    second[player_index] += first[i] * second_probs[second_index]
                    remaining_after_second = remaining.copy()
                    remaining_after_second[player_index] = False
                    if not remaining_after_second.any():
                        continue
                    third_probs = exp_logits[remaining_after_second] / exp_logits[remaining_after_second].sum()
                    third[remaining_after_second] += (
                        first[i] * second_probs[second_index] * third_probs
                    )

            expected_bonus = 3.0 * first + 2.0 * second + third
            for index, bonus in zip(indices, expected_bonus, strict=True):
                components[index]["xp_bonus"] = float(bonus)
                components[index]["projected_points"] = (
                    float(components[index]["projected_points"]) + float(bonus)
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
            pid = int(row["player_id"])
            n_starts = _number(row, "n_starts_historical", 0.0)
            w_ind = n_starts / (n_starts + 4.0)
            exp_mins_start = min(90.0, w_ind * average_minutes + (1.0 - w_ind) * 78.0)
            app_prob = min(1.0, max(0.0, _number(row, "appearance_probability", 1.0)))
            p_start = min(availability, average_minutes / 78.0) if average_minutes > 0 else 0.0
            p_sub = max(0.0, min(availability - p_start, app_prob))
            exp_mins_sub = 18.0
            raw_expected_mins = p_start * exp_mins_start + p_sub * exp_mins_sub
            expected_minutes = cap_projected_minutes(row, raw_expected_mins)
            position = _POS_CODE.get(int(_number(row, "position_id", 3.0)), "M")
            p_sixty_mins = p_start * min(1.0, max(0.0, (exp_mins_start - 45.0) / 30.0))
            event_components = self._project_event_components(
                row,
                position,
                expected_minutes,
                clean_sheet_minutes=exp_mins_start,
                p_sixty_mins=p_sixty_mins,
            )
            xp_minutes = (p_start + p_sub) + p_sixty_mins
            index = len(components)
            components.append({
                "player_id": pid,
                "gameweek_id": gameweek_id,
                "fixture_id": fixture_id,
                "projected_minutes": expected_minutes,
                "xbps": event_components["xbps"],
                "xp_minutes": xp_minutes,
                **event_components,
                "projected_points": xp_minutes + event_components["projected_points"],
            })
            if event_components["eligible_bonus"] and fixture_id is not None and fixture_id >= 0:
                bonus_groups[fixture_id].append(index)

        self._allocate_bonus(components, bonus_groups)
        output = []
        component_columns = (
            "xp_minutes",
            "xp_goals",
            "xp_assists",
            "xp_clean_sheet",
            "xp_conceded",
            "xp_defcon",
            "xp_saves",
            "xp_yellow_cards",
            "xp_red_cards",
            "xp_penalties_saved",
            "xp_penalties_missed",
            "xp_own_goals",
            "xp_bonus",
        )
        for component in components:
            prediction = {
                "player_id": component["player_id"],
                "gameweek_id": component["gameweek_id"],
                "projected_points": component["projected_points"],
                "projected_minutes": component["projected_minutes"],
                **{
                    column: component.get(column, 0.0)
                    for column in component_columns
                },
            }
            if component["fixture_id"] is not None:
                prediction["fixture_id"] = component["fixture_id"]
            output.append(prediction)
        return pd.DataFrame(output)
