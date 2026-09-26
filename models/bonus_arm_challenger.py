"""PROTOTYPE bonus-arm Candidate stub (wayfinder #126).

Throwaway identity vs ``defence_link_challenger`` until #127 locks levers.
Non-flat BPS hooks only — **no** flat ``xp_bonus *= k`` (out per #124/#125).

Placeholder knobs (identity defaults = shipped Champion-path bonus form):
- ``_BONUS_SOFTMAX_T`` — fixture allocation temperature (ADR 0007; shipped 6.0)
- ``_XBPS_WEIGHTS`` — mins/goals/assists/CS/Defcon/saves (documented; wired in #127)
- ``_BONUS_ELIG_MINS`` — eligibility minutes gate (documented; wired in #127)

Do not Admission-race or ``--apply`` from this stub alone.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from models.defence_link_challenger import DefenceLinkChallengerModel

# Identity defaults — #127 may retune; must stay non-flat (not global xp_bonus scale).
_BONUS_SOFTMAX_T = 6.0
_BONUS_ELIG_MINS = 45.0
_XBPS_WEIGHTS = (0.1, 24.0, 12.0, 12.0, 6.0, 2.0)  # mins, goals, assists, CS, Defcon, saves


class BonusArmChallengerModel(DefenceLinkChallengerModel):
    """Defence-link stack plus placeholder BPS Bonus Model hooks (#126 stub)."""

    @property
    def name(self) -> str:
        return "bonus_arm_challenger"

    @staticmethod
    def _allocate_bonus(
        components: list[dict[str, object]],
        bonus_groups: defaultdict[int, list[int]],
    ) -> None:
        """Same Plackett-Luce form as metrics hybrid; temperature = ``_BONUS_SOFTMAX_T``."""
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
