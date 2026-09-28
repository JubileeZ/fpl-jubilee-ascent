"""Lane s4: mass-preserving learned start probability, stacked with soft P(60) bonus eligibility (lane s code).

Participation stage: p_new = (1 - w) * p_champ + w * p_learn (ridge-logistic, lane b2r2) for players with p_learn.
Mass preservation (optional): within a group (club-fixture | target GW | club-fixture x position), p_new rescaled by
iterative proportional scaling (cap 0.99 per player, excess redistributed) so sum(p_new) == sum(p_champ) over the
same players. Learned model decides WHO starts; Champion decides HOW MUCH total start mass. Delta start mass moves
to/from p_dnp (blend_states). p_champ = Champion shrunk start probability (FaceValueChallengerModel._state_probabilities).
Bonus stage (elig60): bonus pool weighted by P(60+) = p_start * p_60_if_start + p_sub_in * p_60_if_sub_in.
All inputs via fit(history_df) / predict(features_df); per-predict state rebuilt each call.
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


def _weighted_plackett_luce(mass: np.ndarray) -> np.ndarray:
    """Expected 3/2/1 bonus under sequential draws proportional to ``mass`` (weighted softmax)."""
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


# ---- participation stage (from lane b2r2 via lane s) ----
_LAGS = 6
_MIN_TRAIN_GW = 4
_MIN_TARGET_GW = 5
_MIN_ROWS = 500
_HIST_COLUMNS = ("player_id", "fixture_id", "gameweek_id", "was_home", "opponent_club_id", "minutes", "starts")
_LAG_COLUMNS = tuple(f"s_lag{k}" for k in range(1, _LAGS + 1))
_COVARIATES = (*_LAG_COLUMNS, "min3", "starts6", "since_start", "pos_gk", "pos_def", "pos_mid", "club_frac")


def _panel(history_df: pd.DataFrame) -> pd.DataFrame:
    """Player-GW rows: started (any), minutes (sum), club (from fixture opposite side)."""
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
    """Covariates per panel row using only the player's earlier rows; n_prior = count of earlier rows."""
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


def learned_start_probabilities(history_df: pd.DataFrame, features_df: pd.DataFrame, lam: float) -> dict[int, float]:
    """player_id -> p_learn for the target GW; empty when gated off."""
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
    beta, mean, std = _fit_logistic(train[list(_COVARIATES)].to_numpy(float), train["started"].to_numpy(float), lam)
    pred = cov[cov["gameweek_id"].eq(target_gw) & cov["started"].isna() & cov["n_prior"].ge(1)]
    x = (pred[list(_COVARIATES)].to_numpy(float) - mean) / std
    p = 1.0 / (1.0 + np.exp(-np.clip(beta[0] + x @ beta[1:], -30, 30)))
    return {int(pid): float(v) for pid, v in zip(pred["player_id"], p)}


def blend_states(p_dnp: float, p_start: float, p_sub_in: float, p_learn: float, w: float) -> tuple[float, float, float]:
    new_start = (1.0 - w) * p_start + w * p_learn
    new_dnp = p_dnp - (new_start - p_start)
    new_sub = p_sub_in
    if new_dnp < 0:
        new_sub, new_dnp = max(0.0, p_sub_in + new_dnp), 0.0
    total = new_dnp + new_start + new_sub
    return new_dnp / total, new_start / total, new_sub / total


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


_GROUP_KEYS: dict[str, tuple[str, ...]] = {
    "club": ("club_id", "fixture_id"),
    "glob": ("gameweek_id",),
    "clubpos": ("club_id", "fixture_id", "position_id"),
}


