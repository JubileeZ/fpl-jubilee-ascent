"""PROTOTYPE: Decoupled Minutes & Event Architecture.

Throwaway prototype demonstrating the base interfaces, data structures, and composite
resolution for Ticket #160 (Wayfinder Map #159).

Run via:
    uv run python -m models.prototype_decoupled
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path
import sys

# Ensure repo root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from features.contracts import assert_projection_contract
from models.base import BaseModel, cap_projected_minutes, iter_feature_rows
from models.learned_start_challenger import LearnedStartChallengerModel
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from models.participation_state_hybrid import target_to_states
from models.metrics_component_hybrid import _number


@dataclass(frozen=True)
class MinutesPrediction:
    """Standardized minutes and participation probabilities container."""
    frame: pd.DataFrame

    def __post_init__(self) -> None:
        required = {
            "player_id", "gameweek_id", "p_dnp", "p_start", "p_sub_in",
            "xmins_if_start", "xmins_if_sub_in", "projected_minutes", "p_60_plus"
        }
        missing = required - set(self.frame.columns)
        if missing:
            raise ValueError(f"MinutesPrediction missing required columns: {sorted(missing)}")

    @property
    def p_dnp(self) -> pd.Series:
        return self.frame["p_dnp"]

    @property
    def p_start(self) -> pd.Series:
        return self.frame["p_start"]

    @property
    def p_sub_in(self) -> pd.Series:
        return self.frame["p_sub_in"]

    @property
    def projected_minutes(self) -> pd.Series:
        return self.frame["projected_minutes"]

    @property
    def p_60_plus(self) -> pd.Series:
        return self.frame["p_60_plus"]


class BaseMinutesModel(abc.ABC):
    """Abstract base class for standalone minutes and participation forecasting."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique identifier name for minutes model."""
        pass

    def fit(self, history_df: pd.DataFrame) -> None:
        """Optional pre-target history fit."""
        pass

    @abc.abstractmethod
    def predict_minutes(self, features_df: pd.DataFrame, horizon: int) -> MinutesPrediction:
        """Predict participation states and pitch duration."""
        pass


class BaseEventRateModel(abc.ABC):
    """Abstract base class for per-minute/per-90 event rates and scoring."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique identifier name for event rate model."""
        pass

    def fit(self, history_df: pd.DataFrame) -> None:
        """Optional pre-target history fit."""
        pass

    @abc.abstractmethod
    def predict_rates(
        self,
        features_df: pd.DataFrame,
        minutes_pred: MinutesPrediction,
        horizon: int,
    ) -> pd.DataFrame:
        """Predict 13 FPL score components conditioned on minutes."""
        pass


class CompositeProjectionModel(BaseModel):
    """Assembles a BaseMinutesModel and BaseEventRateModel into a standard BaseModel."""

    def __init__(
        self,
        minutes_model: BaseMinutesModel,
        event_model: BaseEventRateModel,
        name: str | None = None,
    ) -> None:
        self.minutes_model = minutes_model
        self.event_model = event_model
        self._name = name or f"composite:{minutes_model.name}:{event_model.name}"

    @property
    def name(self) -> str:
        return self._name

    def fit(self, history_df: pd.DataFrame) -> None:
        self.minutes_model.fit(history_df)
        self.event_model.fit(history_df)

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        # Check for external minutes override (e.g. Oracle minutes or manual override)
        if "external_xmins" in features_df.columns and features_df["external_xmins"].notna().any():
            minutes_pred = self._states_from_external_minutes(features_df, horizon)
        else:
            minutes_pred = self.minutes_model.predict_minutes(features_df, horizon)

        return self.event_model.predict_rates(features_df, minutes_pred, horizon)

    @staticmethod
    def _states_from_external_minutes(features_df: pd.DataFrame, horizon: int) -> MinutesPrediction:
        rows = []
        for row, gw, fix in iter_feature_rows(features_df, horizon):
            ext = row.get("external_xmins")
            if ext is not None and pd.notna(ext):
                target = max(0.0, float(ext))
                p_start, p_sub, p_dnp, start_m, sub_m = target_to_states(target)
                p60_start = min(1.0, max(0.0, (start_m - 45.0) / 30.0))
                p60_sub = min(1.0, max(0.0, (sub_m - 45.0) / 30.0))
                p60 = p_start * p60_start + p_sub * p60_sub
                xmins = target
            else:
                p_dnp, p_start, p_sub = 1.0, 0.0, 0.0
                start_m, sub_m, xmins, p60 = 0.0, 0.0, 0.0, 0.0

            rows.append({
                "player_id": int(row["player_id"]),
                "gameweek_id": gw,
                "fixture_id": fix,
                "p_dnp": p_dnp,
                "p_start": p_start,
                "p_sub_in": p_sub,
                "xmins_if_start": start_m,
                "xmins_if_sub_in": sub_m,
                "projected_minutes": xmins,
                "p_60_plus": p60,
            })
        return MinutesPrediction(pd.DataFrame(rows))


# --- Adapter implementations for existing Champion components ---

