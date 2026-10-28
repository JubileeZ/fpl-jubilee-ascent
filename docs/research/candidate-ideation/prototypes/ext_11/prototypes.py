from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from backtesting.walkforward import LEDGER_COMPONENTS
from features.contracts import assert_projection_contract
from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.learned_start_challenger import LearnedStartChallengerModel
from models.ml_panel_features import positional_price_tier_prior
from models.scoring_matrix import event_points


class RoleFixture:
    def __init__(self, opponent: int, offsets: np.ndarray, marks: np.ndarray) -> None:
        self.opponent = opponent
        self.offsets = offsets
        self.marks = marks


def profiles_before(
    history: pd.DataFrame, positions: pd.Series, cutoff: int,
) -> dict[int, tuple[int, float]]:
    required = {"player_id", "gameweek_id", "minutes", "expected_goals", "expected_assists", "price"}
    if history.empty or not required.issubset(history.columns):
        return {}
    prior = history[history["gameweek_id"] < cutoff].copy()
    if prior.empty:
        return {}
    result: dict[int, tuple[int, float]] = {}
    for player_id, rows in prior.groupby("player_id", sort=False):
        position = positions.get(player_id)
        if pd.isna(position) or int(position) not in (3, 4):
            continue
        prices = rows.sort_values(["gameweek_id", "fixture_id"])["price"].dropna()
        if prices.empty or not np.isfinite(float(prices.iloc[0])):
            continue
        played = rows[rows["minutes"] > 0]
        if played.empty:
            continue
        weights = 0.95 ** (cutoff - 1 - played["gameweek_id"].to_numpy(dtype=float))
        exposure = float(np.sum(weights * played["minutes"].to_numpy(dtype=float) / 90.0))
        goals = float(np.sum(weights * played["expected_goals"].to_numpy(dtype=float)))
        assists = float(np.sum(weights * played["expected_assists"].to_numpy(dtype=float)))
        if not np.isfinite([exposure, goals, assists]).all() or min(goals, assists) < 0:
            continue
        price = float(prices.iloc[0])
        mu_g = positional_price_tier_prior(int(position), price, metric="xg90")
        mu_a = positional_price_tier_prior(int(position), price, metric="xa90")
        rate_g = (12.0 * mu_g + goals) / (12.0 + exposure)
        rate_a = (12.0 * mu_a + assists) / (12.0 + exposure)
        if rate_g <= 0 or rate_g + rate_a <= 0:
            continue
        role = 2 if int(position) == 4 else (0 if rate_g / (rate_g + rate_a) >= 0.5 else 1)
        result[int(player_id)] = role, rate_g
    return result


def observed_clubs(history: pd.DataFrame) -> dict[tuple[int, bool], int]:
    required = {"fixture_id", "was_home", "opponent_club_id"}
    if history.empty or not required.issubset(history.columns):
        return {}
    result: dict[tuple[int, bool], int] = {}
    for fixture_id, rows in history.groupby("fixture_id", sort=False):
        sides = rows[["was_home", "opponent_club_id"]].dropna().drop_duplicates()
        if len(sides) != 2 or sides["was_home"].nunique() != 2 or sides["opponent_club_id"].nunique() != 2:
            continue
        mapping = {bool(row["was_home"]): int(row["opponent_club_id"]) for _, row in sides.iterrows()}
        if min(mapping.values()) < 1:
            continue
        result[int(fixture_id), True] = mapping[False]
        result[int(fixture_id), False] = mapping[True]
    return result


def training_fixtures(history: pd.DataFrame, positions: pd.Series, cutoff: int) -> list[RoleFixture]:
    required = {"player_id", "fixture_id", "gameweek_id", "was_home", "opponent_club_id",
                "minutes", "expected_goals", "expected_assists", "price"}
    if history.empty or not required.issubset(history.columns):
        return []
    prior = history[history["gameweek_id"] < cutoff].drop_duplicates(["player_id", "fixture_id"]).copy()
    clubs = observed_clubs(prior)
    fixtures: list[RoleFixture] = []
    for gw, gw_rows in prior.groupby("gameweek_id", sort=True):
        contexts = profiles_before(prior, positions, int(gw))
        by_side: dict[tuple[int, int, int], tuple[np.ndarray, np.ndarray]] = {}
        for _, row in gw_rows.iterrows():
            fixture_id = int(row["fixture_id"])
            side = bool(row["was_home"])
            club = clubs.get((fixture_id, side))
            profile = contexts.get(int(row["player_id"]))
            if club is None or profile is None:
                continue
            role, rate_g = profile
            minutes, xg = float(row["minutes"]), float(row["expected_goals"])
            if not np.isfinite([minutes, xg]).all() or minutes <= 0 or xg < 0:
                continue
            key = fixture_id, club, int(row["opponent_club_id"])
            offsets, marks = by_side.setdefault(key, (np.zeros(3), np.zeros(3)))
            offsets[role] += minutes / 90.0 * rate_g
            marks[role] += xg
        for (_, _, opponent), (offsets, marks) in by_side.items():
            if float(offsets.sum()) > 0 and float(marks.sum()) > 0:
                fixtures.append(RoleFixture(opponent, offsets, marks))
    return fixtures


