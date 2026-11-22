"""EXT-02_1: player exposure handover between assist GLM and stock face-value rate."""

from __future__ import annotations

import math

import pandas as pd

from models.base import resolve_asof_target_gw
from models.calibrated_matchup_hybrid import CalibratedMatchupHybridModel
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.scoring_matrix import Position

_OUTFIELD_POSITIONS: dict[int, Position] = {2: "D", 3: "M", 4: "F"}
_APPEARANCE_KEYS = ["player_id", "fixture_id"]


class PlayerExposureAssistHandoverModel(DefXgShrinkChallengerModel):
    """Blend fitted GLM assist rate toward stock face-value rate by prior minutes."""

    variant_name: str = "ext_02_1_k180"
    k: float = 180.0

    @property
    def name(self) -> str:
        return self.variant_name

    def _prior_minutes_by_player(self, target_gw: int) -> dict[int, float]:
        hist = self._history
        if hist.empty:
            return {}
        valid = (
            hist["gameweek_id"].ge(1)
            & hist["gameweek_id"].lt(target_gw)
            & hist["player_id"].gt(0)
            & hist["fixture_id"].ge(0)
        )
        prior = hist.loc[valid].drop_duplicates(subset=_APPEARANCE_KEYS)
        prior = prior.loc[prior["minutes"].gt(0) & prior["minutes"].lt(math.inf)]
        if prior.empty:
            return {}
        grouped = prior.groupby(prior["player_id"].astype(int))["minutes"].sum()
        return {
            int(pid): float(mins)
            for pid, mins in grouped.items()
            if math.isfinite(float(mins))
        }

    def _fit_assist_rates(
        self, features_df: pd.DataFrame
    ) -> dict[tuple[int, int], float]:
        rates = super()._fit_assist_rates(features_df)
        if not rates or features_df.empty:
            return {}

        target_gw = resolve_asof_target_gw(features_df, self._history)
        minutes_by_player = self._prior_minutes_by_player(target_gw)
        fixture_ids = pd.to_numeric(features_df["fixture_id"], errors="coerce")
        fx = features_df.loc[fixture_ids.ge(0)].drop_duplicates(
            subset=_APPEARANCE_KEYS
        )

        blended: dict[tuple[int, int], float] = {
            key: float(val) for key, val in rates.items() if math.isfinite(float(val))
        }
        for _, row in fx.iterrows():
            key = (int(row["player_id"]), int(row["fixture_id"]))
            g_rate = blended.get(key)
            if g_rate is None:
                continue
            raw_pos = row.get("position_id")
            if raw_pos is None or pd.isna(raw_pos):
                continue
            position = _OUTFIELD_POSITIONS.get(int(raw_pos))
            if position is None:
                continue
            stock = CalibratedMatchupHybridModel._project_event_components(
                self,
                row,
                position,
                90.0,
                clean_sheet_minutes=90.0,
                p_sixty_mins=1.0,
            )
            f_rate = float(stock["xp_assists"]) / 3.0
            if not math.isfinite(f_rate):
                continue
            m = minutes_by_player.get(key[0], 0.0)
            if not math.isfinite(m) or m < 0.0:
                m = 0.0
            blended[key] = (m * g_rate + self.k * f_rate) / (m + self.k)
        return blended


_GRID = (("ext_02_1_k180", 180.0), ("ext_02_1_k450", 450.0))
PROTOTYPES = {
    name: type(
        name,
        (PlayerExposureAssistHandoverModel,),
        {"variant_name": name, "k": k},
    )
    for name, k in _GRID
}
_MANIFEST = (
    "features.player_id",
    "features.fixture_id",
    "features.position_id",
    "features.per90_xa",
    "features.per90_creativity",
    "features.per90_assists",
    "features.attack_multiplier",
    "features.difficulty",
    "features.club_id",
    "features.opponent_id",
    "features.is_home",
    "features.gameweek_id",
    "history.player_id",
    "history.fixture_id",
    "history.gameweek_id",
    "history.minutes",
    "history.expected_goals",
    "history.expected_assists",
    "history.creativity",
    "history.opponent_club_id",
    "history.was_home",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
COMPONENTS = {name: "xp_assists" for name in PROTOTYPES}