def target_start_probabilities(
    features_df: pd.DataFrame, p_learn: dict[int, float], w: float, mass: str | None,
) -> dict[tuple[int, int], float]:
    """(player_id, fixture_id) -> blended (optionally mass-preserved) start probability for rows with p_learn."""
    if not p_learn or features_df.empty:
        return {}
    rows = features_df[features_df["player_id"].isin(p_learn) & pd.to_numeric(features_df["fixture_id"]).ge(0)]
    if rows.empty:
        return {}
    champ = np.array([FaceValueChallengerModel._state_probabilities(row)[1] for _, row in rows.iterrows()])
    frame = rows[["player_id", "fixture_id", "gameweek_id", "club_id", "position_id"]].copy()
    frame["p_champ"] = champ
    frame["p_new"] = (1.0 - w) * champ + w * frame["player_id"].map(p_learn).to_numpy(float)
    if mass is not None:
        for _, group in frame.groupby(list(_GROUP_KEYS[mass]), dropna=False):
            frame.loc[group.index, "p_new"] = preserve_mass(group["p_new"].to_numpy(), float(group["p_champ"].sum()))
    return {(int(pid), int(fid)): float(p) for pid, fid, p in zip(frame["player_id"], frame["fixture_id"], frame["p_new"])}


# ---- stacked model ----
class MassBase(MultiFeatureAssistChallengerModel):
    """Champion + optional soft P(60) bonus eligibility (elig60) + learned p_start (blend_w, mass group)."""

    variant: str = ""
    elig60: bool = False
    blend_w: float = 0.0
    ridge_lambda: float = 10.0
    mass: str | None = None

    def __init__(self) -> None:
        super().__init__()
        self._raw_history = pd.DataFrame()
        self._p_target: dict[tuple[int, int], float] = {}

    @property
    def name(self) -> str:
        return self.variant

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._raw_history = history_df

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        p_learn = learned_start_probabilities(self._raw_history, features_df, self.ridge_lambda) if self.blend_w > 0 else {}
        self._p_target = target_start_probabilities(features_df, p_learn, self.blend_w, self.mass)
        return super().predict(features_df, horizon)

    def _state_probabilities(self, row: pd.Series) -> tuple[float, float, float]:
        p_dnp, p_start, p_sub_in = FaceValueChallengerModel._state_probabilities(row)
        fixture = row.get("fixture_id")
        p_target = None if fixture is None or pd.isna(fixture) else self._p_target.get((int(row["player_id"]), int(fixture)))
        if p_target is None:
            return p_dnp, p_start, p_sub_in
        return blend_states(p_dnp, p_start, p_sub_in, p_target, 1.0)

    def _allocate_bonus(
        self,
        components: list[dict[str, object]],
        bonus_groups: defaultdict[int, list[int]],
    ) -> None:
        if not self.elig60:
            super()._allocate_bonus(components, bonus_groups)
            return
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


def _variant(name: str, **attrs: object) -> type[MassBase]:
    return type(name, (MassBase,), {"variant": name, **attrs})


PROTOTYPES: dict[str, type[MassBase]] = {
    "s4_e60_w100_mclub": _variant("s4_e60_w100_mclub", elig60=True, blend_w=1.0, mass="club"),
    "s4_e60_w100_mglob": _variant("s4_e60_w100_mglob", elig60=True, blend_w=1.0, mass="glob"),
    "s4_e60_w100_mclubpos": _variant("s4_e60_w100_mclubpos", elig60=True, blend_w=1.0, mass="clubpos"),
    "s4_w100_mclub": _variant("s4_w100_mclub", blend_w=1.0, mass="club"),
    "s4_e60_w75": _variant("s4_e60_w75", elig60=True, blend_w=0.75),
    "s4_e60_w75_mclub": _variant("s4_e60_w75_mclub", elig60=True, blend_w=0.75, mass="club"),
}

_ELIG = ("local.fixture_id", "local.p_start", "local.p_60_if_start", "local.p_sub_in", "local.p_60_if_sub_in",
         "local.xp_bonus", "local.projected_points", "local.xbps")
_LEARN = (
    *(f"history.{column}" for column in _HIST_COLUMNS),
    "features.player_id", "features.gameweek_id", "features.club_id", "features.position_id", "features.fixture_id",
    *(f"local.{key}" for key in (*_COVARIATES, "club", "started", "n_prior", "has_pos", "p_champ", "p_new")),
)
_ALL = tuple(dict.fromkeys((*_ELIG, *_LEARN)))
FEATURES: dict[str, tuple[str, ...]] = {name: _ALL for name in PROTOTYPES}
