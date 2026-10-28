from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from backtesting.walkforward import LEDGER_COMPONENTS
from features.contracts import assert_projection_contract
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel
from models.base import cap_projected_minutes, resolve_asof_target_gw
from models.learned_start_challenger import LearnedStartChallengerModel, blend_states
from models.metrics_component_hybrid import _POS_CODE
from models.ml_component_challenger import _ridge_poisson_irls
from models.ml_panel_features import CausalFeatureScaler, build_causal_panel
from models.scoring_matrix import event_points


class TrackAH1Only(AdaptiveCausalChallengerModel):
    def __init__(self) -> None:
        super().__init__(
            enable_mins_h1=True,
            enable_mins_h2=False,
            enable_mins_h3=False,
            enable_goals=False,
            enable_assists=False,
        )

    @property
    def name(self) -> str:
        return "track_a_h1_only"


class TrackAH3Only(AdaptiveCausalChallengerModel):
    def __init__(self) -> None:
        super().__init__(
            enable_mins_h1=False,
            enable_mins_h2=False,
            enable_mins_h3=True,
            enable_goals=False,
            enable_assists=False,
        )

    @property
    def name(self) -> str:
        return "track_a_h3_only"


class TrackAMinsH1H3(AdaptiveCausalChallengerModel):
    def __init__(self) -> None:
        super().__init__(
            enable_mins_h1=True,
            enable_mins_h2=False,
            enable_mins_h3=True,
            enable_goals=False,
            enable_assists=False,
        )

    @property
    def name(self) -> str:
        return "track_a_mins_h1_h3"


