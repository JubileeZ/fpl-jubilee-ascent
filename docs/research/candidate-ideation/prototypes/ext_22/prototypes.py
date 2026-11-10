from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT22(DefXgShrinkChallengerModel):
    variant_name: str = ""
    beta_venue: float = 0.09
    k_venue: float = 4.0

    def __init__(
        self,
        beta_venue: float | None = None,
        k_venue: float | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__()
        self.beta_venue = float(
            beta_venue if beta_venue is not None else self.beta_venue
        )
        self.k_venue = float(
            k_venue if k_venue is not None else self.k_venue
        )
        self._player_matches: dict[int, int] = {}

    @property
    def name(self) -> str:
        return self.variant_name

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._player_matches = {}
        if not history_df.empty and {"player_id", "minutes"}.issubset(history_df.columns):
            mins = pd.to_numeric(history_df["minutes"], errors="coerce").fillna(0.0)
            valid = history_df[mins > 0]
            if not valid.empty:
                counts = valid.groupby("player_id").size()
                self._player_matches = {
                    int(p): int(c)
                    for p, c in counts.items()
                    if pd.notna(p)
                }

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
            row,
            position,
            expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes,
            p_sixty_mins=p_sixty_mins,
        )
        pid = int(row["player_id"])
        n_i = self._player_matches.get(pid, 0)
        denom = float(n_i) + self.k_venue
        if denom <= 0.0:
            return components
        w_v = float(n_i) / denom
        if w_v <= 0.0:
            return components

        is_home = bool(row.get("is_home", True))
        direction = 1.0 if is_home else -1.0
        v_mult = float(np.exp(w_v * self.beta_venue * direction))
        if v_mult == 1.0:
            return components

        old_xp_goals = float(components["xp_goals"])
        new_xp_goals = max(0.0, old_xp_goals * v_mult)
        delta_goals = new_xp_goals - old_xp_goals

        old_xp_assists = float(components["xp_assists"])
        new_xp_assists = max(0.0, old_xp_assists * v_mult)
        delta_assists = new_xp_assists - old_xp_assists

        components["xp_goals"] = new_xp_goals
        components["xp_assists"] = new_xp_assists
        components["projected_points"] += delta_goals + delta_assists

        goal_pts = (
            5.0
            if position == "M"
            else (4.0 if position == "F" else (6.0 if position == "D" else 10.0))
        )
        delta_goal_events = delta_goals / goal_pts
        delta_assist_events = delta_assists / 3.0
        components["xbps"] += 24.0 * delta_goal_events + 12.0 * delta_assist_events
        return components


def _make_variant(name: str, beta_venue: float, k_venue: float) -> type[_BaseEXT22]:
    return type(
        name,
        (_BaseEXT22,),
        {
            "variant_name": name,
            "beta_venue": float(beta_venue),
            "k_venue": float(k_venue),
        },
    )


_GRID = (
    ("ext_22_b06_k4", 0.06, 4.0),
    ("ext_22_b09_k4", 0.09, 4.0),
    ("ext_22_b12_k4", 0.12, 4.0),
    ("ext_22_b08_k6", 0.08, 6.0),
    ("ext_22_b10_k6", 0.10, 6.0),
    ("ext_22_b14_k8", 0.14, 8.0),
)

PROTOTYPES = {name: _make_variant(name, b, k) for name, b, k in _GRID}
_MANIFEST = (
    "features.is_home",
    "features.per90_xg",
    "features.per90_xa",
    "features.position_id",
    "history.player_id",
    "history.minutes",
    "local.xbps",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
