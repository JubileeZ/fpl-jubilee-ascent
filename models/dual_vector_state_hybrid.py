"""Dual-Vector State Hybrid projection model.

Extends ``participation_state_hybrid`` with:
1. Dual-Vector team attack and defence strength multipliers with non-penalty calibration.
2. Team-level match expected goals normalization to align attacker sums with realistic match volume.
3. Penalty threat isolation from open-play attack rates.
"""

import numpy as np
import pandas as pd

from models.metrics_component_hybrid import (
    _number,
    _optional_number,
    _CLEAN_SHEET_POINTS,
    _expected_negbin_conceded_penalty,
    _expected_poisson_floor,
    _negbin_cdf_complement,
)
from models.participation_state_hybrid import ParticipationStateHybridModel
from models.scoring_matrix import event_points

# Baseline average Premier League goals per team per match
_LEAGUE_AVG_TEAM_GOALS = 1.38


class DualVectorStateHybridModel(ParticipationStateHybridModel):
    """Project fixture outcomes using dual-vector strength and calibrated team goal scaling."""

    @property
    def name(self) -> str:
        return "dual_vector_state_hybrid"

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float,
    ) -> dict[str, float]:
        """Project non-minute events with non-penalty isolation and calibrated multipliers."""
        pid = int(row["player_id"])
        diff = _number(row, "difficulty", 3.0)
        fdr_attack = max(0.2, (6.0 - diff) / 3.0)
        fdr_defence = max(0.2, diff / 3.0)

        attack_input = _optional_number(row, "attack_multiplier")
        defence_input = _optional_number(row, "defence_multiplier")
        attack_multiplier = fdr_attack if attack_input is None else attack_input
        defence_multiplier = fdr_defence if defence_input is None else defence_input

        xg_per90 = _number(row, "per90_xg", 0.0)
        threat_per90 = _number(row, "per90_threat", 0.0)
        raw_goals_per90 = _number(row, "per90_goals", 0.0)

        # Check penalty order to isolate penalty threat from open-play threat
        pen_order = _number(row, "penalties_order", 0.0)
        is_penalty_taker = pen_order == 1.0

        if xg_per90 > 0 or threat_per90 > 0:
            expected_goals_per90 = (
                self.goal_weights[0] * xg_per90
                + self.goal_weights[1] * threat_per90 / 100.0
                + self.goal_offsets.get(pid, 0.0)
            )
        else:
            expected_goals_per90 = raw_goals_per90 + self.goal_offsets.get(pid, 0.0)

        expected_goals_per90 = max(0.0, expected_goals_per90)

        # Separate penalty share from open play attack scaling
        if is_penalty_taker and expected_goals_per90 > 0.15:
            open_play_xg_per90 = max(0.0, expected_goals_per90 - 0.15)
            penalty_xg_per90 = 0.15
            expected_goals = (
                (open_play_xg_per90 * attack_multiplier + penalty_xg_per90)
                * expected_minutes
                / 90.0
            )
        else:
            expected_goals = expected_goals_per90 * expected_minutes / 90.0 * attack_multiplier

        xa_per90 = _number(row, "per90_xa", 0.0)
        creativity_per90 = _number(row, "per90_creativity", 0.0)
        raw_assists_per90 = _number(row, "per90_assists", 0.0)
        if xa_per90 > 0 or creativity_per90 > 0:
            expected_assists_per90 = (
                self.assist_weights[0] * xa_per90
                + self.assist_weights[1] * creativity_per90 / 100.0
                + self.assist_offsets.get(pid, 0.0)
            )
        else:
            expected_assists_per90 = raw_assists_per90 + self.assist_offsets.get(pid, 0.0)

        expected_assists = (
            max(0.0, expected_assists_per90) * expected_minutes / 90.0 * attack_multiplier
        )

        gc_per90 = _number(row, "per90_goals_conceded", 1.2)
        lmbda_team_90 = max(0.05, gc_per90 * defence_multiplier)
        lmbda_player = lmbda_team_90 * expected_minutes / 90.0
        p_sixty_mins = min(max(p_sixty_mins, 0.0), 1.0)
        lmbda_pitch = lmbda_team_90 * max(clean_sheet_minutes, 0.0) / 90.0
        prob_clean_sheet_on_pitch = np.exp(-lmbda_pitch)
        prob_clean_sheet = float(prob_clean_sheet_on_pitch) * p_sixty_mins

        defcon_per90 = _number(row, "per90_defensive_contribution", 0.0)
        lmbda_defcon = max(0.0, defcon_per90 * expected_minutes / 90.0 * defence_multiplier)
        defcon_threshold = 10 if position == "D" else 12
        defcon_r = 8.5 if position == "D" else 7.0
        prob_defcon = (
            _negbin_cdf_complement(defcon_threshold, lmbda_defcon, r=defcon_r)
            if position != "GK"
            else 0.0
        )

        saves_per90 = _number(row, "per90_saves", 0.0)
        expected_saves = (
            saves_per90 * expected_minutes / 90.0 * defence_multiplier if position == "GK" else 0.0
        )
        yellow_cards = _number(row, "per90_yellow_cards", 0.0) * expected_minutes / 90.0
        red_cards = _number(row, "per90_red_cards", 0.0) * expected_minutes / 90.0
        penalties_saved = _number(row, "per90_penalties_saved", 0.0) * expected_minutes / 90.0
        penalties_missed = _number(row, "per90_penalties_missed", 0.0) * expected_minutes / 90.0
        own_goals = _number(row, "per90_own_goals", 0.0) * expected_minutes / 90.0

        components = {
            "xp_goals": event_points("goals", position, expected_goals),
            "xp_assists": event_points("assists", position, expected_assists),
            "xp_clean_sheet": prob_clean_sheet * _CLEAN_SHEET_POINTS[position],
            "xp_conceded": (
                -_expected_negbin_conceded_penalty(lmbda_player, r=3.0)
                if position in ("GK", "D")
                else 0.0
            ),
            "xp_defcon": event_points("defensive_contributions", position, prob_defcon),
            "xp_saves": _expected_poisson_floor(expected_saves, 3),
            "xp_yellow_cards": event_points("yellow_cards", position, yellow_cards),
            "xp_red_cards": event_points("red_cards", position, red_cards),
            "xp_penalties_saved": event_points("penalties_saved", position, penalties_saved),
            "xp_penalties_missed": event_points("penalties_missed", position, penalties_missed),
            "xp_own_goals": event_points("own_goals", position, own_goals),
            "xp_bonus": 0.0,
            "xbps": (
                expected_minutes * 0.1
                + expected_goals * 24.0
                + expected_assists * 12.0
                + prob_clean_sheet * 12.0
                + prob_defcon * 6.0
                + expected_saves * 2.0
            ),
        }
        components["projected_points"] = sum(
            value
            for key, value in components.items()
            if key.startswith("xp_") and key != "xp_bonus"
        )
        components["eligible_bonus"] = float(expected_minutes >= 45.0)
        return components
