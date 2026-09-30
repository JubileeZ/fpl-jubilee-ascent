"""Multi-feature assist-rate Model Candidate (explore-candidate 2026-09-28).

Subclass of ``face_value_challenger``. Replaces the single-signal assist rate (per-90 xA x attack_multiplier)
with a ridge Poisson GLM over several as-of signals (``docs/research/multi-feature-event-rate``):

- assists per 90 = player as-of xA/90 x exp(b0 + b . z), z standardized:
  log xA/90, log(creativity/90 + 1), log opponent xG conceded per match, log own-team xG per match
  (both / league mean), home.
- Target = Official xA per appearance (log link, offset log(minutes/90 x xA/90)); ridge lambda 10, intercept free.
- Trained on current-season history each ``predict`` (needs Feature Contract positions). Covariates for a GW-g
  training row use only rows before GW g. Fewer than 3 history GWs -> Champion assists. GKs keep Champion assists.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.face_value_challenger import FaceValueChallengerModel
from models.scoring_matrix import event_points

_DECAY = 0.95
_PSEUDO_MINUTES = 360.0
_CLUB_PSEUDO_MATCHES = 4.0
_LEAGUE_XG_DEFAULT = 1.35
_MIN_TRAIN_GWS = 3
_MIN_TRAIN_ROWS = 200
_RIDGE_LAMBDA = 10.0
_MULT_CLIP = (0.25, 4.0)
_RATE_FLOOR = 0.01
_MIDFIELDER = 3
_GOALKEEPER = 1
_HISTORY_COLUMNS = (
    "player_id", "fixture_id", "gameweek_id", "opponent_club_id", "was_home", "minutes",
    "expected_goals", "expected_assists", "creativity",
)
_PLAYER_SUMS = ("expected_assists", "creativity")


def _poisson_ridge(z: np.ndarray, y: np.ndarray, offset: np.ndarray, lam: float, iters: int = 30) -> np.ndarray:
    """Ridge Poisson GLM (log link, offset) via IRLS; intercept unpenalized; ``z`` pre-standardized."""
    design = np.column_stack([np.ones(len(y)), z])
    penalty = lam * np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    beta = np.zeros(design.shape[1])
    beta[0] = np.log(max(y.sum(), 1e-6) / max(np.exp(offset).sum(), 1e-6))
    for _ in range(iters):
        eta = np.clip(design @ beta + offset, -20, 5)
        mu = np.exp(eta)
        work = eta - offset + (y - mu) / mu
        new = np.linalg.solve(design.T @ (design * mu[:, None]) + penalty, design.T @ (mu * work))
        if np.max(np.abs(new - beta)) < 1e-7:
            return new
        beta = new
    return beta


def _club_fixture_table(hist: pd.DataFrame) -> pd.DataFrame:
    """One row per (fixture, club): gameweek, xg_for, xg_against, opponent. Club = other side of opponent."""
    sides = hist.groupby("fixture_id")["opponent_club_id"].agg(["min", "max"])
    frame = hist.join(sides, on="fixture_id")
    frame = frame[frame["min"] != frame["max"]]
    frame = frame.assign(club=frame["min"] + frame["max"] - frame["opponent_club_id"])
    club = frame.groupby(["fixture_id", "club"], as_index=False).agg(
        gameweek_id=("gameweek_id", "first"), xg_for=("expected_goals", "sum"))
    other = club[["fixture_id", "club", "xg_for"]].rename(columns={"club": "opp", "xg_for": "xg_against"})
    club = club.merge(other, on="fixture_id")
    return club[club["club"] != club["opp"]].reset_index(drop=True)


def _club_asof(club_fx: pd.DataFrame, gw: int) -> tuple[pd.DataFrame, float]:
    """Shrunk per-match club xG for (att) and against (def) from fixtures before ``gw``; league mean xG."""
    prior = club_fx[club_fx["gameweek_id"] < gw]
    league = float(prior["xg_for"].mean()) if len(prior) else _LEAGUE_XG_DEFAULT
    league = league if np.isfinite(league) and league > 0 else _LEAGUE_XG_DEFAULT
    grouped = prior.groupby("club").agg(n=("xg_for", "size"), xg_for=("xg_for", "sum"), xg_against=("xg_against", "sum"))
    pseudo = _CLUB_PSEUDO_MATCHES * league
    rates = pd.DataFrame({
        "att": (grouped["xg_for"] + pseudo) / (grouped["n"] + _CLUB_PSEUDO_MATCHES),
        "def": (grouped["xg_against"] + pseudo) / (grouped["n"] + _CLUB_PSEUDO_MATCHES),
    })
    return rates, league


def _player_asof(prior: pd.DataFrame, positions: pd.Series, players: np.ndarray) -> pd.DataFrame:
    """Recency-weighted per-90 xA / creativity shrunk to position mean (builder-style), indexed by player."""
    played = prior[prior["minutes"] > 0]
    played = played.assign(pos=played["player_id"].map(positions).fillna(_MIDFIELDER))
    by_pos = played.groupby("pos")[[*_PLAYER_SUMS, "minutes"]].sum()
    last = played.groupby("player_id")["gameweek_id"].transform("max")
    weight = _DECAY ** (last - played["gameweek_id"])
    sums = played[list(_PLAYER_SUMS)].mul(weight, axis=0).assign(
        minutes=played["minutes"] * weight, player_id=played["player_id"]).groupby("player_id").sum()
    player_pos = positions.reindex(players).fillna(_MIDFIELDER)
    out = pd.DataFrame({"position": player_pos}, index=player_pos.index)
    denom = sums["minutes"].reindex(out.index).fillna(0.0) + _PSEUDO_MINUTES
    for column in _PLAYER_SUMS:
        pos_rate = player_pos.map((by_pos[column] / by_pos["minutes"].clip(lower=1.0) * 90.0).to_dict()).fillna(0.0)
        out[column] = (sums[column].reindex(out.index).fillna(0.0) + pos_rate / 90.0 * _PSEUDO_MINUTES) / denom * 90.0
    return out


def _attach_club(frame: pd.DataFrame, own: np.ndarray, opp: np.ndarray, clubs: pd.DataFrame, league: float) -> pd.DataFrame:
    return frame.assign(
        team_att=pd.Series(own).map(clubs["att"]).fillna(league).to_numpy() / league,
        opp_def=pd.Series(opp).map(clubs["def"]).fillna(league).to_numpy() / league,
    )


def _design(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return (log base xA/90, covariates) for rows carrying as-of player + club columns."""
    log_base = np.log(frame["expected_assists"].clip(lower=_RATE_FLOOR).to_numpy())
    z = np.column_stack([
        log_base,
        np.log(frame["creativity"].to_numpy() + 1.0),
        np.log(frame["opp_def"].to_numpy()),
        np.log(frame["team_att"].to_numpy()),
        frame["home"].to_numpy(dtype=float),
    ])
    return log_base, z