class TrackAExposureReplay(AdaptiveCausalChallengerModel):
    def __init__(
        self,
        *,
        enable_mins_h1: bool = True,
        enable_mins_h3: bool = True,
        enable_goals: bool = False,
        enable_assists: bool = False,
    ) -> None:
        super().__init__(
            enable_mins_h1=enable_mins_h1,
            enable_mins_h2=False,
            enable_mins_h3=enable_mins_h3,
            enable_goals=enable_goals,
            enable_assists=enable_assists,
        )
        self._effective_rows: dict[tuple[int, int, int], pd.Series] = {}
        self._capture_rows = False

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float,
    ) -> dict[str, float]:
        if self._capture_rows:
            key = (int(row["player_id"]), int(row["gameweek_id"]), int(row["fixture_id"]))
            self._effective_rows[key] = row.copy()
        return super()._project_event_components(
            row,
            position,
            expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes,
            p_sixty_mins=p_sixty_mins,
        )

    def _event_multipliers(self, features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray] | None:
        train, pred = build_causal_panel(self._history_df, features, min_train_gw=4)
        if train.empty or pred.empty:
            return None
        cols = [
            c
            for c in pred.columns
            if not c.startswith("target_") and c not in ("player_id", "gameweek_id", "fixture_id", "obs_count")
        ]
        scaler = CausalFeatureScaler().fit(train, cols)
        train_scaled = scaler.transform(train, obs_counts=train.get("obs_count"))
        pred_scaled = scaler.transform(pred, obs_counts=pred.get("obs_count"))
        goal_factors = np.ones(len(pred))
        g_cols = [
            "shrunk_xg90",
            "shot_quality_ratio",
            "club_xg_share",
            "finishing_offset_90",
            "team_att_ratio",
            "opp_def_ratio",
            "is_home",
        ]
        mask = (train["target_minutes"] > 0) & (train["target_expected_goals"] > 0)
        if self.enable_goals and int(mask.sum()) > 50:
            x_train = np.column_stack([np.ones(int(mask.sum())), train_scaled.loc[mask, g_cols].to_numpy()])
            offset = np.log(
                np.maximum(
                    train.loc[mask, "target_minutes"] / 90.0 * np.maximum(train.loc[mask, "shrunk_xg90"], 0.01),
                    1e-4,
                )
            )
            beta = _ridge_poisson_irls(
                x_train, train.loc[mask, "target_goals_blend"].to_numpy(), offset, lam=25.0
            )
            x_pred = np.column_stack([np.ones(len(pred)), pred_scaled[g_cols].to_numpy()])
            raw = np.exp(np.clip(x_pred @ beta, -0.4, 0.4))
            positions = pred["pos_gk"] + 2 * pred["pos_def"] + 3 * pred["pos_mid"] + 4 * pred["pos_fwd"]
            for _, group in pred.groupby("gameweek_id"):
                idx = group.index.to_numpy()
                norm = raw[idx] / max(float(np.mean(raw[idx])), 1e-4)
                for j, k in enumerate(idx):
                    pos = int(positions.iloc[k])
                    goal_factors[k] = (
                        1.0
                        if pos == 1
                        else float(
                            np.clip(norm[j], 0.90, 1.10) if pos == 2 else np.clip(norm[j], 0.75, 1.35)
                        )
                    )
        assist_factors = (
            pred["loo_teammate_finishing"].to_numpy() if self.enable_assists else np.ones(len(pred))
        )
        return goal_factors, assist_factors

    def _replay(
        self,
        features: pd.DataFrame,
        final: pd.DataFrame,
        goal_factors: np.ndarray,
        assist_factors: np.ndarray,
    ) -> pd.DataFrame:
        result = final.copy().reset_index(drop=True)
        components: list[dict[str, object]] = []
        for i, (_, state) in enumerate(result.iterrows()):
            key = (int(state["player_id"]), int(state["gameweek_id"]), int(state["fixture_id"]))
            if key[2] < 0:
                for col in LEDGER_COMPONENTS:
                    result.loc[i, col] = 0.0
                result.loc[i, "p_start"] = 0.0
                result.loc[i, "p_sub_in"] = 0.0
                result.loc[i, "p_dnp"] = 1.0
                result.loc[i, "projected_minutes"] = 0.0
                components.append({**state.to_dict(), "xbps": 0.0, "xp_bonus": 0.0, "projected_points": 0.0})
                continue
            row = self._effective_rows[key]
            p_start = float(np.clip(state["p_start"], 0.0, 1.0))
            p_sub = float(np.clip(state["p_sub_in"], 0.0, 1.0))
            p_dnp, p_start, p_sub = blend_states(1.0 - p_sub, 0.0, p_sub, p_start)
            start_m = float(state["xmins_if_start"])
            sub_m = float(state["xmins_if_sub_in"])
            p60_start = float(state["p_60_if_start"])
            p60_sub = float(state["p_60_if_sub_in"])
            raw_minutes = p_start * start_m + p_sub * sub_m
            external = row.get("external_xmins")
            expected_minutes = (
                raw_minutes if pd.notna(external) else max(0.0, cap_projected_minutes(row, raw_minutes))
            )
            if raw_minutes > 0 and expected_minutes < raw_minutes:
                scale = expected_minutes / raw_minutes
                start_m *= scale
                sub_m *= scale
            position = _POS_CODE[int(row["position_id"])]
            start_events = super()._project_event_components(
                row,
                position,
                start_m,
                clean_sheet_minutes=start_m,
                p_sixty_mins=p60_start,
            )
            sub_events = super()._project_event_components(
                row,
                position,
                sub_m,
                clean_sheet_minutes=sub_m,
                p_sixty_mins=p60_sub,
            )
            events = {
                c: p_start * float(start_events[c]) + p_sub * float(sub_events[c])
                for c in start_events
                if c not in {"eligible_bonus", "projected_points"}
            }
            old_goals, old_assists = events["xp_goals"], events["xp_assists"]
            events["xp_goals"] *= float(goal_factors[i])
            events["xp_assists"] *= float(assist_factors[i])
            events["xbps"] += 24.0 * (events["xp_goals"] - old_goals) / event_points(
                "goals", position, 1.0
            ) + 12.0 * (events["xp_assists"] - old_assists) / 3.0
            xp_minutes = p_start * (1.0 + p60_start) + p_sub * (1.0 + p60_sub)
            updates = {
                "p_start": p_start,
                "p_sub_in": p_sub,
                "p_dnp": p_dnp,
                "xmins_if_start": start_m,
                "xmins_if_sub_in": sub_m,
                "projected_minutes": expected_minutes,
                "xp_minutes": xp_minutes,
            }
            for col, value in updates.items():
                result.loc[i, col] = value
            for col in LEDGER_COMPONENTS:
                if col != "xp_minutes":
                    result.loc[i, col] = events[col]
            components.append({**state.to_dict(), **updates, **events, "projected_points": 0.0})
        LearnedStartChallengerModel._allocate_bonus(self, components, defaultdict(list))
        result["xp_bonus"] = [float(c["xp_bonus"]) for c in components]
        result["projected_points"] = result[list(LEDGER_COMPONENTS)].sum(axis=1)
        states = result[["p_dnp", "p_start", "p_sub_in"]].to_numpy()
        if not np.isfinite(states).all() or (states < 0).any() or not np.allclose(states.sum(axis=1), 1.0, atol=1e-12):
            raise ValueError("Replay probability simplex violated")
        expectation = result["p_start"] * result["xmins_if_start"] + result["p_sub_in"] * result["xmins_if_sub_in"]
        if not np.allclose(expectation, result["projected_minutes"], atol=1e-10):
            raise ValueError("Replay minutes expectation violated")
        result.index = final.index
        assert_projection_contract(result)
        return result

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._effective_rows = {}
        self._capture_rows = True
        try:
            final = super().predict(features_df, horizon)
        finally:
            self._capture_rows = False
        if (
            features_df.empty
            or resolve_asof_target_gw(features_df, self._history_df) < self.min_ml_gw
            or len(self._history_df) < 500
        ):
            return final
        features = features_df.reset_index(drop=True)
        multipliers = self._event_multipliers(features)
        if multipliers is None:
            return final
        return self._replay(features, final, *multipliers)


