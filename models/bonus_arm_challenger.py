"""Bonus-arm Model Candidate (wayfinder #126 / #127 / #129).

Subclass of ``defence_link_challenger``: keeps goals + post-link CS/GC scales;
overrides BPS Bonus Model ``xbps`` weights and softmax temperature only.
**No** flat ``xp_bonus *= k`` (out per #124/#125/#127).

Calibrate via ``docs/research/champion-component-gap/calibrate_bonus_arm.py``.
Eligibility / allocation form frozen (#127).
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from models.defence_link_challenger import DefenceLinkChallengerModel
from models.metrics_component_hybrid import (
    _CLEAN_SHEET_POINTS,
    _number,
    _optional_number,
)

# Frozen by calibrate_bonus_arm.py (#129): mins_60/ALL xp_bonus bias then T grid.
_BONUS_SOFTMAX_T = 8.0
_BONUS_ELIG_MINS = 45.0  # documented; eligibility frozen (#127) — not wired
_XBPS_WEIGHTS = (0.1, 96.0, 48.0, 48.0, 24.0, 8.0)  # mins, goals, assists, CS, Defcon, saves; event k=4

_GOAL_POINTS = {"GK": 10.0, "D": 6.0, "M": 5.0, "F": 4.0}
_DEFCON_POINTS = {"GK": 0.0, "D": 2.0, "M": 2.0, "F": 2.0}


class BonusArmChallengerModel(DefenceLinkChallengerModel):
    """Defence-link stack plus non-flat BPS Bonus Model levers (#129)."""

    @property
    def name(self) -> str:
        return "bonus_arm_challenger"

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float,
    ) -> dict[str, float]:
        """Parent Event Components; ``xbps`` rebuilt from ``_XBPS_WEIGHTS`` only."""
        components = super()._project_event_components(
            row,
            position,
            expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes,
            p_sixty_mins=p_sixty_mins,
        )
        w_mins, w_goals, w_assists, w_cs, w_defcon, w_saves = _XBPS_WEIGHTS
        goal_pts = _GOAL_POINTS[position]
        expected_goals = float(components["xp_goals"]) / goal_pts if goal_pts else 0.0
        expected_assists = float(components["xp_assists"]) / 3.0
        cs_pts = _CLEAN_SHEET_POINTS[position]
        prob_clean_sheet = float(components["xp_clean_sheet"]) / cs_pts if cs_pts else 0.0
        dc_pts = _DEFCON_POINTS[position]
        prob_defcon = float(components["xp_defcon"]) / dc_pts if dc_pts else 0.0
        expected_saves = self._expected_saves(row, position, expected_minutes)
        components["xbps"] = (
            expected_minutes * w_mins
            + expected_goals * w_goals
            + expected_assists * w_assists
            + prob_clean_sheet * w_cs
            + prob_defcon * w_defcon
            + expected_saves * w_saves
        )
        return components

    @staticmethod
    def _expected_saves(row: pd.Series, position: str, expected_minutes: float) -> float:
        if position != "GK":
            return 0.0
        diff = _number(row, "difficulty", 3.0)
        fdr_defence = max(0.2, diff / 3.0)
        defence_input = _optional_number(row, "defence_multiplier")
        defence_multiplier = fdr_defence if defence_input is None else defence_input
        saves_per90 = _number(row, "per90_saves", 0.0)
        return saves_per90 * expected_minutes / 90.0 * defence_multiplier

    @staticmethod
    def _allocate_bonus(
        components: list[dict[str, object]],
        bonus_groups: defaultdict[int, list[int]],
    ) -> None:
        """Plackett-Luce fixture tiers; temperature = ``_BONUS_SOFTMAX_T``."""
        temperature = float(_BONUS_SOFTMAX_T)
        if temperature <= 0.0:
            raise ValueError("_BONUS_SOFTMAX_T must be > 0")
        for indices in bonus_groups.values():
            xbps_values = np.array([float(components[index]["xbps"]) for index in indices])
            logits = xbps_values / temperature
            logits -= logits.max()
            exp_logits = np.exp(logits)
            first = exp_logits / exp_logits.sum()
            second = np.zeros(len(indices))
            third = np.zeros(len(indices))

            for i in range(len(indices)):
                remaining = np.ones(len(indices), dtype=bool)
                remaining[i] = False
                if not remaining.any():
                    continue
                second_probs = exp_logits[remaining] / exp_logits[remaining].sum()
                remaining_indices = np.flatnonzero(remaining)
                for second_index, player_index in enumerate(remaining_indices):
                    second[player_index] += first[i] * second_probs[second_index]
                    remaining_after_second = remaining.copy()
                    remaining_after_second[player_index] = False
                    if not remaining_after_second.any():
                        continue
                    third_probs = (
                        exp_logits[remaining_after_second]
                        / exp_logits[remaining_after_second].sum()
                    )
                    third[remaining_after_second] += (
                        first[i] * second_probs[second_index] * third_probs
                    )

            expected_bonus = 3.0 * first + 2.0 * second + third
            for index, bonus in zip(indices, expected_bonus, strict=True):
                components[index]["xp_bonus"] = float(bonus)
                components[index]["projected_points"] = (
                    float(components[index]["projected_points"]) + float(bonus)
                )