class MultiFeatureAssistChallengerModel(FaceValueChallengerModel):
    """Face-value Champion with multi-feature GLM assist rate."""

    def __init__(self) -> None:
        super().__init__()
        self._history = pd.DataFrame()
        self._assist_rates: dict[tuple[int, int], float] = {}

    @property
    def name(self) -> str:
        return "multi_feature_assist_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if not set(_HISTORY_COLUMNS).issubset(history_df.columns):
            self._history = pd.DataFrame()
            return
        hist = history_df[list(_HISTORY_COLUMNS)].copy()
        numeric = [column for column in _HISTORY_COLUMNS if column != "was_home"]
        hist[numeric] = hist[numeric].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        self._history = hist

    def _training_rows(self, positions: pd.Series, club_fx: pd.DataFrame) -> pd.DataFrame:
        hist = self._history
        club_of = club_fx.set_index(["fixture_id", "opp"])["club"]
        rows: list[pd.DataFrame] = []
        for gw in sorted(hist["gameweek_id"].unique()):
            prior = hist[hist["gameweek_id"] < gw]
            if gw < 2 or prior.empty:
                continue
            target = hist[(hist["gameweek_id"] == gw) & (hist["minutes"] > 0)]
            clubs, league = _club_asof(club_fx, gw)
            own = club_of.reindex(pd.MultiIndex.from_arrays([target["fixture_id"], target["opponent_club_id"]])).to_numpy()
            frame = pd.concat([
                pd.DataFrame({"minutes": target["minutes"].to_numpy(), "y": target["expected_assists"].to_numpy(),
                              "home": target["was_home"].astype(bool).to_numpy()}),
                _player_asof(prior, positions, target["player_id"].unique())
                .reindex(target["player_id"].to_numpy()).reset_index(drop=True),
            ], axis=1)
            rows.append(_attach_club(frame, own, target["opponent_club_id"].to_numpy(), clubs, league))
        return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

    def _fit_assist_rates(self, features_df: pd.DataFrame) -> dict[tuple[int, int], float]:
        hist = self._history
        if features_df.empty or hist.empty or hist["gameweek_id"].nunique() < _MIN_TRAIN_GWS:
            return {}
        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]
        club_fx = _club_fixture_table(hist)
        train = self._training_rows(positions, club_fx)
        train = train[train["position"] != _GOALKEEPER] if not train.empty else train
        if len(train) < _MIN_TRAIN_ROWS:
            return {}
        log_base, z = _design(train)
        mu, sd = z.mean(axis=0), z.std(axis=0) + 1e-9
        offset = np.log(train["minutes"].to_numpy() / 90.0) + log_base
        beta = _poisson_ridge((z - mu) / sd, train["y"].to_numpy(dtype=float), offset, _RIDGE_LAMBDA)

        target_gw = resolve_asof_target_gw(features_df, hist)
        fx = features_df[features_df["fixture_id"] >= 0].drop_duplicates(["player_id", "fixture_id"])
        clubs, league = _club_asof(club_fx, target_gw)
        frame = pd.concat([
            pd.DataFrame({"player_id": fx["player_id"].to_numpy(), "fixture_id": fx["fixture_id"].to_numpy(),
                          "home": fx["is_home"].astype(bool).to_numpy()}),
            _player_asof(hist, positions, fx["player_id"].unique()).reindex(fx["player_id"].to_numpy()).reset_index(drop=True),
        ], axis=1)
        frame = _attach_club(frame, fx["club_id"].to_numpy(), fx["opponent_id"].to_numpy(), clubs, league)
        log_base, z = _design(frame)
        rates = np.exp(log_base) * np.clip(np.exp(beta[0] + ((z - mu) / sd) @ beta[1:]), *_MULT_CLIP)
        keep = frame["position"].to_numpy() != _GOALKEEPER
        return {
            (int(pid), int(fid)): float(rate)
            for pid, fid, rate, ok in zip(frame["player_id"], frame["fixture_id"], rates, keep, strict=True)
            if ok
        }

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._assist_rates = self._fit_assist_rates(features_df)
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
        components = super()._project_event_components(
            row, position, expected_minutes, clean_sheet_minutes=clean_sheet_minutes, p_sixty_mins=p_sixty_mins
        )
        fixture = row.get("fixture_id")
        rate = None if fixture is None or pd.isna(fixture) else self._assist_rates.get((int(row["player_id"]), int(fixture)))
        if rate is None:
            return components
        old_assists = components["xp_assists"] / 3.0
        new_assists = rate * expected_minutes / 90.0
        new_points = event_points("assists", position, new_assists)
        components["projected_points"] += new_points - components["xp_assists"]
        components["xbps"] += 12.0 * (new_assists - old_assists)
        components["xp_assists"] = new_points
        return components