def fit_contrasts(fixtures: list[RoleFixture], ridge: float) -> dict[int, np.ndarray]:
    if not fixtures:
        return {}
    exposure = np.sum([fixture.offsets for fixture in fixtures], axis=0)
    if float(exposure.sum()) <= 0:
        return {}
    pi = exposure / exposure.sum()
    _, _, right = np.linalg.svd(pi.reshape(1, 3), full_matrices=True)
    basis = right[1:].T
    grouped: defaultdict[int, list[RoleFixture]] = defaultdict(list)
    for fixture in fixtures:
        grouped[fixture.opponent].append(fixture)
    result: dict[int, np.ndarray] = {}
    for opponent, observations in grouped.items():
        beta = np.zeros(2)
        for _ in range(30):
            theta = basis @ beta
            gradient = -ridge * beta
            hessian = ridge * np.eye(2)
            for observation in observations:
                mass = observation.offsets * np.exp(np.clip(theta, -20.0, 20.0))
                probs = mass / mass.sum()
                total = float(observation.marks.sum())
                gradient += basis.T @ (observation.marks - total * probs)
                covariance = np.diag(probs) - np.outer(probs, probs)
                hessian += total * basis.T @ covariance @ basis
            step = np.linalg.solve(hessian, gradient)
            beta += step
            if float(np.max(np.abs(step))) < 1e-10:
                break
        theta = basis @ beta
        if np.isfinite(theta).all():
            result[opponent] = theta
    return result


def normalized_counts(counts: np.ndarray, contrasts: np.ndarray, alpha: float) -> np.ndarray:
    if len(counts) == 0 or float(counts.sum()) <= 0 or alpha <= 0:
        return counts.copy()
    bound = np.log(1.10)
    logits = alpha * np.clip(contrasts, -bound, bound)
    if np.all(logits == logits[0]):
        return counts.copy()
    weighted = counts * np.exp(logits)
    if not np.isfinite(weighted).all() or float(weighted.sum()) <= 0:
        return counts.copy()
    result = weighted * float(counts.sum()) / float(weighted.sum())
    if not np.isclose(float(result.sum()), float(counts.sum()), atol=1e-12, rtol=1e-12):
        raise ValueError("Final attacker count conservation violated")
    return result


