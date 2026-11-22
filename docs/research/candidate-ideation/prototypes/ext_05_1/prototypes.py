"""EXT-05_1: negative binomial dispersion for goalkeeper save-threshold expectation."""

from __future__ import annotations

import math

import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.metrics_component_hybrid import _number, _optional_number

_OMEGA = complex(-0.5, math.sqrt(3.0) / 2.0)


def _expected_negbin_floor3(mu: float, r: float) -> float:
    """Return exact E[floor(S / 3)] for S ~ NegativeBinomial(mean=mu, shape=r)."""
    if not math.isfinite(mu) or mu <= 0.0 or not math.isfinite(r) or r <= 0.0:
        return 0.0
    pgf = (1.0 + mu * (1.0 - _OMEGA) / r) ** (-r)
    conj_omega = _OMEGA.conjugate()
    p1 = (1.0 + 2.0 * (conj_omega * pgf).real) / 3.0
    p2 = (1.0 + 2.0 * ((conj_omega**2) * pgf).real) / 3.0
    return max(0.0, (mu - p1 - 2.0 * p2) / 3.0)


class GoalkeeperSaveCountDispersionModel(DefXgShrinkChallengerModel):
    """Replace GK Poisson save expectation with NegBin threshold expectation at fixed mu."""

    variant_name: str = "ext_05_1_r3"
    r: float = 3.0

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
        if position != "GK":
            return components

        diff = _number(row, "difficulty", 3.0)
        fdr_defence = max(0.2, diff / 3.0)
        defence_input = _optional_number(row, "defence_multiplier")
        defence_multiplier = fdr_defence if defence_input is None else defence_input
        saves_per90 = _number(row, "per90_saves", 0.0)
        expected_saves = saves_per90 * expected_minutes / 90.0 * defence_multiplier

        old_xp_saves = float(components["xp_saves"])
        new_xp_saves = _expected_negbin_floor3(expected_saves, self.r)
        updated = dict(components)
        updated["xp_saves"] = new_xp_saves
        updated["projected_points"] = float(components["projected_points"]) + (
            new_xp_saves - old_xp_saves
        )
        return updated


_GRID = (("ext_05_1_r3", 3.0), ("ext_05_1_r8", 8.0))
PROTOTYPES = {
    name: type(
        name,
        (GoalkeeperSaveCountDispersionModel,),
        {"variant_name": name, "r": r},
    )
    for name, r in _GRID
}
_MANIFEST = (
    "features.position_id",
    "features.per90_saves",
    "features.defence_multiplier",
    "features.difficulty",
    "features.xmins_if_start",
    "features.xmins_if_sub_in",
)
FEATURES = {name: _MANIFEST for name in PROTOTYPES}
COMPONENTS = {name: "xp_saves" for name in PROTOTYPES}
