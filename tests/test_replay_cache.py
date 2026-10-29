from dataclasses import replace
import json

import pandas as pd
import pytest

from backtesting.forecast_store import _canonical_json_bytes, _sha256_hex
from backtesting.data_admission import AdmittedInput
from backtesting.replay_cache import AdmissionContext, checkpoint_transition, problem_id, problem_material
from backtesting.replay_state import Decision, Lineup, Outcome, OutcomeBatch, Player, initial_state, state_hash
from models.scoring_matrix import Position


def test_problem_identity_and_verified_checkpoint(tmp_path, monkeypatch) -> None:
    positions = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    players = tuple(Player(i + 1, position, i // 3 + 1, 50, 50) for i, position in enumerate(positions))
    state = initial_state("2024-25", players)
    material = {"issue": {"gw": 1, "season": "2024-25", "native_rules": "native-2024-25-v1"}}
    forecast_id = _sha256_hex(_canonical_json_bytes(material))
    folder = tmp_path / "forecasts" / forecast_id
    folder.mkdir(parents=True)
    table = pd.DataFrame({"player_id": range(1, 16)}).to_csv(index=False).encode()
    (folder / "material.json").write_bytes(_canonical_json_bytes(material))
    (folder / "forecast.csv").write_bytes(table)
    (folder / "manifest.json").write_bytes(_canonical_json_bytes({"version": 1, "forecast_id": forecast_id, "material_sha256": forecast_id, "forecast_sha256": _sha256_hex(table), "rows": 15}))
    solver = {"version": "1", "binary_sha256": "a" * 64, "options": {"gap": 0}}
    context = AdmissionContext(AdmittedInput("2024-25", 1, "synthetic"), {}, {}, "synthetic")
    monkeypatch.setattr("backtesting.replay_cache.load_forecast_verified", lambda *args: (pd.DataFrame({"player_id": range(1, 16)}), material))
    contexts: dict[str, AdmissionContext] = {forecast_id: context}
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
    attempts = list((tmp_path / "checkpoints" / "attempts").iterdir())
    assert len(attempts) == 3
    assert sum((att / "complete.json").exists() for att in attempts) == 2
    assert sum((att / "failed.json").exists() for att in attempts) == 1


def test_multigw_lineage_and_resume(tmp_path, monkeypatch) -> None:
    positions = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    players = tuple(Player(i + 1, position, (i % 5) + 1, 50, 50) for i, position in enumerate(positions))
    state_gw1 = initial_state("2024-25", players)

    # Setup forecast for GW1
    mat_gw1 = {"issue": {"gw": 1, "season": "2024-25", "native_rules": "native-2024-25-v1"}}
    fc_id_gw1 = _sha256_hex(_canonical_json_bytes(mat_gw1))
    folder1 = tmp_path / "forecasts" / fc_id_gw1
    folder1.mkdir(parents=True)
    table = pd.DataFrame({"player_id": range(1, 16)}).to_csv(index=False).encode()
    (folder1 / "material.json").write_bytes(_canonical_json_bytes(mat_gw1))
    (folder1 / "forecast.csv").write_bytes(table)
    (folder1 / "manifest.json").write_bytes(_canonical_json_bytes({"version": 1, "forecast_id": fc_id_gw1, "material_sha256": fc_id_gw1, "forecast_sha256": _sha256_hex(table), "rows": 15}))

    # Setup forecast for GW2
    mat_gw2 = {"issue": {"gw": 2, "season": "2024-25", "native_rules": "native-2024-25-v1"}}
    fc_id_gw2 = _sha256_hex(_canonical_json_bytes(mat_gw2))
    folder2 = tmp_path / "forecasts" / fc_id_gw2
    folder2.mkdir(parents=True)
    (folder2 / "material.json").write_bytes(_canonical_json_bytes(mat_gw2))
    (folder2 / "forecast.csv").write_bytes(table)
    (folder2 / "manifest.json").write_bytes(_canonical_json_bytes({"version": 1, "forecast_id": fc_id_gw2, "material_sha256": fc_id_gw2, "forecast_sha256": _sha256_hex(table), "rows": 15}))

    ctx1 = AdmissionContext(AdmittedInput("2024-25", 1, "synthetic"), {}, {}, "synthetic")
    ctx2 = AdmissionContext(AdmittedInput("2024-25", 2, "synthetic"), {}, {}, "synthetic")
    contexts: dict[str, AdmissionContext] = {fc_id_gw1: ctx1, fc_id_gw2: ctx2}

    def mock_load(store, fid, *args):
        m = mat_gw1 if fid == fc_id_gw1 else mat_gw2
        return pd.DataFrame({"player_id": range(1, 16)}), m

    monkeypatch.setattr("backtesting.replay_cache.load_forecast_verified", mock_load)

    solver = {"version": "1", "binary_sha256": "a" * 64, "options": {"gap": 0}}
    problem_gw1 = problem_material(tmp_path, fc_id_gw1, ctx1, state_gw1, {"id": "anchor"}, {"chips": []}, {"name": "strategic"}, solver, {"gap": 0})
    lineup = Lineup((1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15), (2, 6, 7, 12), 8, 9)
    decision_gw1 = Decision((), lineup, state_hash(state_gw1), 1)
    outcomes_gw1 = OutcomeBatch("2024-25", 1, "synthetic", tuple((p.player_id, Outcome(2, 90, True)) for p in players))

    # GW1 checkpoint
    ckpt_gw1, res_gw1, hit1 = checkpoint_transition(tmp_path / "checkpoints", tmp_path, contexts, problem_gw1, state_gw1, decision_gw1, outcomes_gw1, None)
    assert not hit1 and res_gw1.state.deadline == 2

    # GW2 state from GW1 result
    state_gw2 = res_gw1.state
    problem_gw2 = problem_material(tmp_path, fc_id_gw2, ctx2, state_gw2, {"id": "anchor"}, {"chips": []}, {"name": "strategic"}, solver, {"gap": 0})
    decision_gw2 = Decision((), lineup, state_hash(state_gw2), 2)
    outcomes_gw2 = OutcomeBatch("2024-25", 2, "synthetic", tuple((p.player_id, Outcome(3, 90, True)) for p in players))

    # Missing parent checkpoint for GW2 must fail
    with pytest.raises(ValueError, match="Missing parent checkpoint"):
        checkpoint_transition(tmp_path / "checkpoints", tmp_path, contexts, problem_gw2, state_gw2, decision_gw2, outcomes_gw2, None)

    # GW2 checkpoint with valid parent
    ckpt_gw2, res_gw2, hit2 = checkpoint_transition(tmp_path / "checkpoints", tmp_path, contexts, problem_gw2, state_gw2, decision_gw2, outcomes_gw2, ckpt_gw1)
    assert not hit2 and res_gw2.state.deadline == 3

    # Resuming GW2 checkpoint returns hit=True
    assert checkpoint_transition(tmp_path / "checkpoints", tmp_path, contexts, problem_gw2, state_gw2, decision_gw2, outcomes_gw2, ckpt_gw1)[2] is True

    # Altering parent_hash fails validation
    state_bad_parent = replace(state_gw2, parent_hash="0" * 64)
    problem_bad_parent = problem_material(tmp_path, fc_id_gw2, ctx2, state_bad_parent, {"id": "anchor"}, {"chips": []}, {"name": "strategic"}, solver, {"gap": 0})
    decision_bad_parent = Decision((), lineup, state_hash(state_bad_parent), 2)
    with pytest.raises(ValueError, match="Checkpoint parent state mismatch"):
        checkpoint_transition(tmp_path / "checkpoints", tmp_path, contexts, problem_bad_parent, state_bad_parent, decision_bad_parent, outcomes_gw2, ckpt_gw1)


def test_real_offline_synthetic_integration(tmp_path) -> None:
    from test_data_admission import request, catalog, rehash, authorize, RETAINED
    from backtesting.data_admission import require_input
    from features.builder import EVENT_RATE_MAP
    from test_forecast_inputs import retain
    from backtesting.forecast_store import generate_forecast
    from backtesting.forecast_solver_export import export_solver_csv

    value = request()
    origin = value["origins"][0]
    origin["season"] = "2024-25"
    origin["native_rules"] = "native-2024-25-v1"
    origin["universe"] = list(range(1, 16))
    positions = [1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4]
    pos_str: tuple[Position, ...] = ("GK", "GK", "D", "D", "D", "D", "D", "M", "M", "M", "M", "M", "F", "F", "F")
    origin["players"] = [
        {"id": i + 1, "club": (i % 5) + 1, "position": pos, "price": 50, "eligible": True, "ownership": 10.0, "availability": "available"}
        for i, pos in enumerate(positions)
    ]
    origin["fixtures"] = [{"id": 10 + gw, "gw": gw, "home_club": 1, "away_club": 2} for gw in range(1, 7)]
    origin["fixture_events"] = [{"fixture": 10 + gw, "gw": gw, "status": "final", "home_club": 1, "away_club": 2, "changed_at": None, "finalized_at": "2025-01-02T12:00:00Z"} for gw in range(1, 7)]
    origin["schedule"] = [
        {"player": p["id"], "gw": gw, "status": "fixture" if p["club"] in (1, 2) else "blank", "fixture": (10 + gw) if p["club"] in (1, 2) else None, "price": 50, "ownership": 10.0}
        for gw in range(1, 7) for p in origin["players"]
    ]
    origin["outcomes"] = [
        {"player": p["id"], "gw": gw, "fixture": (10 + gw) if p["club"] in (1, 2) else None, "status": "played" if p["club"] in (1, 2) else "blank", "points": 2 if p["club"] in (1, 2) else 0}
        for gw in range(1, 7) for p in origin["players"]
    ]
    origin["target_gws"] = list(range(1, 7))

    entries = catalog(value)
    base = json.loads(entries[value["authority_digest"]])
    base.update({
        "version": 2,
        "season": "2024-25",
        "native_rules": origin["native_rules"],
        "universe": list(range(1, 16)),
        "seed_mapping": {str(i + 1): f"s{i + 1}" for i in range(15)},
        "components": {str(i + 1): ["points"] for i in range(15)},
        "eligible_since": {str(i + 1): 1 for i in range(15)}
    })
    event = {name: 0.0 for name, _ in EVENT_RATE_MAP}
    seed_rows = [{**event, "player_id": i + 1, "fixture_id": 99, "gameweek_id": 38, "kickoff_time": "2024-05-19T00:00:00Z", "minutes": 90, "total_points": 3, "starts": 1, "was_home": True, "opponent_club_id": 3} for i in range(15)]
    source = {
        "version": 2,
        "url": "synthetic://" + "a" * 40,
        "revision": "a" * 40,
        "parser_version": "1",
        "seed_season": "2023-24",
        "seed_registry_complete": True,
        "published_at": "2025-01-01T10:00:00Z",
        "captured_at": "2025-01-01T11:00:00Z",
        "timestamp_uncertainty_seconds": 0,
        "seed_mapping": base["seed_mapping"],
        "tables": {
            "clubs": [{"id": n, "strength": 1000, "short_name": f"C{n}"} for n in range(1, 6)],
            "player_metadata": [{"id": n, "web_name": f"Player {n}"} for n in range(1, 16)],
            "target_fixtures": [{"id": f["id"], "gameweek_id": f["gw"], "home_club_id": f["home_club"], "away_club_id": f["away_club"], "team_h_difficulty": 3, "team_a_difficulty": 3} for f in origin["fixtures"]],
            "history": [],
            "history_fixtures": [],
            "seed_players": [{"seed_key": f"s{n}", "id": n, "club_id": (n % 5) + 1, "position_id": positions[n - 1], "now_cost": 50} for n in range(1, 16)],
            "seed_history": seed_rows,
            "seed_fixtures": [{"id": 99, "gameweek_id": 38, "home_club_id": 1, "away_club_id": 3, "finished": True, "finalized_at": "2024-05-20T00:00:00Z"}]
        }
    }

    source_digest = retain(entries, source)
    base["training_source_digests"] = [source_digest]
    value["authority_digest"] = retain(entries, base)
    RETAINED[value["authority_digest"]] = entries[value["authority_digest"]]
    for item in origin["sources"]:
        item["parent_manifest"] = value["authority_digest"]

    rehash(value)
    authorize(value)
    for item in origin["sources"]:
        entries[item["blob_sha256"]] = item["bytes"]
    entries.update(RETAINED)

    cap = require_input(value, entries, "2024-25", 1)
    authority = {"version": 2, "mode": "synthetic", "input_digest": cap.input_digest, "season": "2024-25", "gw": 1, "seed_identity": origin["seed_identity"], "source_digest": source_digest}
    auth_digest = retain(entries, authority)

    # 1. Generate real forecast
    forecast_id, frame, hit = generate_forecast(tmp_path, cap, value, entries, auth_digest)
    assert not hit and len(frame) == 90

    # 2. Export solver CSV
    csv_path, csv_manifest = export_solver_csv(tmp_path, forecast_id, cap, value, entries, auth_digest)
    assert csv_manifest["forecast_id"] == forecast_id
    assert csv_path.exists()

    # 3. Create initial state and problem material
    players = tuple(Player(i + 1, pos_str[i], (i % 5) + 1, 50, 50) for i in range(15))
    state = initial_state("2024-25", players)
    context = AdmissionContext(cap, value, entries, auth_digest)
    contexts: dict[str, AdmissionContext] = {forecast_id: context}
    solver = {"version": "1", "binary_sha256": "a" * 64, "options": {"gap": 0}}
    problem = problem_material(tmp_path, forecast_id, context, state, {"id": "anchor"}, {"chips": []}, {"name": "strategic"}, solver, {"gap": 0})

    # 4. Checkpoint transition without mocks
    lineup = Lineup((1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15), (2, 6, 7, 12), 8, 9)
    decision = Decision((), lineup, state_hash(state), 1)
    outcomes = OutcomeBatch("2024-25", 1, "synthetic", tuple((p.player_id, Outcome(2, 90, True)) for p in players))
    checkpoint, result, hit = checkpoint_transition(tmp_path / "checkpoints", tmp_path, contexts, problem, state, decision, outcomes, None)

    assert not hit
    assert result.state.deadline == 2
    assert result.state.parent_hash == state_hash(state)