class OpponentRoleAllocation(DefXgShrinkChallengerModel):
    ridge: float = 50.0

    def __init__(self) -> None:
        super().__init__()
        self._anchor_components: list[dict[str, object]] = []
        self._history_df = pd.DataFrame()

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._history_df = history_df

    @property
    def name(self) -> str:
        return f"ext_11_role_l{int(self.ridge)}"

    def _allocate_bonus(self, components: list[dict[str, object]], bonus_groups: defaultdict[int, list[int]]) -> None:
        self._anchor_components = [component.copy() for component in components]
        super()._allocate_bonus(components, bonus_groups)

    def _apply_role_counts(
        self, features: pd.DataFrame, final: pd.DataFrame,
        profiles: dict[int, tuple[int, float]], contrasts: dict[int, np.ndarray], alpha: float,
    ) -> pd.DataFrame:
        if alpha <= 0 or not profiles or not contrasts:
            return final
        result = final.copy().reset_index(drop=True)
        current = features.reset_index(drop=True)
        anchor = [component.copy() for component in self._anchor_components]
        anchor_index = {(int(c["player_id"]), int(c["gameweek_id"]), int(c["fixture_id"])): j
                        for j, c in enumerate(anchor)}
        changed = False
        for fixture_id, rows in current.groupby("fixture_id", sort=False):
            if int(fixture_id) < 0:
                continue
            sides = rows[["club_id", "opponent_id"]].dropna().drop_duplicates()
            if len(sides) != 2:
                continue
            first, second = sides.iloc[0], sides.iloc[1]
            if (int(first["club_id"]) != int(second["opponent_id"])
                    or int(second["club_id"]) != int(first["opponent_id"])
                    or int(first["club_id"]) == int(first["opponent_id"])):
                continue
            for _, club_rows in rows.groupby("club_id", sort=False):
                attackers = club_rows[club_rows["position_id"].isin([3, 4])]
                if attackers.empty:
                    continue
                idx = attackers.index.to_numpy()
                counts = np.array([float(result.loc[k, "xp_goals"])
                                   / event_points("goals", _position(int(current.loc[k, "position_id"])), 1.0)
                                   for k in idx])
                role_contrasts = np.zeros(len(idx))
                known = np.zeros(len(idx), dtype=bool)
                for j, k in enumerate(idx):
                    player = int(current.loc[k, "player_id"])
                    opponent = int(current.loc[k, "opponent_id"])
                    profile = profiles.get(player)
                    theta = contrasts.get(opponent)
                    if profile is not None and theta is not None:
                        role_contrasts[j] = float(theta[profile[0]])
                        known[j] = True
                active_mask = known & (counts > 0)
                if int(np.sum(active_mask)) < 2:
                    continue
                new_counts = counts.copy()
                new_counts[active_mask] = normalized_counts(
                    counts[active_mask], role_contrasts[active_mask], alpha
                )
                for j, k in enumerate(idx):
                    delta = float(new_counts[j] - counts[j])
                    if delta == 0.0:
                        continue
                    changed = True
                    position = _position(int(current.loc[k, "position_id"]))
                    result.loc[k, "xp_goals"] = event_points("goals", position, float(new_counts[j]))
                    key = (int(current.loc[k, "player_id"]), int(current.loc[k, "gameweek_id"]), int(fixture_id))
                    item = anchor[anchor_index[key]]
                    item["xbps"] = float(item["xbps"]) + 24.0 * delta
        if not changed:
            return final
        for item in anchor:
            item["xp_bonus"] = 0.0
            item["projected_points"] = 0.0
        LearnedStartChallengerModel._allocate_bonus(self, anchor, defaultdict(list))
        bonus = {(int(c["player_id"]), int(c["gameweek_id"]), int(c["fixture_id"])): float(c["xp_bonus"])
                 for c in anchor}
        result["xp_bonus"] = [bonus[int(row["player_id"]), int(row["gameweek_id"]), int(row["fixture_id"])]
                              for _, row in result.iterrows()]
        result["projected_points"] = result[list(LEDGER_COMPONENTS)].sum(axis=1)
        result.index = final.index
        assert_projection_contract(result)
        return result

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._anchor_components = []
        final = super().predict(features_df, horizon)
        if features_df.empty:
            return final
        cutoff = resolve_asof_target_gw(features_df, self._history_df)
        if cutoff < 4 or self._history_df.empty:
            return final
        history = self._history_df[self._history_df["gameweek_id"] < cutoff].drop_duplicates(["player_id", "fixture_id"])
        alpha = float(np.clip((len(history) - 3500.0) / 4000.0, 0.0, 1.0))
        if alpha <= 0:
            return final
        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        profiles = profiles_before(history, positions, cutoff)
        observations = training_fixtures(history, positions, cutoff)
        contrasts = fit_contrasts(observations, self.ridge)
        return self._apply_role_counts(features_df, final, profiles, contrasts, alpha)


def _position(position_id: int) -> str:
    return "M" if position_id == 3 else "F"


class Role25(OpponentRoleAllocation):
    ridge = 25.0


class Role50(OpponentRoleAllocation):
    ridge = 50.0


class Role100(OpponentRoleAllocation):
    ridge = 100.0


PROTOTYPES = {"ext_11_role_l25": Role25, "ext_11_role_l50": Role50, "ext_11_role_l100": Role100}
COMPONENTS = {name: "xp_goals" for name in PROTOTYPES}
FEATURES = {name: (
    "features.player_id", "features.fixture_id", "features.gameweek_id", "features.position_id",
    "features.club_id", "features.opponent_id", "history.player_id", "history.fixture_id", "history.gameweek_id",
    "history.was_home", "history.opponent_club_id", "history.minutes", "history.expected_goals",
    "history.expected_assists", "history.price", "local.xbps",
) for name in PROTOTYPES}
