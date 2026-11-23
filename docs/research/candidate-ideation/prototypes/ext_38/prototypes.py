"""EXT-38 fixed variants for two-part outfield fixture xG."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import NamedTuple

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.optimize import brentq

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_KEYS = ("player_id", "gameweek_id", "fixture_id")
_HISTORY_COLUMNS = (*_KEYS, "minutes", "expected_goals")
_OUTFIELD = (2, 3, 4)
_BANDS = (0, 1, 2)
_DECAY = 0.95
_LOWER_HAZARD = 1e-6
_UPPER_HAZARD = 20.0
FloatArray = NDArray[np.float64]


class _XgEstimate(NamedTuple):
    hazard: float
    positive_amounts: tuple[float, ...]
    single_mean_xg_per90: float

    def fixture_xg(self, minutes: float) -> tuple[float, float]:
        exposure = min(minutes, 90.0) / 90.0
        band = sum(minutes > edge for edge in (30.0, 60.0))
        return (
            -math.expm1(-self.hazard * exposure) * self.positive_amounts[band],
            self.single_mean_xg_per90 * exposure,
        )


def _fit_hazard(
    positive_exposure: FloatArray,
    positive_weight: FloatArray,
    negative_exposure: float,
    prior_positive: float = 0.0,
    prior_negative: float = 0.0,
) -> float:
    """Solve the bounded weighted Bernoulli likelihood through its score."""

    def derivative(hazard: float) -> float:
        positive_term = np.dot(
            positive_weight, positive_exposure / np.expm1(hazard * positive_exposure)
        )
        return float(
            positive_term
            + prior_positive / math.expm1(hazard)
            - negative_exposure
            - prior_negative
        )

    if derivative(_LOWER_HAZARD) <= 0.0:
        return _LOWER_HAZARD
    if derivative(_UPPER_HAZARD) >= 0.0:
        return _UPPER_HAZARD
    return float(brentq(derivative, _LOWER_HAZARD, _UPPER_HAZARD))


def _prepare_history(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame(columns=list(_HISTORY_COLUMNS))
    prepared = history.loc[:, list(_HISTORY_COLUMNS)].apply(
        pd.to_numeric, errors="coerce"
    )
    identities = prepared.loc[:, list(_KEYS)].to_numpy(dtype=float)
    if not (
        np.isfinite(identities).all()
        and (identities > 0.0).all()
        and (identities == np.floor(identities)).all()
    ):
        raise ValueError("EXT-38 requires positive integer player-fixture history keys")
    if prepared.duplicated(list(_KEYS)).any():
        raise ValueError("EXT-38 requires unique player-fixture history keys")
    minutes = prepared["minutes"]
    xg = prepared["expected_goals"]
    valid = np.isfinite(minutes) & minutes.gt(0.0) & np.isfinite(xg) & xg.ge(0.0)
    return prepared.loc[valid].copy()


def _fit_position(pool: pd.DataFrame, k: float) -> dict[int, _XgEstimate]:
    positives = pool[pool["expected_goals"].gt(0.0)]
    if positives.empty:
        return {}

    hazard = _fit_hazard(
        positives["exposure"].to_numpy(dtype=np.float64),
        positives["weight"].to_numpy(dtype=np.float64),
        float(pool.loc[pool["expected_goals"].eq(0.0), "weighted_exposure"].sum()),
    )
    prior_positive = k * -math.expm1(-hazard)
    prior_negative = k - prior_positive
    prior_rate = float(pool["weighted_xg"].sum() / pool["weighted_exposure"].sum())
    pooled_mean = float(positives["weighted_xg"].sum() / positives["weight"].sum())
    by_band = positives.groupby("duration_band")[["weighted_xg", "weight"]].sum()
    prior_amount = (
        (by_band["weighted_xg"] / by_band["weight"]).reindex(_BANDS).fillna(pooled_mean)
    )

    estimates: dict[int, _XgEstimate] = {}
    for player_id, rows in pool.groupby("player_id"):
        player_positive = rows[rows["expected_goals"].gt(0.0)]
        fitted_hazard = _fit_hazard(
            player_positive["exposure"].to_numpy(dtype=np.float64),
            player_positive["weight"].to_numpy(dtype=np.float64),
            float(rows.loc[rows["expected_goals"].eq(0.0), "weighted_exposure"].sum()),
            prior_positive,
            prior_negative,
        )
        player_bands = (
            player_positive.groupby("duration_band")[["weighted_xg", "weight"]]
            .sum()
            .reindex(_BANDS, fill_value=0.0)
        )
        amounts = (player_bands["weighted_xg"] + k * prior_amount) / (
            player_bands["weight"] + k
        )
        single_mean = (rows["weighted_xg"].sum() + k * prior_rate) / (
            rows["weighted_exposure"].sum() + k
        )
        estimates[int(player_id)] = _XgEstimate(
            fitted_hazard, tuple(map(float, amounts)), float(single_mean)
        )
    return estimates


class TwoPartFixtureXgChallengerModel(DefXgShrinkChallengerModel):
    """Apply a fitted state-level xG correction inside the inherited scorer."""

    variant_name: str = "ext_38_k08_d16"
    k: float = 8.0
    k_def: float = 16.0
    # Research controls leave the production scoring path as issued.
    correction_scale: float = 1.0
    correct_defenders: bool = True
    capture_xg: bool = False

    def __init__(self) -> None:
        super().__init__()
        self._two_part_history = pd.DataFrame()
        self._estimates: dict[int, _XgEstimate] = {}
        self._state_xg: defaultdict[
            tuple[int, int, int], list[tuple[float, float, float]]
        ] = defaultdict(list)

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._two_part_history = _prepare_history(history_df)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        issue = resolve_asof_target_gw(features_df, self._raw_history)
        self._state_xg.clear()
        self._estimates = {}
        roster = features_df[["player_id", "position_id"]].drop_duplicates()
        if roster["player_id"].duplicated().any():
            raise ValueError("EXT-38 requires one issue-time position per player")
        if not self._two_part_history.empty:
            prior = self._two_part_history.loc[
                self._two_part_history["gameweek_id"].lt(issue)
            ].copy()
            prior["position_id"] = prior["player_id"].map(
                roster.set_index("player_id")["position_id"]
            )
            prior = prior[prior["position_id"].isin(_OUTFIELD)].copy()
            duration = prior["minutes"].clip(upper=90.0)
            prior["exposure"] = duration / 90.0
            prior["weight"] = _DECAY ** (issue - 1 - prior["gameweek_id"])
            prior["duration_band"] = duration.gt(30.0).astype(int) + duration.gt(60.0)
            prior["weighted_exposure"] = prior["weight"] * prior["exposure"]
            prior["weighted_xg"] = prior["weight"] * prior["expected_goals"]
            for position, group in prior.groupby("position_id"):
                self._estimates.update(
                    _fit_position(group, self.k_def if position == 2 else self.k)
                )

        return super().predict(features_df, horizon)

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float,
    ) -> dict[str, float]:
        player_id = int(row["player_id"])
        xg_per90 = row.get("per90_xg", 0.0)
        base_rate = float(xg_per90) if pd.notna(xg_per90) else 0.0
        exposure = expected_minutes / 90.0
        adjusted_rate = base_rate
        matched_xg = max(0.0, base_rate * exposure)
        estimate = self._estimates.get(player_id)
        if estimate is not None and exposure > 0.0:
            two_part, matched_xg = estimate.fixture_xg(expected_minutes)
            if (
                base_rate > 0.0
                and self.correction_scale
                and (self.correct_defenders or position != "D")
            ):
                adjusted_rate = max(
                    0.0,
                    base_rate
                    + self.correction_scale * (two_part - matched_xg) / exposure,
                )
        if self.capture_xg:
            key = (player_id, int(row["gameweek_id"]), int(row["fixture_id"]))
            self._state_xg[key].append(
                (
                    max(0.0, base_rate * exposure),
                    matched_xg,
                    max(0.0, adjusted_rate * exposure),
                )
            )
        if adjusted_rate != base_rate:
            row = row.copy()
            row["per90_xg"] = adjusted_rate
        return super()._project_event_components(
            row,
            position,
            expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes,
            p_sixty_mins=p_sixty_mins,
        )

    def xg_diagnostics(self, projections: pd.DataFrame) -> pd.DataFrame:
        """Return issued xG inputs weighted by the Champion's state probabilities."""
        data: list[tuple[int, int, int, float, float, float]] = []
        for row in projections.itertuples(index=False):
            key = (int(row.player_id), int(row.gameweek_id), int(row.fixture_id))
            if key[2] < 0:
                continue
            start, sub = self._state_xg[key]
            expected = tuple(
                row.p_start * started + row.p_sub_in * substituted
                for started, substituted in zip(start, sub, strict=True)
            )
            data.append((*key, *expected))
        return pd.DataFrame(
            data, columns=[*_KEYS, "champion_xg", "single_mean_xg", "candidate_xg"]
        )


_GRID = (("ext_38_k08_d16", 8.0, 16.0), ("ext_38_k16_d32", 16.0, 32.0))
PROTOTYPES = {
    name: type(
        name,
        (TwoPartFixtureXgChallengerModel,),
        {"variant_name": name, "k": k, "k_def": k_def},
    )
    for name, k, k_def in _GRID
}
_MANIFEST = (
    "features.player_id",
    "features.position_id",
    "features.gameweek_id",
    "features.fixture_id",
    "features.per90_xg",
    "history.player_id",
    "history.gameweek_id",
    "history.fixture_id",
    "history.minutes",
    "history.expected_goals",
    "local.exposure",
    "local.weight",
    "local.duration_band",
    "local.weighted_exposure",
    "local.weighted_xg",
    "local.champion_xg",
    "local.single_mean_xg",
    "local.candidate_xg",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
COMPONENTS = {name: "xp_goals" for name in PROTOTYPES}