class LearnedStartMinutesAdapter(BaseMinutesModel):
    """Adapter exposing LearnedStart participation prediction as a BaseMinutesModel."""

    def __init__(self) -> None:
        self._inner = LearnedStartChallengerModel()

    @property
    def name(self) -> str:
        return "learned_start"

    def fit(self, history_df: pd.DataFrame) -> None:
        self._inner.fit(history_df)

    def predict_minutes(self, features_df: pd.DataFrame, horizon: int) -> MinutesPrediction:
        rows = []
        for row, gw, fix in iter_feature_rows(features_df, horizon):
            p_dnp, p_start, p_sub = self._inner._state_probabilities(row)
            start_m = self._inner._conditional_minutes(row, "start", 78.0)
            sub_m = self._inner._conditional_minutes(row, "sub_in", 18.0)
            p60_start = min(1.0, max(0.0, _number(row, "p_60_if_start", (start_m - 45.0) / 30.0)))
            p60_sub = min(1.0, max(0.0, _number(row, "p_60_if_sub_in", (sub_m - 45.0) / 30.0)))

            raw_mins = p_start * start_m + p_sub * sub_m
            expected_mins = cap_projected_minutes(row, raw_mins)
            p60 = p_start * p60_start + p_sub * p60_sub

            rows.append({
                "player_id": int(row["player_id"]),
                "gameweek_id": gw,
                "fixture_id": fix,
                "p_dnp": p_dnp,
                "p_start": p_start,
                "p_sub_in": p_sub,
                "xmins_if_start": start_m,
                "xmins_if_sub_in": sub_m,
                "projected_minutes": expected_mins,
                "p_60_plus": p60,
            })
        return MinutesPrediction(pd.DataFrame(rows))


class DefXgShrinkEventAdapter(BaseEventRateModel):
    """Adapter exposing DefXgShrink event rate scoring as a BaseEventRateModel."""

    def __init__(self) -> None:
        self._inner = DefXgShrinkChallengerModel()

    @property
    def name(self) -> str:
        return "def_xg_shrink"

    def fit(self, history_df: pd.DataFrame) -> None:
        self._inner.fit(history_df)

    def predict_rates(
        self,
        features_df: pd.DataFrame,
        minutes_pred: MinutesPrediction,
        horizon: int,
    ) -> pd.DataFrame:
        # Align features with minutes_pred
        feat_with_mins = features_df.copy()
        if "projected_minutes" not in feat_with_mins.columns:
            feat_with_mins["external_xmins"] = minutes_pred.frame["projected_minutes"].to_numpy()
        return self._inner.predict(feat_with_mins, horizon)


def resolve_composite_spec(spec: str) -> CompositeProjectionModel:
    """Resolve dynamic composite model spec 'composite:<mins>:<event>'."""
    if not spec.startswith("composite:"):
        raise ValueError(f"Not a composite spec: {spec}")
    parts = spec.split(":")
    if len(parts) != 3:
        raise ValueError(f"Composite spec must be 'composite:<mins>:<event>', got: {spec}")

    mins_key, event_key = parts[1], parts[2]
    # Minutes registry mapping
    mins_registry: dict[str, type[BaseMinutesModel]] = {
        "learned_start": LearnedStartMinutesAdapter,
    }
    # Event registry mapping
    event_registry: dict[str, type[BaseEventRateModel]] = {
        "def_xg_shrink": DefXgShrinkEventAdapter,
    }

    if mins_key not in mins_registry:
        raise KeyError(f"Unknown minutes model: '{mins_key}'. Available: {list(mins_registry.keys())}")
    if event_key not in event_registry:
        raise KeyError(f"Unknown event model: '{event_key}'. Available: {list(event_registry.keys())}")

    return CompositeProjectionModel(
        minutes_model=mins_registry[mins_key](),
        event_model=event_registry[event_key](),
        name=spec,
    )


def run_prototype_smoke() -> None:
    """Smoke test running on real repository features."""
    from features.builder import build_features, resolve_operational_processed_dir
    processed_dir = resolve_operational_processed_dir(Path("."))
    print(f"Loading features from {processed_dir}...")
    df_feat = build_features(processed_dir, target_gw=6, horizon=1)
    print(f"Features loaded: {len(df_feat)} rows.")

    spec = "composite:learned_start:def_xg_shrink"
    print(f"Instantiating composite model: '{spec}'...")
    composite_model = resolve_composite_spec(spec)

    perf_path = processed_dir / "player_performances.parquet"
    if perf_path.exists():
        df_perf = pd.read_parquet(perf_path)
        print(f"Fitting model with {len(df_perf)} performance records...")
        composite_model.fit(df_perf)

    print("Running composite prediction...")
    df_proj = composite_model.predict(df_feat, horizon=1)
    print(f"Predictions generated: {len(df_proj)} rows.")

    # Contract verification
    print("Verifying ProjectionContract...")
    assert_projection_contract(df_proj)
    print("Assertion passed: ProjectionContract satisfied!")

    components = [c for c in df_proj.columns if c.startswith("xp_")]
    print(f"Component columns present ({len(components)}): {components}")
    print("\nSample top 5 projected players:")
    top_players = df_proj.sort_values("projected_points", ascending=False).head(5)
    cols_to_show = ["player_id", "projected_points", "projected_minutes"] + [c for c in ["xp_goals", "xp_assists", "xp_clean_sheet"] if c in df_proj.columns]
    print(top_players[cols_to_show].to_string(index=False))

    # Test Oracle Minutes override
    print("\nTesting Oracle Minutes override (external_xmins = 90.0)...")
    df_feat_oracle = df_feat.copy()
    df_feat_oracle["external_xmins"] = 90.0
    df_proj_oracle = composite_model.predict(df_feat_oracle, horizon=1)
    assert_projection_contract(df_proj_oracle)
    print("Oracle minutes override satisfied ProjectionContract successfully!")
    print("\nPROTOTYPE VERIFICATION COMPLETE: ALL CHECKS PASSED.")


if __name__ == "__main__":
    run_prototype_smoke()
