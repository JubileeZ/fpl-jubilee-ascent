"""Causality and score reconciliation for the direct FPL score experiment."""

from pathlib import Path
import runpy

import numpy as np
import pandas as pd
import pytest

from backtesting.walkforward import LEDGER_COMPONENTS
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

_PROTOTYPE = (
    Path(__file__).resolve().parents[1]
    / "docs/research/candidate-ideation/prototypes/component_score_head/prototypes.py"
)


@pytest.fixture
def inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[tuple[int, pd.DataFrame]]]:
    base = pd.DataFrame(
        {
            **dict.fromkeys(LEDGER_COMPONENTS, 0.0),
            "player_id": [1, 2, 3, 1],
            "gameweek_id": [5, 5, 5, 6],
            "fixture_id": [50, -1, 50, 60],
            "xp_minutes": [2.0, 0.0, 0.0, 2.0],
            "projected_minutes": [90.0, 0.0, 0.0, 90.0],
            "projected_points": [2.0, 0.0, 0.0, 2.0],
        }
    )
    features = base[["player_id", "gameweek_id", "fixture_id"]].assign(
        position_id=[2, 1, 3, 2]
    )
    features.attrs["issue_gameweek"] = 5
    history = pd.DataFrame(
        {
            "player_id": 1,
            "gameweek_id": list(range(1, 5)),
            "fixture_id": [10, 20, 30, 40],
            "minutes": 90,
            "bps": 18,
            "ict_index": 3.0,
            "total_points": -2,
        }
    )
    design_matrix = runpy.run_path(str(_PROTOTYPE))["design_matrix"]
    bank = [
        (
            gw,
            design_matrix(
                features,
                base.iloc[:1].assign(gameweek_id=gw, fixture_id=gw * 10),
                history.loc[history["gameweek_id"].lt(gw)],
            ),
        )
        for gw in range(1, 5)
    ]

    def champion_forecast(
        _model: DefXgShrinkChallengerModel, _features: pd.DataFrame, _horizon: int
    ) -> pd.DataFrame:
        return base.copy()

    monkeypatch.setattr(DefXgShrinkChallengerModel, "predict", champion_forecast)
    return base, features, history, bank


def test_signed_scores_have_explicit_adjustment_and_keep_component_forecasts(
    inputs: tuple[
        pd.DataFrame, pd.DataFrame, pd.DataFrame, list[tuple[int, pd.DataFrame]]
    ],
) -> None:
    base, features, history, bank = inputs
    model = runpy.run_path(str(_PROTOTYPE))["ComponentScoreHeadModel"]()
    projections, published = model.predict_with_prior_forecasts(
        features, 2, history, bank
    )
    assert projections["projected_points"].tolist() == pytest.approx(
        [-2, 0, 0, -2], abs=0.02
    )
    preserved = [*LEDGER_COMPONENTS, "projected_minutes"]
    pd.testing.assert_frame_equal(projections[preserved], base[preserved])
    assert np.allclose(
        projections[list(LEDGER_COMPONENTS)].sum(axis=1)
        + projections["score_head_adjustment"],
        projections["projected_points"],
    )
    assert published["gameweek_id"].tolist() == [5, 5]
    assert published["fixture_id"].tolist() == [50, 50]
    assert published["projected_bps"].tolist() == [18.0, 0.0]
    assert published["projected_ict"].tolist() == [3.0, 0.0]


def test_unmatched_fixture_label_keeps_champion_until_four_labeled_weeks(
    inputs: tuple[
        pd.DataFrame, pd.DataFrame, pd.DataFrame, list[tuple[int, pd.DataFrame]]
    ],
) -> None:
    base, features, history, bank = inputs
    history.loc[history["gameweek_id"].eq(4), "fixture_id"] = 41
    model = runpy.run_path(str(_PROTOTYPE))["ComponentScoreHeadModel"]()
    projections, _ = model.predict_with_prior_forecasts(features, 2, history, bank)
    pd.testing.assert_frame_equal(projections, base.assign(score_head_adjustment=0.0))


def test_plain_predict_requires_replay_inputs() -> None:
    model = runpy.run_path(str(_PROTOTYPE))["ComponentScoreHeadModel"]()
    with pytest.raises(ValueError, match="historical replay forecast inputs"):
        model.predict(pd.DataFrame(), 1)


@pytest.mark.parametrize("origin, target", [(5, 5), (1, 2)])
def test_rejects_current_issue_or_a_mismatched_forecast_row(
    inputs: tuple[
        pd.DataFrame, pd.DataFrame, pd.DataFrame, list[tuple[int, pd.DataFrame]]
    ],
    origin: int,
    target: int,
) -> None:
    _, features, history, bank = inputs
    invalid_bank = [(origin, bank[0][1].assign(gameweek_id=target))]
    model = runpy.run_path(str(_PROTOTYPE))["ComponentScoreHeadModel"]()
    with pytest.raises(
        ValueError, match="Score head training origins|Training forecasts"
    ):
        model.predict_with_prior_forecasts(features, 2, history, invalid_bank)
