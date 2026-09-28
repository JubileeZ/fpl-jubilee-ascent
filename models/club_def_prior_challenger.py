"""Club x DEF xG prior Model Candidate (explore-candidate Queue mode 2026-09-29; smoke variant ``atk_05_def_k5``).

Subclass of ``learned_start_challenger`` (``docs/research/component-model-ideas`` idea ATK-05): DEF xG/90 keeps the
Champion shrink strength (360 pseudo-minutes, recency decay 0.95) but shrinks toward the as-of club x DEF pooled xG/90
(set-piece structure proxy) instead of the DEF mean. Club prior itself shrinks toward the DEF mean with 5 90-minute
matches. Club of a history row = other side of its fixture; player's club = ``features.club_id``. Applied as ratio
new/old on ``features.per90_xg`` so builder prior, matchup addon and penalty isolation survive. Other positions and
assists unchanged.
"""

from __future__ import annotations

import pandas as pd

from models.learned_start_challenger import LearnedStartChallengerModel

_SHRINK = 360.0
_DECAY = 0.95
_CLUB_PSEUDO_MINUTES = 5.0 * 90.0
_RATIO_CLIP = (0.1, 10.0)
_DEFENDER = 2
_MIDFIELDER = 3
_HIST_COLUMNS = ("player_id", "gameweek_id", "minutes", "expected_goals", "fixture_id", "was_home", "opponent_club_id")


def attach_club(history: pd.DataFrame) -> pd.DataFrame:
    """History rows with ``club`` = other side of the fixture."""
    hist = history.copy()
    hist["was_home"] = hist["was_home"].astype(bool)
    sides = hist[["fixture_id", "was_home", "opponent_club_id"]].drop_duplicates(subset=["fixture_id", "was_home"])
    sides = sides.assign(was_home=~sides["was_home"]).rename(columns={"opponent_club_id": "club"})
    return hist.merge(sides, on=["fixture_id", "was_home"], how="left")


def shrunk_xg_rates(hist: pd.DataFrame, prior: pd.Series) -> pd.Series:
    """player_id -> decayed xG/90 shrunk toward ``prior`` (player_id -> xG/90) with 360 pseudo-minutes."""
    last = hist.groupby("player_id")["gameweek_id"].transform("max")
    weight = _DECAY ** (last - hist["gameweek_id"])
    sums = pd.DataFrame({"events": hist["expected_goals"] * weight, "mins": hist["minutes"] * weight,
                         "player_id": hist["player_id"]}).groupby("player_id").sum()
    p = prior.reindex(sums.index).fillna(0.0)
    return (sums["events"] + _SHRINK * p / 90.0) / (sums["mins"] + _SHRINK) * 90.0


def club_def_ratio(hist: pd.DataFrame, current: pd.DataFrame) -> pd.Series:
    """player_id -> xG rate ratio (club x DEF prior vs DEF-mean prior); 1.0 for non-DEF."""
    positions = current.set_index("player_id")["position_id"]
    clubs = current.set_index("player_id")["club_id"]
    pos = hist["player_id"].map(positions).fillna(_MIDFIELDER)
    by_pos = hist.groupby(pos)[["expected_goals", "minutes"]].sum()
    pos_rate = by_pos["expected_goals"] / by_pos["minutes"].clip(lower=1.0) * 90.0
    by_cp = hist.assign(pos=pos.to_numpy()).groupby(["club", "pos"])[["expected_goals", "minutes"]].sum()
    base = by_cp.index.get_level_values(1).map(pos_rate.to_dict()).to_numpy(dtype=float)
    club_rate = (by_cp["expected_goals"] + _CLUB_PSEUDO_MINUTES * base / 90.0) / (by_cp["minutes"] + _CLUB_PSEUDO_MINUTES) * 90.0
    player_pos = positions.fillna(_MIDFIELDER)
    old_prior = player_pos.map(pos_rate.to_dict()).fillna(0.0)
    cp = pd.Series([club_rate.get((c, p), float("nan")) for c, p in zip(clubs.reindex(player_pos.index), player_pos)],
                   index=player_pos.index)
    new_prior = cp.where(player_pos.eq(_DEFENDER) & cp.notna(), old_prior)
    new, old = shrunk_xg_rates(hist, new_prior), shrunk_xg_rates(hist, old_prior)
    return (new / old.where(old > 1e-9)).fillna(1.0).clip(*_RATIO_CLIP)


class ClubDefPriorChallengerModel(LearnedStartChallengerModel):
    """Learned-start Champion plus DEF xG/90 shrunk toward as-of club x DEF prior."""

    def __init__(self) -> None:
        super().__init__()
        self._xg_hist = pd.DataFrame()

    @property
    def name(self) -> str:
        return "club_def_prior_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        if history_df.empty or not set(_HIST_COLUMNS).issubset(history_df.columns):
            self._xg_hist = pd.DataFrame()
            return
        hist = history_df[list(_HIST_COLUMNS)].copy()
        for column in ("player_id", "gameweek_id", "minutes", "expected_goals"):
            hist[column] = pd.to_numeric(hist[column], errors="coerce").fillna(0.0)
        hist = attach_club(hist)
        self._xg_hist = hist[(hist["minutes"] > 0) & hist["club"].notna()]

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if self._xg_hist.empty:
            return super().predict(features_df, horizon)
        current = features_df[["player_id", "position_id", "club_id"]].drop_duplicates(subset=["player_id"])
        ratio = club_def_ratio(self._xg_hist, current)
        features = features_df.copy()
        features["per90_xg"] = features["per90_xg"] * features["player_id"].map(ratio).fillna(1.0).to_numpy()
        return super().predict(features, horizon)
