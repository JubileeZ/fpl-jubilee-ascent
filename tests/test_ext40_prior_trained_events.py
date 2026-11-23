"""Synthetic tests for the EXT-40 research model's issue-time interface."""

from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from scipy.stats import poisson

TOPIC = Path(__file__).resolve().parents[1] / "docs/research/candidate-ideation"
sys.path.insert(0, str(TOPIC))

from prototypes.ext_40.prototypes import (  # noqa: E402
    KEYS,
    REQUIRED_COMPONENTS,
    fit_count_head,
    poisson_categories,
    score_fixture_component,
    state_distribution,
)
from prototypes.ext_40.panel import IssueContext, eligible_issue_history  # noqa: E402


def test_zero_current_labels_keep_prior_and_change_gw1_estimates() -> None:
    predictors = pd.DataFrame(
        {
            "rate": np.repeat(0.2, 80),
            "form": np.tile([-0.7, 0.5], 40),
            "position_id": np.tile([2, 3, 4, 3], 20),
            "is_home": np.tile([False, True, True, False], 20),
            "opponent_form": np.zeros(80),
            "minutes": np.repeat(90, 80),
            "gameweek_id": np.repeat(np.arange(1, 9), 10),
        }
    )
    targets = np.eye(4)[np.tile([0, 1, 0, 3], 20)]
    prior = fit_count_head(predictors, targets, penalty=0.03, dynamic=True)
    refit = fit_count_head(
        predictors.iloc[:0], targets[:0], penalty=0.03, dynamic=True, prior=prior
    )
    issued = predictors.iloc[:4].assign(
        p_start=0.6, p_sub_in=0.3, p_dnp=0.1, xmins_if_start=80, xmins_if_sub_in=20
    )

    np.testing.assert_array_equal(refit, prior)
    probabilities, mean = state_distribution(issued, prior, dynamic=True)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1)
    assert np.abs(mean - (0.6 * 80 + 0.3 * 20) / 90 * 0.2).max() > 0.05


def test_poisson_tail_includes_each_four_plus_event_and_dnp_is_exact() -> None:
    mu = np.array([0.0, 0.01, 2.0, 7.0])
    probabilities, conditional_counts = poisson_categories(mu)
    np.testing.assert_allclose(probabilities[:, 3], poisson.sf(2, mu))
    np.testing.assert_allclose((probabilities * conditional_counts).sum(axis=1), mu)
    assert conditional_counts[-1, 3] > 7
    np.testing.assert_array_equal(probabilities[0], [1, 0, 0, 0])


@pytest.mark.parametrize(
    ("gameweek", "kickoff", "error"),
    [
        (2, "2025-08-16T14:00:00Z", "target or future Gameweek"),
        (3, "2025-08-16T14:00:00Z", "target or future Gameweek"),
        (1, "2025-08-22T17:30:00Z", "starts after issue deadline"),
    ],
)
def test_issue_cutoff_rejects_unavailable_label(
    gameweek: int, kickoff: str, error: str,
) -> None:
    cutoff = datetime(2025, 8, 22, 17, 30, tzinfo=timezone.utc)
    history = pd.DataFrame({"gameweek_id": [1], "kickoff_time": pd.to_datetime(["2025-08-16T14:00:00Z"])})
    context = IssueContext("2025-26", 2, cutoff, "source", "receipt", pd.DataFrame(), history, {})
    pd.testing.assert_frame_equal(eligible_issue_history(context), history)
    history.loc[0, ["gameweek_id", "kickoff_time"]] = [gameweek, pd.Timestamp(kickoff)]
    with pytest.raises(ValueError, match=error):
        eligible_issue_history(context)


@pytest.mark.parametrize("component", ["goals", "assists"])
def test_replacement_isolates_ledger_across_doubles_blanks_and_hard_dnp(component: str) -> None:
    fixture_ids = [11, 12, -1, 13, 14]
    champion = pd.DataFrame(
        {
            "player_id": [1, 1, 2, 3, 4], "gameweek_id": [1] * 5, "fixture_id": fixture_ids,
            "p_start": [0.8, 0.5, 0.0, 0.0, 0.9], "p_sub_in": [0.1, 0.3, 0.0, 0.0, 0.0],
            "p_dnp": [0.1, 0.2, 1.0, 1.0, 0.1], "xmins_if_start": [85.0, 91.0, 0.0, 80.0, 90.0],
            "xmins_if_sub_in": [25.0, 25.0, 0.0, 15.0, 0.0], "projected_minutes": [70.5, 53.0, 0.0, 0.0, 81.0],
            **dict.fromkeys(REQUIRED_COMPONENTS, 0.0),
        },
    )
    champion["xp_goals"] = [1.2, 1.0, 0.0, 0.0, 0.01]
    champion["xp_assists"] = [0.5, 0.3, 0.0, 0.0, 0.01]
    champion["xp_minutes"] = [1.7, 1.3, 0.0, 0.0, 1.8]
    champion["projected_points"] = champion[list(REQUIRED_COMPONENTS)].sum(axis=1)
    predictors = champion[KEYS].assign(
        position_id=[3, 3, 3, 3, 1], rate=[0.3, 0.7, 0.3, 0.3, 0.4], form=0.0,
        is_home=True, opponent_form=0.0, support="linked_source",
    ).iloc[::-1]

    result, counts = score_fixture_component(
        champion, predictors, component, np.zeros((6, 3)), "2025-26", dynamic=False,
    )
    target = f"xp_{component}"
    unchanged = champion.columns.difference([target, "projected_points"])
    pd.testing.assert_frame_equal(result[unchanged], champion[unchanged], check_exact=True)
    assert result[target].iloc[:2].ne(champion[target].iloc[:2]).all()
    pd.testing.assert_series_equal(result[target].iloc[2:], champion[target].iloc[2:])
    np.testing.assert_allclose(result["projected_points"], result[list(REQUIRED_COMPONENTS)].sum(axis=1))
    np.testing.assert_array_equal(counts["p_zero"].iloc[2:4], [1.0, 1.0])
    disabled, _ = score_fixture_component(champion, predictors, None, None, "2025-26", dynamic=False)
    pd.testing.assert_frame_equal(disabled, champion, check_exact=True)
