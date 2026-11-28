"""Participation-state hybrid projection model.

The model keeps event scoring from ``metrics_component_hybrid`` but separates
Did Not Play, Start, and Sub-in outcomes before calculating xMins and xP.
"""

from collections import defaultdict

import pandas as pd

from models.native_scoring_context import native_scoring_context

from models.base import cap_projected_minutes, iter_feature_rows
from models.metrics_component_hybrid import (
    MetricsComponentHybridModel,
    _POS_CODE,
    _number,
)


ORACLE_STATE_COLUMNS: tuple[str, ...] = (
    "oracle_p_start",
    "oracle_p_sub_in",
    "oracle_p_dnp",
    "oracle_minutes",
    "oracle_p_60",
)


def _validate_oracle_state_columns(features_df: pd.DataFrame) -> bool:
    """Return True if all Oracle Participation State columns are present, False if none, else raise."""
    present = [col for col in ORACLE_STATE_COLUMNS if col in features_df.columns]
    if not present:
        return False
    if len(present) != len(ORACLE_STATE_COLUMNS):
        missing = [col for col in ORACLE_STATE_COLUMNS if col not in features_df.columns]
        raise ValueError(f"Partial Oracle state columns provided; missing: {missing}")
    return True


def extract_oracle_state_row(
    row: pd.Series,
) -> tuple[float, float, float, float, float, float, float, float]:
    """Return clamped Oracle Participation State tuple ``(p_dnp, p_start, p_sub_in, start_mins, sub_mins, p60_start, p60_sub, expected_mins)``."""
    p_start = _clamp01(float(row["oracle_p_start"]))
    p_sub_in = _clamp01(float(row["oracle_p_sub_in"]))
    p_dnp = _clamp01(float(row["oracle_p_dnp"]))
    oracle_mins = max(0.0, float(row["oracle_minutes"]))
    oracle_p60 = _clamp01(float(row["oracle_p_60"]))
    start_minutes = oracle_mins if p_start > 0.0 else 0.0
    sub_minutes = oracle_mins if p_sub_in > 0.0 else 0.0
    p60_start = oracle_p60 if p_start > 0.0 else 0.0
    p60_sub = oracle_p60 if p_sub_in > 0.0 else 0.0
    return p_dnp, p_start, p_sub_in, start_minutes, sub_minutes, p60_start, p60_sub, oracle_mins


def target_to_states(xmins: float) -> tuple[float, float, float, float, float]:
    """Convert external xmins into (p_start, p_sub_in, p_dnp, start_minutes, sub_minutes)."""
    if xmins <= 0.0:
        return 0.0, 0.0, 1.0, 0.0, 0.0
    if xmins >= 70.0:
        start_mins = min(90.0, max(75.0, xmins / 0.98))
        p_start = min(0.99, xmins / start_mins)
        p_sub = 0.0
        p_dnp = max(0.0, 1.0 - p_start)
        sub_mins = 18.0
        return p_start, p_sub, p_dnp, start_mins, sub_mins
    elif xmins > 18.0:
        start_mins = 78.0
        sub_mins = 18.0
        p_start = max(0.0, (xmins - 12.0) / (78.0 - 12.0))
        rem = max(0.0, xmins - p_start * start_mins)
        p_sub = min(0.8, rem / sub_mins)
        p_dnp = max(0.0, 1.0 - p_start - p_sub)
        return p_start, p_sub, p_dnp, start_mins, sub_mins
    else:
        start_mins = 78.0
        sub_mins = 18.0
        p_start = 0.0
        p_sub = min(1.0, xmins / sub_mins)
        p_dnp = max(0.0, 1.0 - p_sub)
        return p_start, p_sub, p_dnp, start_mins, sub_mins


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _normalize_probs(p_dnp: float, p_start: float, p_sub_in: float) -> tuple[float, float, float]:
    total = p_dnp + p_start + p_sub_in
    if total > 0.0 and abs(total - 1.0) > 1e-9:
        return p_dnp / total, p_start / total, p_sub_in / total
    return p_dnp, p_start, p_sub_in


