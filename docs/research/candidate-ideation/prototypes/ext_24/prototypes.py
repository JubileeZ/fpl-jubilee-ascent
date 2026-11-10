from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class _BaseEXT24(DefXgShrinkChallengerModel):
    variant_name: str = ""
    gamma_budget: float = 0.22
    cost_cutoff: float = 55.0

    def __init__(
        self,
        gamma_budget: float | None = None,
        cost_cutoff: float | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__()
        self.gamma_budget = float(
            gamma_budget if gamma_budget is not None else self.gamma_budget
        )
        self.cost_cutoff = float(
            cost_cutoff if cost_cutoff is not None else self.cost_cutoff
        )

    @property
    def name(self) -> str:
        return self.variant_name

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
        if position not in ("M", "F"):
            return components

        position_id = row.get("position_id")
        if position_id is not None and not pd.isna(position_id):
            try:
                if int(position_id) not in (3, 4):
                    return components
            except (ValueError, TypeError):
                pass

        now_cost_raw = row.get("now_cost", 100.0)
        now_cost = float(pd.to_numeric(now_cost_raw, errors="coerce"))
        if np.isnan(now_cost):
            now_cost = 100.0

        diff_raw = row.get("difficulty", 3.0)
        difficulty = float(pd.to_numeric(diff_raw, errors="coerce"))
        if np.isnan(difficulty):
            difficulty = 3.0

        price_weight = max(0.0, (self.cost_cutoff - now_cost) / 15.0)
        if price_weight <= 0.0:
            return components

        mult = 1.0 + self.gamma_budget * price_weight * ((3.0 - difficulty) / 2.0)
        if mult == 1.0:
            return components

        old_xp_goals = float(components["xp_goals"])
        new_xp_goals = max(0.0, old_xp_goals * mult)
        delta_goals = new_xp_goals - old_xp_goals

        old_xp_assists = float(components["xp_assists"])
        new_xp_assists = max(0.0, old_xp_assists * mult)
        delta_assists = new_xp_assists - old_xp_assists

        components["xp_goals"] = new_xp_goals
        components["xp_assists"] = new_xp_assists
        components["projected_points"] += delta_goals + delta_assists

        delta_goal_events = delta_goals / (5.0 if position == "M" else 4.0)
        delta_assist_events = delta_assists / 3.0
        components["xbps"] += 24.0 * delta_goal_events + 12.0 * delta_assist_events

        return components


def _make_variant(
    name: str, gamma_budget: float, cost_cutoff: float
) -> type[_BaseEXT24]:
    return type(
        name,
        (_BaseEXT24,),
        {
            "variant_name": name,
            "gamma_budget": float(gamma_budget),
            "cost_cutoff": float(cost_cutoff),
        },
    )


_GRID = (
    ("ext_24_g15_c55", 0.15, 55.0),
    ("ext_24_g22_c55", 0.22, 55.0),
    ("ext_24_g30_c55", 0.30, 55.0),
    ("ext_24_g20_c60", 0.20, 60.0),
    ("ext_24_g28_c60", 0.28, 60.0),
    ("ext_24_g35_c60", 0.35, 60.0),
)

PROTOTYPES = {name: _make_variant(name, g, c) for name, g, c in _GRID}
_MANIFEST = (
    "features.position_id",
    "features.now_cost",
    "features.difficulty",
    "local.xbps",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
