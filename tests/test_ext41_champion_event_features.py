"""Regression tests for EXT-41's frozen Champion feature inputs."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

TOPIC = Path(__file__).resolve().parents[1] / "docs/research/candidate-ideation"
sys.path.insert(0, str(TOPIC))

from prototypes.ext_40.prototypes import (  # noqa: E402
    KEYS,
    REQUIRED_COMPONENTS,
    fit_count_head,
)
from prototypes.ext_41.prototypes import (  # noqa: E402
    PENALTY,
    ChampionFeatureScale,
    arm_features,
    attach_champion_components,
)


def test_join_uses_original_fixture_not_row_order_or_experimental_output() -> None:
    predictors = pd.DataFrame(
        {"player_id": [1, 1], "gameweek_id": [2, 2], "fixture_id": [25, 27]}
    )
    champion = predictors.assign(**dict.fromkeys(REQUIRED_COMPONENTS, 0.0))
    champion["xp_goals"] = [0.2, 0.5]
    original = champion.copy(deep=True)
    attached = attach_champion_components(predictors, champion.iloc[::-1], exact=True)
    pd.testing.assert_frame_equal(attached[KEYS], predictors)
    assert attached["xp_goals"].to_list() == [0.2, 0.5]
    pd.testing.assert_frame_equal(champion, original)
    with pytest.raises(ValueError, match="Candidate rows"):
        attach_champion_components(attached, champion, exact=True)
    with pytest.raises(ValueError, match="Missing or nonfinite"):
        attach_champion_components(
            predictors, champion.assign(fixture_id=[25, 29]), exact=True
        )


def test_zero_source_scale_feature_can_enter_only_with_later_nonzero_support() -> None:
    source = pd.DataFrame(
        {
            "rate": np.full(24, 0.2),
            "form": np.zeros(24),
            "position_id": np.resize([2, 3, 4], 24),
            "is_home": np.resize([False, True], 24),
            "opponent_form": np.zeros(24),
            "minutes": np.full(24, 90),
            "gameweek_id": np.resize([1, 2, 3, 4], 24),
            **dict.fromkeys(REQUIRED_COMPONENTS, 0.0),
        }
    )
    source["xp_conceded"] = -0.25
    targets = np.eye(4)[np.resize([0, 1, 2, 3], 24)]
    scale = ChampionFeatureScale.fit(source)
    features = arm_features("c", "goals")
    source_design = scale.transform(source)
    np.testing.assert_array_equal(source_design["xp_conceded"], np.zeros(24))
    source_fit = fit_count_head(
        source_design, targets, penalty=PENALTY, dynamic=False, extra_features=features
    )
    defcon_row = 6 + features.index("xp_defcon")
    np.testing.assert_array_equal(source_fit[defcon_row], np.zeros(3))
    gw1_fit = fit_count_head(
        source_design.iloc[:0],
        targets[:0],
        penalty=PENALTY,
        dynamic=False,
        extra_features=features,
        prior=source_fit,
    )
    np.testing.assert_array_equal(gw1_fit, source_fit)

    native = scale.transform(source.assign(xp_defcon=np.resize([0, 1, 0, 2], 24)))
    np.testing.assert_array_equal(
        native["xp_defcon"], np.log1p(np.resize([0, 1, 0, 2], 24))
    )
    np.testing.assert_array_equal(native["xp_conceded"], np.zeros(24))
    updated = fit_count_head(
        native,
        targets,
        penalty=PENALTY,
        dynamic=False,
        extra_features=features,
        prior=source_fit,
    )
    assert np.abs(updated[defcon_row]).max() > 0.01