def scale_states_to_target(
    p_dnp: float,
    p_start: float,
    p_sub_in: float,
    start_mins: float,
    sub_mins: float,
    p60_start: float,
    p60_sub: float,
    target_mins: float,
) -> tuple[float, float, float, float, float, float, float]:
    """Scale native participation states to ``target_mins`` while preserving conditional uncertainty."""
    target = max(0.0, float(target_mins))
    if target <= 0.0:
        return 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    native_mins = p_start * start_mins + p_sub_in * sub_mins
    if abs(target - native_mins) <= 1e-6:
        return p_dnp, p_start, p_sub_in, start_mins, sub_mins, p60_start, p60_sub

    if native_mins < 5.0 or (target > native_mins and start_mins <= 1e-6):
        ps, psub, pd, sm, subm = target_to_states(target)
        return pd, ps, psub, sm, subm, _clamp01((sm - 45.0) / 30.0), _clamp01((subm - 45.0) / 30.0)

    if target < native_mins:
        alpha = target / native_mins
        new_start = p_start * alpha
        new_sub = p_sub_in * alpha
        new_dnp = max(0.0, 1.0 - new_start - new_sub)
        new_dnp, new_start, new_sub = _normalize_probs(new_dnp, new_start, new_sub)
        return new_dnp, new_start, new_sub, start_mins, sub_mins, p60_start, p60_sub

    cur_dnp, cur_start, cur_sub = p_dnp, p_start, p_sub_in
    cur_sm, cur_p60_s = start_mins, p60_start
    cur_mins = native_mins

    if cur_sm > 1e-6 and cur_dnp > 0.0:
        dp = min(cur_dnp, max(0.0, 0.99 - cur_start), (target - cur_mins) / cur_sm)
        cur_start += dp
        cur_dnp -= dp
        cur_mins = cur_start * cur_sm + cur_sub * sub_mins

    if cur_mins < target - 1e-6 and cur_sub > 0.0 and cur_sm > sub_mins + 1e-6:
        dp = min(cur_sub, max(0.0, 0.99 - cur_start), (target - cur_mins) / (cur_sm - sub_mins))
        cur_start += dp
        cur_sub -= dp
        cur_mins = cur_start * cur_sm + cur_sub * sub_mins

    if cur_mins < target - 1e-6 and cur_start > 1e-6:
        cur_sm = min(90.0, max(cur_sm, (target - cur_sub * sub_mins) / cur_start))
        cur_p60_s = max(cur_p60_s, _clamp01((cur_sm - 45.0) / 30.0))
        cur_mins = cur_start * cur_sm + cur_sub * sub_mins

    # Reach targets in (89.1, 90.0] by finishing the final 0.99 -> 1.00 probability shift
    if cur_mins < target - 1e-6 and cur_sm > 1e-6:
        need = (target - cur_mins) / cur_sm
        take_dnp = min(cur_dnp, max(0.0, 1.0 - cur_start), need)
        cur_start += take_dnp
        cur_dnp -= take_dnp
        cur_mins = cur_start * cur_sm + cur_sub * sub_mins
        if cur_mins < target - 1e-6 and cur_sub > 0.0 and cur_sm > sub_mins + 1e-6:
            take_sub = min(cur_sub, max(0.0, 1.0 - cur_start), (target - cur_mins) / (cur_sm - sub_mins))
            cur_start += take_sub
            cur_sub -= take_sub

    cur_dnp, cur_start, cur_sub = _normalize_probs(cur_dnp, cur_start, cur_sub)
    return cur_dnp, cur_start, cur_sub, cur_sm, sub_mins, cur_p60_s, p60_sub


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
        native_scoring_context(features_df)
        has_oracle_cols = _validate_oracle_state_columns(features_df)
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

            if has_oracle_cols and all(pd.notna(row.get(col)) for col in ORACLE_STATE_COLUMNS):
                p_dnp, p_start, p_sub_in, start_minutes, sub_minutes, p60_start, p60_sub, expected_minutes = (
                    extract_oracle_state_row(row)
                )
            else:
                p_dnp, p_start, p_sub_in = self._state_probabilities(row)
                is_immediate = bool(row.get("is_immediate_next_gw", False))
                has_snapshot = bool(row.get("has_availability_snapshot", False))
                chance = _number(row, "chance_of_playing", 100.0)
                status = str(row.get("status", "")).lower()

                # Hard DNP for immediate next GW:
                # 1. In snapshot-backed backtests: chance <= 0.0 (ADR 0010)
                # 2. In live operational runs: chance <= 0.0 or status in {'i', 's', 'u', 'n'} (ADR 0056)
                if is_immediate and (
                    (has_snapshot and chance <= 0.0)
                    or (not has_snapshot and (chance <= 0.0 or status in {"i", "s", "u", "n"}))
                ):
                    p_dnp, p_start, p_sub_in = 1.0, 0.0, 0.0

                start_minutes = self._conditional_minutes(row, "start", 78.0)
                sub_minutes = self._conditional_minutes(row, "sub_in", 18.0)
                p60_start = _clamp01(_number(row, "p_60_if_start", (start_minutes - 45.0) / 30.0))
                p60_sub = _clamp01(_number(row, "p_60_if_sub_in", (sub_minutes - 45.0) / 30.0))

                raw_minutes = p_start * start_minutes + p_sub_in * sub_minutes
                expected_minutes = cap_projected_minutes(row, raw_minutes)
                if raw_minutes > 0 and expected_minutes < raw_minutes:
                    scale = expected_minutes / raw_minutes
                    start_minutes *= scale
                    sub_minutes *= scale

                ext_mins = row.get("external_xmins")
                if ext_mins is not None and pd.notna(ext_mins):
                    target_mins = max(0.0, float(ext_mins))
                    p_dnp, p_start, p_sub_in, start_minutes, sub_minutes, p60_start, p60_sub = scale_states_to_target(
                        p_dnp,
                        p_start,
                        p_sub_in,
                        start_minutes,
                        sub_minutes,
                        p60_start,
                        p60_sub,
                        target_mins,
                    )
                    expected_minutes = target_mins

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
