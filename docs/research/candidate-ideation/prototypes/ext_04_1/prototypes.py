"""EXT-04_1: downweight attacking xG evidence from fixtures with red-card dismissals."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from models.base import resolve_asof_target_gw
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_APPEARANCE_KEY = ["player_id", "fixture_id"]
_FIXTURE_FIELDS = ["player_id", "fixture_id", "gameweek_id", "opponent_club_id"]
_HISTORY_COLUMNS = [*_FIXTURE_FIELDS, "minutes", "red_cards", "expected_goals"]
_MID_FWD_POSITIONS = frozenset({3, 4})
_DECAY = 0.95
_PSEUDO_MINUTES = 360.0


def _prepare_dismissal_history(history_df: pd.DataFrame) -> pd.DataFrame:
    """Verify two-sided fixtures and compute fixture-level red-card flag before filtering."""
    cols = [
        "player_id",
        "fixture_id",
        "gameweek_id",
        "club_id",
        "minutes",
        "expected_goals",
        "red_cards",
    ]
    if history_df.empty or not set(_HISTORY_COLUMNS).issubset(history_df.columns):
        return pd.DataFrame(columns=cols)

    history = history_df[_HISTORY_COLUMNS].apply(pd.to_numeric, errors="coerce")
    history = history.replace([np.inf, -np.inf], np.nan)
    valid_keys = history[_FIXTURE_FIELDS].fillna(0).gt(0).all(axis=1)
    history = history.loc[valid_keys].drop_duplicates().reset_index(drop=True)
    if history.empty:
        return pd.DataFrame(columns=cols)

    appearances = history.groupby(_APPEARANCE_KEY)["opponent_club_id"]
    conflicting_sides = appearances.transform("nunique").gt(1)
    conflicting_fixtures = history.loc[conflicting_sides, "fixture_id"]

    dedup = history.loc[~history["fixture_id"].isin(conflicting_fixtures)].drop_duplicates(
        subset=_APPEARANCE_KEY, keep=False
    )
    if dedup.empty:
        return pd.DataFrame(columns=cols)

    fixtures = dedup.groupby("fixture_id")
    sides = fixtures["opponent_club_id"]
    valid_rc = dedup["red_cards"].notna() & dedup["red_cards"].ge(0)
    complete = (
        sides.transform("nunique").eq(2)
        & fixtures["gameweek_id"].transform("nunique").eq(1)
        & valid_rc.groupby(dedup["fixture_id"]).transform("all")
    )
    dedup = dedup.loc[complete].copy()
    if dedup.empty:
        return pd.DataFrame(columns=cols)

    sides = dedup.groupby("fixture_id")["opponent_club_id"]
    lower_club = sides.transform("min")
    own_club = sides.transform("max").where(
        dedup["opponent_club_id"].eq(lower_club), lower_club
    )
    fixture_red = (
        dedup.groupby("fixture_id")["red_cards"].transform("sum").gt(0).astype(float)
    )
    prepared = dedup.assign(club_id=own_club, red_cards=fixture_red)
    valid_obs = (
        prepared["minutes"].notna()
        & prepared["minutes"].gt(0)
        & prepared["expected_goals"].notna()
        & prepared["expected_goals"].ge(0)
    )
    return prepared.loc[valid_obs, cols].reset_index(drop=True)


class DismissalFixtureXgReliabilityModel(DefXgShrinkChallengerModel):
    """Downweight historical xG from red-card fixtures inside event rate projection."""

    variant_name: str = "ext_04_1_a050"
    a: float = 0.50

    def __init__(self) -> None:
        super().__init__()
        self._dismissal_hist: pd.DataFrame = pd.DataFrame()
        self._xg_delta: dict[tuple[int, int], float] = {}

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._dismissal_hist = _prepare_dismissal_history(history_df)

    def _compute_xg_deltas(self, features_df: pd.DataFrame) -> dict[tuple[int, int], float]:
        if (
            features_df.empty
            or self._dismissal_hist.empty
            or not {"player_id", "club_id", "position_id"}.issubset(features_df.columns)
        ):
            return {}

        target_gw = resolve_asof_target_gw(features_df, self._raw_history)
        prior = self._dismissal_hist.loc[
            self._dismissal_hist["gameweek_id"].lt(target_gw)
        ]
        if prior.empty:
            return {}

        meta = features_df[["player_id", "club_id", "position_id"]].copy()
        for col in ("player_id", "club_id", "position_id"):
            meta[col] = pd.to_numeric(meta[col], errors="coerce")
        meta = meta.dropna(subset=["player_id", "club_id", "position_id"])
        meta = meta.loc[meta["position_id"].isin(_MID_FWD_POSITIONS)].drop_duplicates(
            subset=["player_id", "club_id"]
        )
        if meta.empty:
            return {}

        eligible_pairs = {
            (int(pid), int(cid))
            for pid, cid in zip(meta["player_id"], meta["club_id"], strict=True)
        }
        prior_keys = list(
            zip(
                prior["player_id"].astype(int),
                prior["club_id"].astype(int),
                strict=True,
            )
        )
        mask = [key in eligible_pairs for key in prior_keys]
        scoped = prior.loc[mask].copy()
        if scoped.empty:
            return {}

        scoped["player_id"] = scoped["player_id"].astype(int)
        scoped["club_id"] = scoped["club_id"].astype(int)
        latest_gw = scoped.groupby(["player_id", "club_id"])["gameweek_id"].transform(
            "max"
        )
        weights = (_DECAY ** (latest_gw - scoped["gameweek_id"])).to_numpy(dtype=float)
        dismissal = scoped["red_cards"].to_numpy(dtype=float)
        rel_weights = weights * (1.0 - self.a * dismissal)
        mins = scoped["minutes"].to_numpy(dtype=float)
        xg = scoped["expected_goals"].to_numpy(dtype=float)

        grouped = (
            pd.DataFrame(
                {
                    "w_m": weights * mins,
                    "w_xg": weights * xg,
                    "v_m": rel_weights * mins,
                    "v_xg": rel_weights * xg,
                    "m_plain": np.where(dismissal == 0.0, mins, 0.0),
                    "m_red": np.where(dismissal == 1.0, mins, 0.0),
                }
            )
            .groupby([scoped["player_id"].to_numpy(), scoped["club_id"].to_numpy()])
            .sum()
        )

        deltas: dict[tuple[int, int], float] = {}
        for rec in grouped.itertuples():
            pid, cid = rec.Index
            m_plain = float(rec.m_plain)
            m_red = float(rec.m_red)
            w_m = float(rec.w_m)
            if m_plain <= 0.0 or m_red <= 0.0 or w_m <= 0.0:
                continue
            b_rate = 90.0 * float(rec.w_xg) / w_m
            v_m = float(rec.v_m)
            denom = _PSEUDO_MINUTES + v_m
            if denom <= 0.0:
                continue
            d = 90.0 * (float(rec.v_xg) - b_rate * v_m / 90.0) / denom
            if math.isfinite(d) and d != 0.0:
                deltas[(int(pid), int(cid))] = d
        return deltas

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._xg_delta = self._compute_xg_deltas(features_df)
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
        if position in ("M", "F") and self._xg_delta:
            raw_pid = row.get("player_id")
            raw_cid = row.get("club_id")
            raw_xg = row.get("per90_xg")
            if (
                raw_pid is not None
                and raw_cid is not None
                and raw_xg is not None
                and not (pd.isna(raw_pid) or pd.isna(raw_cid) or pd.isna(raw_xg))
            ):
                xg_val = float(raw_xg)
                if math.isfinite(xg_val) and xg_val > 0.0:
                    delta = self._xg_delta.get((int(raw_pid), int(raw_cid)), 0.0)
                    if math.isfinite(delta) and delta != 0.0:
                        adjusted_xg = max(0.0, xg_val + delta)
                        row_copy = row.copy()
                        row_copy["per90_xg"] = adjusted_xg
                        if adjusted_xg == 0.0:
                            raw_threat = row_copy.get("per90_threat")
                            threat_val = (
                                0.0
                                if raw_threat is None or pd.isna(raw_threat)
                                else float(raw_threat)
                            )
                            if not math.isfinite(threat_val) or threat_val <= 0.0:
                                row_copy["per90_goals"] = 0.0
                        return super()._project_event_components(
                            row_copy,
                            position,
                            expected_minutes,
                            clean_sheet_minutes=clean_sheet_minutes,
                            p_sixty_mins=p_sixty_mins,
                        )
        return super()._project_event_components(
            row,
            position,
            expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes,
            p_sixty_mins=p_sixty_mins,
        )


_GRID = (("ext_04_1_a050", 0.50), ("ext_04_1_a080", 0.80))
PROTOTYPES = {
    name: type(
        name,
        (DismissalFixtureXgReliabilityModel,),
        {"variant_name": name, "a": a},
    )
    for name, a in _GRID
}
_MANIFEST = (
    "features.player_id",
    "features.club_id",
    "features.position_id",
    "features.per90_xg",
    "features.per90_threat",
    "features.per90_goals",
    "history.player_id",
    "history.fixture_id",
    "history.gameweek_id",
    "history.opponent_club_id",
    "history.minutes",
    "history.red_cards",
    "history.expected_goals",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
COMPONENTS = {name: "xp_goals" for name in PROTOTYPES}
