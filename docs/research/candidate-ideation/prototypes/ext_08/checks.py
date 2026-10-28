from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel
from tests.test_ml_panel_leakage import _create_synthetic_features, _create_synthetic_history

spec = importlib.util.spec_from_file_location("prototype", Path(__file__).with_name("prototypes.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

for k_mix in (2.0, 4.0, 8.0, 16.0):
    f0 = module.joint_factors(0.2, 0.1, 3.0, 0.20, 0.18, k_mix, 1.0)
    f1 = module.joint_factors(0.2, 0.10001, 3.0, 0.20, 0.18, k_mix, 1.0)
    assert abs(f1[0] - f0[0]) > 1e-9, (k_mix, f0, f1)
    assert module.joint_factors(0.2, 0.1, 3.0, 0.20, 0.18, k_mix, 0.0) == (1.0, 1.0)
    identity = module.joint_factors(0.2, 0.1, 3.0, 0.20, 0.18, 12.0 * 0.38, 1.0)
    np.testing.assert_allclose(identity, (1.0, 1.0), atol=1e-15)
print("PASS nonzero cross-signal derivative; independent-collapse identity; alpha-zero identity")

history = _create_synthetic_history(n_gws=19, n_players=300)
features = _create_synthetic_features(target_gw=20, n_players=300)
model = module.JointAllocationModel()
model.fit(history)
cache = model._factor_cache(features)
assert cache and any(pair != (1.0, 1.0) for pair in cache.values())
for row in features.itertuples():
    if row.position_id in (1, 2):
        assert (row.player_id, row.fixture_id) not in cache
mutated = history.copy()
mutated.loc[mutated.gameweek_id > 1, "price"] = 999.0
model.fit(mutated)
assert model._factor_cache(features) == cache
model.fit(history)
with_future = pd.concat([history, history.assign(gameweek_id=20, fixture_id=99999, expected_assists=99999.0)])
model.fit(with_future)
assert model._factor_cache(features) != cache
model.fit(history)
print("PASS active current-only reliability, MID/FWD restriction, first-observed-price invariance")

for gw in (1, 10, 19):
    earlier = history[history.gameweek_id < gw]
    frame = _create_synthetic_features(target_gw=gw, n_players=10)
    champion = AdaptiveCausalChallengerModel()
    candidate = module.JointAllocationModel()
    champion.fit(earlier)
    candidate.fit(earlier)
    pd.testing.assert_frame_equal(champion.predict(frame, 1), candidate.predict(frame, 1))
print("PASS exact Champion frame parity at GW1/10/19")

for cls in module.PROTOTYPES.values():
    candidate = cls()
    candidate.fit(history)
    out = candidate.predict(features, 1)
    components = [column for column in out if column.startswith("xp_")]
    np.testing.assert_allclose(out.projected_points, out[components].sum(axis=1), atol=1e-9)
    assert np.isfinite(out.projected_points).all()
print("PASS all variants finite late predictions and component reconciliation")
