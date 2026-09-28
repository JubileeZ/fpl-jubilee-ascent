"""Learned-start Model Candidate (explore-candidate dual-lane 2026-09-28; smoke variant ``s4_e60_w100_mglob``).

Subclass of ``multi_feature_assist_challenger`` with two changes (``docs/research/dual-lane-candidate-search``):

- Participation: ridge-logistic (lambda 10) start probability replaces Champion p_start for players with history.
  Covariates per player-GW from earlier rows only: started lags 1-6, minutes last 3 GWs / 90, starts in last 6,
  GWs since last start (cap 6), position dummies, share of club GWs started. Trained on current-season GW4+ rows
  (>= 500 rows); target GW < 5 -> Champion participation. Per GW, learned p_start rescaled (cap 0.99, excess
  redistributed) so its total equals Champion total over same players; delta start mass moves to/from p_dnp.
- Bonus: fixture bonus pool = weighted Plackett-Luce over softmax(xBPS / 6) x P(60+),
  P(60+) = p_start x p_60_if_start + p_sub_in x p_60_if_sub_in.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from models.face_value_challenger import FaceValueChallengerModel
from models.multi_feature_assist_challenger import MultiFeatureAssistChallengerModel

_BONUS_TEMPERATURE = 6.0
_MIN_WEIGHT = 1e-6
_CAP = 0.99
_RIDGE_LAMBDA = 10.0
_LAGS = 6
_MIN_TRAIN_GW = 4
_MIN_TARGET_GW = 5
_MIN_ROWS = 500
_HIST_COLUMNS = ("player_id", "fixture_id", "gameweek_id", "was_home", "opponent_club_id", "minutes", "starts")
_LAG_COLUMNS = tuple(f"s_lag{k}" for k in range(1, _LAGS + 1))
_COVARIATES = (*_LAG_COLUMNS, "min3", "starts6", "since_start", "pos_gk", "pos_def", "pos_mid", "club_frac")


def _weighted_plackett_luce(mass: np.ndarray) -> np.ndarray:
    """Expected 3/2/1 bonus under sequential draws proportional to ``mass``."""
    total = mass.sum()
    first = mass / total
    rest = total - mass
    p2 = np.divide(first[:, None] * mass[None, :], rest[:, None], out=np.zeros((len(mass), len(mass))),
                   where=rest[:, None] > 0)
    np.fill_diagonal(p2, 0.0)
    second = p2.sum(axis=0)
    remaining = total - mass[:, None] - mass[None, :]
    t = np.divide(p2, remaining, out=np.zeros_like(p2), where=remaining > 1e-15 * total)
    np.fill_diagonal(t, 0.0)
    third = mass * (t.sum() - t.sum(axis=1) - t.sum(axis=0))
    return 3.0 * first + 2.0 * second + third


def _panel(history_df: pd.DataFrame) -> pd.DataFrame:
    """Player-GW rows: started (any), minutes (sum), club (other side of fixture)."""
    hist = history_df[list(_HIST_COLUMNS)].copy()
    hist["was_home"] = hist["was_home"].astype(bool)
    sides = hist[["fixture_id", "was_home", "opponent_club_id"]].drop_duplicates(subset=["fixture_id", "was_home"])
    sides = sides.assign(was_home=~sides["was_home"]).rename(columns={"opponent_club_id": "club"})
    hist = hist.merge(sides, on=["fixture_id", "was_home"], how="left")
    hist["started"] = pd.to_numeric(hist["starts"], errors="coerce").fillna(0.0).ge(1).astype(float)
    hist["minutes"] = pd.to_numeric(hist["minutes"], errors="coerce").fillna(0.0)
    grouped = hist.sort_values("fixture_id").groupby(["player_id", "gameweek_id"], as_index=False)
    return grouped.agg(started=("started", "max"), minutes=("minutes", "sum"), club=("club", "first"))


def _covariates(panel: pd.DataFrame, positions: pd.Series) -> pd.DataFrame:
    """Covariates per panel row from the player's earlier rows; n_prior = count of earlier rows."""
    panel = panel.sort_values(["player_id", "gameweek_id"]).reset_index(drop=True)
    by_player = panel.groupby("player_id", sort=False)
    started, minutes = by_player["started"], by_player["minutes"]
    out = pd.DataFrame({"player_id": panel["player_id"], "gameweek_id": panel["gameweek_id"]})
    for k, column in enumerate(_LAG_COLUMNS, start=1):
        out[column] = started.shift(k).fillna(0.0).to_numpy()
    out["min3"] = sum(minutes.shift(k).fillna(0.0) for k in range(1, 4)).to_numpy() / 90.0
    out["starts6"] = out[list(_LAG_COLUMNS)].sum(axis=1)
    idx = by_player.cumcount().astype(float)
    last_start = idx.where(panel["started"].eq(1.0)).groupby(panel["player_id"]).transform(lambda s: s.ffill().shift(1))
    out["since_start"] = (idx - last_start).fillna(float(_LAGS)).clip(upper=float(_LAGS)).to_numpy()
    pos = panel["player_id"].map(positions)
    out["pos_gk"], out["pos_def"], out["pos_mid"] = (pos.eq(p).astype(float).to_numpy() for p in (1, 2, 3))
    out["n_prior"] = idx.to_numpy()
    started_filled = panel["started"].fillna(0.0)
    prior_starts = (started_filled.groupby(panel["player_id"]).cumsum() - started_filled).to_numpy()
    club_gws = panel[["club", "gameweek_id"]].dropna().drop_duplicates()
    club_sorted = {club: np.sort(g["gameweek_id"].to_numpy()) for club, g in club_gws.groupby("club")}
    n_club = np.array([
        np.searchsorted(club_sorted[c], gw) if c in club_sorted else 0.0
        for c, gw in zip(panel["club"], panel["gameweek_id"])], dtype=float)
    denom = np.where(n_club > 0, np.maximum(n_club, 1.0), np.maximum(idx.to_numpy(), 1.0))
    out["club_frac"] = np.clip(prior_starts / denom, 0.0, 1.0)
    out["started"] = panel["started"].to_numpy()
    out["has_pos"] = pos.notna().to_numpy()
    return out