class TrackAMinsH1H3Coherent(TrackAExposureReplay):
    def __init__(self) -> None:
        super().__init__(
            enable_mins_h1=True,
            enable_mins_h3=True,
            enable_goals=False,
            enable_assists=False,
        )

    @property
    def name(self) -> str:
        return "track_a_mins_h1_h3_coherent"


class TrackAGroupBAssists(AdaptiveCausalChallengerModel):
    def __init__(self) -> None:
        super().__init__(
            enable_mins_h1=False,
            enable_mins_h2=False,
            enable_mins_h3=False,
            enable_goals=False,
            enable_assists=True,
        )

    @property
    def name(self) -> str:
        return "track_a_group_b_assists"


class TrackANoGoalsH1H3B(AdaptiveCausalChallengerModel):
    def __init__(self) -> None:
        super().__init__(
            enable_mins_h1=True,
            enable_mins_h2=False,
            enable_mins_h3=True,
            enable_goals=False,
            enable_assists=True,
        )

    @property
    def name(self) -> str:
        return "track_a_no_goals_h1_h3_b"


PROTOTYPES = {
    "track_a_h1_only": TrackAH1Only,
    "track_a_h3_only": TrackAH3Only,
    "track_a_mins_h1_h3": TrackAMinsH1H3,
    "track_a_mins_h1_h3_coherent": TrackAMinsH1H3Coherent,
    "track_a_group_b_assists": TrackAGroupBAssists,
    "track_a_no_goals_h1_h3_b": TrackANoGoalsH1H3B,
}

_COMMON_FEATURES = (
    "features.player_id",
    "features.fixture_id",
    "features.gameweek_id",
    "features.position_id",
    "features.external_xmins",
    "features.xmins_cap",
    "features.per90_xg",
    "features.per90_xa",
    "features.attack_multiplier",
    "features.defence_multiplier",
    "features.p_start",
    "features.p_sub_in",
    "features.p_dnp",
    "features.xmins_if_start",
    "features.xmins_if_sub_in",
    "features.p_60_if_start",
    "features.p_60_if_sub_in",
    "local.xbps",
    "local.eligible_bonus",
    "history.obs_count",
    "history.shrunk_xg90",
    "history.shot_quality_ratio",
    "history.club_xg_share",
    "history.finishing_offset_90",
    "history.team_att_ratio",
    "history.opp_def_ratio",
    "history.is_home",
    "history.target_minutes",
    "history.target_expected_goals",
    "history.target_goals_blend",
    "history.pos_gk",
    "history.pos_def",
    "history.pos_mid",
    "history.pos_fwd",
    "history.loo_teammate_finishing",
)

FEATURES = {name: _COMMON_FEATURES for name in PROTOTYPES}
