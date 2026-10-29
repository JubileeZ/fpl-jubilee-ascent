from dataclasses import replace

import pandas as pd
import pytest

from backtesting.forecast_store import _bytes, _hash
from backtesting.data_admission import AdmittedInput
from backtesting.replay_cache import checkpoint_transition, problem_id, problem_material
from backtesting.replay_state import Decision, Lineup, Outcome, OutcomeBatch, Player, initial_state, state_hash


def test_problem_identity_and_verified_checkpoint(tmp_path, monkeypatch) -> None:
    positions = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    players = tuple(Player(i + 1, position, i // 3 + 1, 50, 50) for i, position in enumerate(positions))
    state = initial_state("2024-25", players)
    material = {"issue": {"gw": 1, "season": "2024-25", "native_rules": "native-2024-25-v1"}}
    forecast_id = _hash(_bytes(material))
    folder = tmp_path / "forecasts" / forecast_id
    folder.mkdir(parents=True)
    table = pd.DataFrame({"player_id": range(1, 16)}).to_csv(index=False).encode()
    (folder / "material.json").write_bytes(_bytes(material))
    (folder / "forecast.csv").write_bytes(table)
    (folder / "manifest.json").write_bytes(_bytes({"version": 1, "forecast_id": forecast_id, "material_sha256": forecast_id, "forecast_sha256": _hash(table), "rows": 15}))
    solver = {"version": "1", "binary_sha256": "a" * 64, "options": {"gap": 0}}
    context = (AdmittedInput("2024-25", 1, "synthetic"), {}, {}, "synthetic")
    monkeypatch.setattr("backtesting.replay_cache.load_forecast_verified", lambda *args: (pd.DataFrame({"player_id": range(1, 16)}), material))
    contexts = {forecast_id: context}
    problem = problem_material(tmp_path, forecast_id, context, state, {"id": "anchor"}, {"chips": []}, {"name": "strategic"}, solver, {"gap": 0})
    changed = problem_material(tmp_path, forecast_id, context, replace(state, bank=state.bank - 1), {"id": "anchor"}, {"chips": []}, {"name": "strategic"}, solver, {"gap": 0})
    assert problem_id(problem) != problem_id(changed)
    lineup = Lineup((1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15), (2, 6, 7, 12), 8, 9)
    decision = Decision((), lineup, state_hash(state), 1)
    outcomes = OutcomeBatch("2024-25", 1, "synthetic", tuple((p.player_id, Outcome(2, 90, True)) for p in players))
    checkpoint, result, hit = checkpoint_transition(tmp_path / "checkpoints", tmp_path, contexts, problem, state, decision, outcomes, None)
    assert not hit and result.state.parent_hash == state_hash(state)
    assert checkpoint_transition(tmp_path / "checkpoints", tmp_path, contexts, problem, state, decision, outcomes, None)[2]
    (tmp_path / "checkpoints" / f"{checkpoint}.json").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash"):
        checkpoint_transition(tmp_path / "checkpoints", tmp_path, contexts, problem, state, decision, outcomes, None)
