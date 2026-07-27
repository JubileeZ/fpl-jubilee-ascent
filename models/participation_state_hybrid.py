"""Participation-state hybrid projection model.

The model keeps event scoring from ``metrics_component_hybrid`` but separates
Did Not Play, Start, and Sub-in outcomes before calculating xMins and xP.
"""

from collections import defaultdict

import pandas as pd

from models.base import cap_projected_minutes, iter_feature_rows
from models.metrics_component_hybrid import (
    MetricsComponentHybridModel,
    _POS_CODE,
    _number,
)


class ParticipationStateHybridModel(MetricsComponentHybridModel):
    """Project fixture outcomes through mutually exclusive participation states."""

    @property
    def name(self) -> str:
        return "participation_state_hybrid"

    @staticmethod
    def _state_probabilities(row: pd.Series) -> tuple[float, float, float]:
        p_start = max(0.0, _number(row, "p_start", _number(row, "p_start_prior", 0.0)))
        p_sub_in = max(0.0, _number(row, "p_sub_in", _number(row, "p_sub_in_prior", 0.0)))
        p_dnp = max(0.0, _number(row, "p_dnp", _number(row, "p_dnp_prior", 0.0)))
        total = p_dnp + p_start + p_sub_in
        if total <= 0:
            appearance = min(
                1.0,
                max(0.0, _number(row, "appearance_probability", 1.0)),
            )
            average_minutes = _number(row, "avg_mins_3gw", 0.0)
            p_start = min(appearance, average_minutes / 78.0) if average_minutes > 0 else 0.0
            p_sub_in = max(0.0, appearance - p_start)
            p_dnp = 1.0 - appearance
            total = p_dnp + p_start + p_sub_in
        return p_dnp / total, p_start / total, p_sub_in / total

    @staticmethod
    def _conditional_minutes(row: pd.Series, state: str, default: float) -> float:
        return max(0.0, _number(row, f"xmins_if_{state}", default))

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        components: list[dict[str, object]] = []
        bonus_groups: defaultdict[int, list[int]] = defaultdict(list)
        component_columns = (
            "xp_minutes",
            "xp_goals",
            "xp_assists",
            "xp_clean_sheet",
            "xp_conceded",
            "xp_defcon",
            "xp_saves",
            "xp_yellow_cards",
            "xp_red_cards",
            "xp_penalties_saved",
            "xp_penalties_missed",
            "xp_own_goals",
            "xp_bonus",
        )

        for row, gameweek_id, fixture_id in iter_feature_rows(features_df, horizon):
            if fixture_id is not None and fixture_id < 0:
                components.append({
                    "player_id": int(row["player_id"]),
                    "gameweek_id": gameweek_id,
                    "fixture_id": fixture_id,
                    "projected_points": 0.0,
                    "projected_minutes": 0.0,
                    "xbps": 0.0,
                    "p_dnp": 1.0,
                    "p_start": 0.0,
                    "p_sub_in": 0.0,
                })
                continue

            p_dnp, p_start, p_sub_in = self._state_probabilities(row)
            is_immediate = bool(row.get("is_immediate_next_gw", False))
            has_snapshot = bool(row.get("has_availability_snapshot", False))
            chance = _number(row, "chance_of_playing", 100.0)
            if is_immediate and has_snapshot and chance <= 0.0:
                p_dnp, p_start, p_sub_in = 1.0, 0.0, 0.0

            start_minutes = self._conditional_minutes(row, "start", 78.0)
            sub_minutes = self._conditional_minutes(row, "sub_in", 18.0)
            p60_start = min(
                1.0,
                max(0.0, _number(row, "p_60_if_start", (start_minutes - 45.0) / 30.0)),
            )
            p60_sub = min(
                1.0,
                max(0.0, _number(row, "p_60_if_sub_in", (sub_minutes - 45.0) / 30.0)),
            )

            raw_minutes = p_start * start_minutes + p_sub_in * sub_minutes
            expected_minutes = cap_projected_minutes(row, raw_minutes)
            if raw_minutes > 0 and expected_minutes < raw_minutes:
                scale = expected_minutes / raw_minutes
                start_minutes *= scale
                sub_minutes *= scale

            position = _POS_CODE.get(int(_number(row, "position_id", 3.0)), "M")
            start_events = self._project_event_components(
                row,
                position,
                start_minutes,
                clean_sheet_minutes=start_minutes,
                p_sixty_mins=p60_start,
            )
            sub_events = self._project_event_components(
                row,
                position,
                sub_minutes,
                clean_sheet_minutes=sub_minutes,
                p_sixty_mins=p60_sub,
            )
            weighted_events = {
                key: p_start * float(start_events[key]) + p_sub_in * float(sub_events[key])
                for key in start_events
                if key not in {"eligible_bonus", "projected_points"}
            }
            xp_minutes = p_start * (1.0 + p60_start) + p_sub_in * (1.0 + p60_sub)
            weighted_points = (
                p_start * float(start_events["projected_points"])
                + p_sub_in * float(sub_events["projected_points"])
            )
            eligible_bonus = (
                (p_start if start_minutes >= 45.0 else 0.0)
                + (p_sub_in if sub_minutes >= 45.0 else 0.0)
            )
            index = len(components)
            components.append({
                "player_id": int(row["player_id"]),
                "gameweek_id": gameweek_id,
                "fixture_id": fixture_id,
                "projected_points": xp_minutes + weighted_points,
                "projected_minutes": expected_minutes,
                "xbps": weighted_events["xbps"],
                "xp_minutes": xp_minutes,
                "p_dnp": p_dnp,
                "p_start": p_start,
                "p_sub_in": p_sub_in,
                "xmins_if_start": start_minutes,
                "xmins_if_sub_in": sub_minutes,
                "p_60_if_start": p60_start,
                "p_60_if_sub_in": p60_sub,
                **weighted_events,
            })
            if eligible_bonus > 0 and fixture_id is not None and fixture_id >= 0:
                bonus_groups[fixture_id].append(index)

        self._allocate_bonus(components, bonus_groups)
        output = []
        for component in components:
            prediction = {
                "player_id": component["player_id"],
                "gameweek_id": component["gameweek_id"],
                "projected_points": component["projected_points"],
                "projected_minutes": component["projected_minutes"],
                **{
                    column: component.get(column, 0.0)
                    for column in component_columns
                },
                "p_dnp": component.get("p_dnp", 1.0),
                "p_start": component.get("p_start", 0.0),
                "p_sub_in": component.get("p_sub_in", 0.0),
                "xmins_if_start": component.get("xmins_if_start", 0.0),
                "xmins_if_sub_in": component.get("xmins_if_sub_in", 0.0),
                "p_60_if_start": component.get("p_60_if_start", 0.0),
                "p_60_if_sub_in": component.get("p_60_if_sub_in", 0.0),
            }
            if component["fixture_id"] is not None:
                prediction["fixture_id"] = component["fixture_id"]
            output.append(prediction)
        return pd.DataFrame(output)
