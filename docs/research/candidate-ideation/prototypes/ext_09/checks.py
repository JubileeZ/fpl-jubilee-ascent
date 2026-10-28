from __future__ import annotations

import importlib.util
import runpy
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("ext_09_prototype_checks", Path(__file__).with_name("prototypes.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel
from models.learned_start_challenger import _fit_logistic


def main() -> None:
    rng = np.random.default_rng(9)
    x = rng.normal(size=(400, 13))
    y = rng.binomial(1, 0.6, size=400).astype(float)
    actual = module.fit_binomial(x, y, np.ones(len(y)), 10.0)
    expected = _fit_logistic(x, y, 10.0)
    for left, right in zip(actual, expected):
        np.testing.assert_allclose(left, right, rtol=0.0, atol=1e-12)
    print("PASS F=1 grouped-binomial equals shipped binary solver (atol 1e-12)")

    successes = np.array([1.0, 1.0, 0.0, 2.0])
    trials = np.array([2.0, 1.0, 1.0, 2.0])
    beta, _, _ = module.fit_binomial(np.zeros((4, 1)), successes, trials, 10.0)
    np.testing.assert_allclose(1.0 / (1.0 + np.exp(-beta[0])), successes.sum() / trials.sum(), atol=1e-12)
    print("PASS DGW intercept-only optimum equals total starts / total fixture opportunities")

    hist = pd.DataFrame({
        "player_id": [1, 1, 1, 2, 2, 3, 3], "gameweek_id": [1, 1, 1, 1, 1, 1, 1],
        "fixture_id": [10, 11, 11, 20, np.nan, 30, 30], "starts": [1, 0, 0, 1, 0, 1, 0],
    })
    exposures = module.fixture_exposures(hist)
    assert exposures["player_id"].tolist() == [1]
    assert exposures["fixture_count"].tolist() == [2]
    assert exposures["start_count"].tolist() == [1]
    print("PASS duplicate opportunities counted once; unknown and contradictory observations excluded")

    row = runpy.run_path(str(ROOT / "tests/test_face_value_challenger.py"))["_row"]
    candidate = module.BinomialFixtureExposure()
    champion = AdaptiveCausalChallengerModel()
    candidate.fit(pd.DataFrame())
    champion.fit(pd.DataFrame())
    for gw in range(1, 20):
        features = pd.DataFrame([row(gameweek_id=gw), row(player_id=2, position_id=3, gameweek_id=gw)])
        pd.testing.assert_frame_equal(candidate.predict(features, 1), champion.predict(features, 1), check_exact=True)
    print("PASS GW1-19 exact Champion parity with synthetic contract rows")

    rows: list[dict[str, object]] = []
    for gw in range(1, 25):
        for fixture_round in range(2 if gw in (10, 11, 12) else 1):
            fixture = gw * 2 + fixture_round
            for player in range(1, 51):
                home = player <= 25
                start = int((player + gw + fixture_round) % 5 != 0)
                rows.append({"player_id": player, "fixture_id": fixture, "gameweek_id": gw,
                             "was_home": home, "opponent_club_id": 2 if home else 1,
                             "minutes": 90.0 * start, "starts": start})
    history = pd.DataFrame(rows)
    features = pd.DataFrame({"player_id": range(1, 51), "fixture_id": 100, "gameweek_id": 25,
                             "position_id": [1 + player % 4 for player in range(1, 51)],
                             "club_id": [1 if player <= 25 else 2 for player in range(1, 51)]})
    assert module.corrected_probabilities(history.drop(columns=["fixture_id"]), features) == {}
    print("PASS absent fixture_id column falls back via shipped _HIST_COLUMNS guard")
    changed = module.corrected_probabilities(history, features)
    original = module.learned_start_probabilities(history, features)
    assert len(changed) == 50
    effect = max(abs(changed[key] - original[key]) for key in changed)
    assert effect > 1e-5
    print(f"PASS reachable inherited-anchor correction differs from any-start likelihood, max raw probability delta {effect:.8f}")


if __name__ == "__main__":
    main()