def _fit_logistic(x: np.ndarray, y: np.ndarray, lam: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ridge logistic regression (Newton); intercept unpenalized; returns (beta, mean, std) for standardization."""
    mean, std = x.mean(axis=0), x.std(axis=0)
    std = np.where(std > 1e-9, std, 1.0)
    design = np.column_stack([np.ones(len(x)), (x - mean) / std])
    penalty = np.eye(design.shape[1]) * lam
    penalty[0, 0] = 0.0
    beta = np.zeros(design.shape[1])
    for _ in range(50):
        p = 1.0 / (1.0 + np.exp(-np.clip(design @ beta, -30, 30)))
        w = np.clip(p * (1.0 - p), 1e-9, None)
        step = np.linalg.solve(design.T @ (design * w[:, None]) + penalty, design.T @ (y - p) - penalty @ beta)
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    return beta, mean, std


def learned_start_probabilities(history_df: pd.DataFrame, features_df: pd.DataFrame) -> dict[int, float]:
    """player_id -> learned start probability for the target GW; empty when gated off."""
    if history_df.empty or features_df.empty or not set(_HIST_COLUMNS).issubset(history_df.columns):
        return {}
    target_gw = int(pd.to_numeric(features_df["gameweek_id"]).min())
    if target_gw < _MIN_TARGET_GW:
        return {}
    current = features_df[["player_id", "position_id", "club_id"]].drop_duplicates(subset=["player_id"])
    positions = current.set_index("player_id")["position_id"]
    panel = _panel(history_df)
    panel = panel[panel["gameweek_id"] < target_gw]
    seen = current[current["player_id"].isin(panel["player_id"])]
    future = pd.DataFrame({"player_id": seen["player_id"], "gameweek_id": target_gw, "started": np.nan,
                           "minutes": np.nan, "club": seen["club_id"]})
    cov = _covariates(pd.concat([panel, future], ignore_index=True), positions)
    train = cov[cov["started"].notna() & cov["gameweek_id"].ge(_MIN_TRAIN_GW) & cov["n_prior"].ge(1) & cov["has_pos"]]
    if len(train) < _MIN_ROWS:
        return {}
    beta, mean, std = _fit_logistic(train[list(_COVARIATES)].to_numpy(float), train["started"].to_numpy(float),
                                    _RIDGE_LAMBDA)
    pred = cov[cov["gameweek_id"].eq(target_gw) & cov["started"].isna() & cov["n_prior"].ge(1)]
    x = (pred[list(_COVARIATES)].to_numpy(float) - mean) / std
    p = 1.0 / (1.0 + np.exp(-np.clip(beta[0] + x @ beta[1:], -30, 30)))
    return {int(pid): float(v) for pid, v in zip(pred["player_id"], p)}


def preserve_mass(p_new: np.ndarray, target: float, cap: float = _CAP) -> np.ndarray:
    """Iterative proportional scaling: sum(out) == target (if feasible), out <= cap, excess redistributed."""
    out = p_new.astype(float).copy()
    capped = np.zeros(len(out), dtype=bool)
    for _ in range(len(out) + 1):
        free_mass = out[~capped].sum()
        remaining = target - cap * capped.sum()
        if remaining <= 0:
            out[~capped] = 0.0
            break
        if free_mass <= 0:
            break
        out[~capped] *= remaining / free_mass
        over = ~capped & (out > cap)
        if not over.any():
            break
        capped |= over
        out[capped] = cap
    return out


def target_start_probabilities(features_df: pd.DataFrame, p_learn: dict[int, float]) -> dict[tuple[int, int], float]:
    """(player_id, fixture_id) -> learned start probability, rescaled per GW to Champion start mass."""
    if not p_learn or features_df.empty:
        return {}
    rows = features_df[features_df["player_id"].isin(p_learn) & pd.to_numeric(features_df["fixture_id"]).ge(0)]
    if rows.empty:
        return {}
    frame = rows[["player_id", "fixture_id", "gameweek_id"]].copy()
    frame["p_champ"] = [FaceValueChallengerModel._state_probabilities(row)[1] for _, row in rows.iterrows()]
    frame["p_new"] = frame["player_id"].map(p_learn).to_numpy(float)
    for _, group in frame.groupby("gameweek_id", dropna=False):
        frame.loc[group.index, "p_new"] = preserve_mass(group["p_new"].to_numpy(), float(group["p_champ"].sum()))
    return {(int(pid), int(fid)): float(p) for pid, fid, p in zip(frame["player_id"], frame["fixture_id"], frame["p_new"])}


def blend_states(p_dnp: float, p_start: float, p_sub_in: float, p_target: float) -> tuple[float, float, float]:
    """Replace p_start with ``p_target``; delta moves to/from p_dnp (then p_sub_in if p_dnp exhausted)."""
    new_dnp = p_dnp - (p_target - p_start)
    new_sub = p_sub_in
    if new_dnp < 0:
        new_sub, new_dnp = max(0.0, p_sub_in + new_dnp), 0.0
    total = new_dnp + p_target + new_sub
    return new_dnp / total, p_target / total, new_sub / total


class LearnedStartChallengerModel(MultiFeatureAssistChallengerModel):
    """Multi-feature assist Champion + mass-preserving learned p_start + P(60)-weighted bonus pool."""

    def __init__(self) -> None:
        super().__init__()
        self._raw_history = pd.DataFrame()
        self._p_target: dict[tuple[int, int], float] = {}

    @property
    def name(self) -> str:
        return "learned_start_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._raw_history = history_df

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._p_target = target_start_probabilities(features_df, learned_start_probabilities(self._raw_history, features_df))
        return super().predict(features_df, horizon)

    def _state_probabilities(self, row: pd.Series) -> tuple[float, float, float]:
        p_dnp, p_start, p_sub_in = FaceValueChallengerModel._state_probabilities(row)
        fixture = row.get("fixture_id")
        p_target = None if fixture is None or pd.isna(fixture) else self._p_target.get((int(row["player_id"]), int(fixture)))
        return (p_dnp, p_start, p_sub_in) if p_target is None else blend_states(p_dnp, p_start, p_sub_in, p_target)

    def _allocate_bonus(self, components: list[dict[str, object]], bonus_groups: defaultdict[int, list[int]]) -> None:
        groups: defaultdict[int, list[tuple[int, float]]] = defaultdict(list)
        for index, component in enumerate(components):
            fixture_id = component["fixture_id"]
            if fixture_id is None or fixture_id < 0:
                continue
            weight = (
                float(component.get("p_start", 0.0)) * float(component.get("p_60_if_start", 0.0))
                + float(component.get("p_sub_in", 0.0)) * float(component.get("p_60_if_sub_in", 0.0))
            )
            if weight > _MIN_WEIGHT:
                groups[fixture_id].append((index, weight))
        for members in groups.values():
            indices = [index for index, _ in members]
            logits = np.array([float(components[index]["xbps"]) for index in indices]) / _BONUS_TEMPERATURE
            mass = np.exp(logits - logits.max()) * np.array([weight for _, weight in members])
            for index, bonus in zip(indices, _weighted_plackett_luce(mass), strict=True):
                components[index]["xp_bonus"] = float(bonus)
                components[index]["projected_points"] = float(components[index]["projected_points"]) + float(bonus)
