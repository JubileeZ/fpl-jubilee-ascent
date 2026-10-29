import copy
import json

import pytest

from backtesting.data_admission import require_input
from backtesting.forecast_adapter import predict_synthetic_issue
from backtesting.forecast_store import generate_forecast, load_forecast_verified
from backtesting.forecast_solver_export import export_solver_csv
from features.builder import EVENT_RATE_MAP
from test_data_admission import catalog, request
from test_forecast_inputs import retain


def test_admitted_issue_uses_real_model_once(tmp_path) -> None:
    value = request()
    entries = catalog(value)
    origin = value["origins"][0]
    origin["season"] = "2024-25"
    origin["native_rules"] = "native-2024-25-v1"
    base = json.loads(entries[value["authority_digest"]])
    base.update({"version": 2, "season": "2024-25", "native_rules": origin["native_rules"]})
    event = {name: 0.0 for name, _ in EVENT_RATE_MAP}
    seed_row = {**event, "player_id": 1, "fixture_id": 99, "gameweek_id": 38, "kickoff_time": "2024-05-19T00:00:00Z", "minutes": 90, "total_points": 3, "starts": 1, "was_home": True, "opponent_club_id": 3}
    source = {"version": 2, "url": "synthetic://" + "a" * 40, "revision": "a" * 40, "parser_version": "1", "seed_season": "2023-24", "seed_registry_complete": True, "published_at": "2025-01-01T10:00:00Z", "captured_at": "2025-01-01T11:00:00Z", "timestamp_uncertainty_seconds": 0, "seed_mapping": base["seed_mapping"], "tables": {"clubs": [{"id": n, "strength": 1000, "short_name": f"C{n}"} for n in (1, 2, 3)], "player_metadata": [{"id": n, "web_name": f"Player {n}"} for n in (1, 2)], "target_fixtures": [{"id": f["id"], "gameweek_id": f["gw"], "home_club_id": f["home_club"], "away_club_id": f["away_club"], "team_h_difficulty": 3, "team_a_difficulty": 3} for f in origin["fixtures"]], "history": [], "history_fixtures": [], "seed_players": [{"seed_key": f"s{n}", "id": n, "club_id": n, "position_id": n, "now_cost": 50} for n in (1, 2)], "seed_history": [seed_row], "seed_fixtures": [{"id": 99, "gameweek_id": 38, "home_club_id": 1, "away_club_id": 3, "finished": True, "finalized_at": "2024-05-20T00:00:00Z"}]}}
    source_digest = retain(entries, source)
    base["training_source_digests"] = [source_digest]
    value["authority_digest"] = retain(entries, base)
    for item in origin["sources"]:
        item["parent_manifest"] = value["authority_digest"]
    cap = require_input(value, entries, "2024-25", 1)
    authority = {"version": 2, "mode": "synthetic", "input_digest": cap.input_digest, "season": "2024-25", "gw": 1, "seed_identity": origin["seed_identity"], "source_digest": source_digest}
    predictions, meta = predict_synthetic_issue(cap, value, entries, retain(entries, authority), tmp_path)
    assert set(predictions.gameweek_id) == set(range(1, 7))
    assert len(predictions) == 12
    assert meta["fit_count"] == meta["predict_count"] == 1
    assert set(predictions.loc[predictions.player_id == 2, "projected_points"]) == {0}
    # Check full grain metadata attached to forecast rows
    for grain_col in ("horizon_lead", "issue_gameweek", "model", "rules_version", "cutoff", "training_cutoff"):
        assert grain_col in predictions.columns
    assert (predictions["cutoff"] == origin["deadline"]).all()
    assert (predictions["training_cutoff"] == source["captured_at"]).all()
    changed = copy.deepcopy(value)
    changed["origins"][0]["outcomes"][0]["points"] = 99
    repeated, _ = predict_synthetic_issue(cap, changed, entries, retain(entries, authority), tmp_path)
    assert predictions.equals(repeated)
    authority_digest = retain(entries, authority)
    first_id, first, hit = generate_forecast(tmp_path, cap, value, entries, authority_digest)
    assert hit is False
    second_id, second, hit = generate_forecast(tmp_path, cap, changed, entries, authority_digest)
    assert hit is True and first_id == second_id and first.equals(second)
    path, csv_manifest = export_solver_csv(tmp_path, first_id, cap, value, entries, authority_digest)
    assert csv_manifest["forecast_id"] == first_id
    assert "6_Pts" in path.read_text().splitlines()[0]
    broken_catalog = dict(entries)
    del broken_catalog[source_digest]
    with pytest.raises(ValueError):
        load_forecast_verified(tmp_path, first_id, cap, value, broken_catalog, authority_digest)
    table = tmp_path / "forecasts" / first_id / "forecast.csv"
    table.write_bytes(table.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="corruption"):
        generate_forecast(tmp_path, cap, value, entries, authority_digest)
    attempts = list((tmp_path / "attempts").iterdir())
    assert len(attempts) == 3 and all((attempt / "started.json").exists() for attempt in attempts)
    assert sum((attempt / "failed.json").exists() for attempt in attempts) == 1


def test_forecast_id_mutation_sensitivity(tmp_path) -> None:
    value = request()
    entries = catalog(value)
    origin = value["origins"][0]
    origin["season"] = "2024-25"
    origin["native_rules"] = "native-2024-25-v1"
    base = json.loads(entries[value["authority_digest"]])
    base.update({"version": 2, "season": "2024-25", "native_rules": origin["native_rules"]})
    event = {name: 0.0 for name, _ in EVENT_RATE_MAP}
    seed_row = {**event, "player_id": 1, "fixture_id": 99, "gameweek_id": 38, "kickoff_time": "2024-05-19T00:00:00Z", "minutes": 90, "total_points": 3, "starts": 1, "was_home": True, "opponent_club_id": 3}
    source = {"version": 2, "url": "synthetic://" + "a" * 40, "revision": "a" * 40, "parser_version": "1", "seed_season": "2023-24", "seed_registry_complete": True, "published_at": "2025-01-01T10:00:00Z", "captured_at": "2025-01-01T11:00:00Z", "timestamp_uncertainty_seconds": 0, "seed_mapping": base["seed_mapping"], "tables": {"clubs": [{"id": n, "strength": 1000, "short_name": f"C{n}"} for n in (1, 2, 3)], "player_metadata": [{"id": n, "web_name": f"Player {n}"} for n in (1, 2)], "target_fixtures": [{"id": f["id"], "gameweek_id": f["gw"], "home_club_id": f["home_club"], "away_club_id": f["away_club"], "team_h_difficulty": 3, "team_a_difficulty": 3} for f in origin["fixtures"]], "history": [], "history_fixtures": [], "seed_players": [{"seed_key": f"s{n}", "id": n, "club_id": n, "position_id": n, "now_cost": 50} for n in (1, 2)], "seed_history": [seed_row], "seed_fixtures": [{"id": 99, "gameweek_id": 38, "home_club_id": 1, "away_club_id": 3, "finished": True, "finalized_at": "2024-05-20T00:00:00Z"}]}}
    source_digest = retain(entries, source)
    base["training_source_digests"] = [source_digest]
    value["authority_digest"] = retain(entries, base)
    for item in origin["sources"]:
        item["parent_manifest"] = value["authority_digest"]
    cap = require_input(value, entries, "2024-25", 1)
    authority = {"version": 2, "mode": "synthetic", "input_digest": cap.input_digest, "season": "2024-25", "gw": 1, "seed_identity": origin["seed_identity"], "source_digest": source_digest}
    authority_digest = retain(entries, authority)

    from backtesting.forecast_store import forecast_material, _hash, _bytes
    base_material = forecast_material(cap, value, entries, authority_digest)
    base_forecast_id = _hash(_bytes(base_material))

    # Mutating training source changes forecast_id
    mutated_source = copy.deepcopy(source)
    mutated_source["tables"]["seed_history"][0]["minutes"] = 45
    mut_src_digest = retain(entries, mutated_source)
    base_with_mut = copy.deepcopy(base)
    base_with_mut["training_source_digests"].append(mut_src_digest)
    mut_value = copy.deepcopy(value)
    mut_value["authority_digest"] = retain(entries, base_with_mut)
    for item in mut_value["origins"][0]["sources"]:
        item["parent_manifest"] = mut_value["authority_digest"]
    mut_cap = require_input(mut_value, entries, "2024-25", 1)
    mut_authority = copy.deepcopy(authority)
    mut_authority["input_digest"] = mut_cap.input_digest
    mut_authority["source_digest"] = mut_src_digest
    mut_auth_digest = retain(entries, mut_authority)
    mut_material = forecast_material(mut_cap, mut_value, entries, mut_auth_digest)
    assert _hash(_bytes(mut_material)) != base_forecast_id

    # Mutating code changes forecast_id
    code_mutated = copy.deepcopy(base_material)
    code_mutated["code"]["pyproject.toml"] = "ff" * 32
    assert _hash(_bytes(code_mutated)) != base_forecast_id

    # Mutating parameters changes forecast_id
    param_mutated = copy.deepcopy(base_material)
    param_mutated["model_parameters"]["k"] = 100
    assert _hash(_bytes(param_mutated)) != base_forecast_id


def test_cached_forecast_component_reconciliation_failure(tmp_path) -> None:
    value = request()
    entries = catalog(value)
    origin = value["origins"][0]
    origin["season"] = "2024-25"
    origin["native_rules"] = "native-2024-25-v1"
    base = json.loads(entries[value["authority_digest"]])
    base.update({"version": 2, "season": "2024-25", "native_rules": origin["native_rules"]})
    event = {name: 0.0 for name, _ in EVENT_RATE_MAP}
    seed_row = {**event, "player_id": 1, "fixture_id": 99, "gameweek_id": 38, "kickoff_time": "2024-05-19T00:00:00Z", "minutes": 90, "total_points": 3, "starts": 1, "was_home": True, "opponent_club_id": 3}
    source = {"version": 2, "url": "synthetic://" + "a" * 40, "revision": "a" * 40, "parser_version": "1", "seed_season": "2023-24", "seed_registry_complete": True, "published_at": "2025-01-01T10:00:00Z", "captured_at": "2025-01-01T11:00:00Z", "timestamp_uncertainty_seconds": 0, "seed_mapping": base["seed_mapping"], "tables": {"clubs": [{"id": n, "strength": 1000, "short_name": f"C{n}"} for n in (1, 2, 3)], "player_metadata": [{"id": n, "web_name": f"Player {n}"} for n in (1, 2)], "target_fixtures": [{"id": f["id"], "gameweek_id": f["gw"], "home_club_id": f["home_club"], "away_club_id": f["away_club"], "team_h_difficulty": 3, "team_a_difficulty": 3} for f in origin["fixtures"]], "history": [], "history_fixtures": [], "seed_players": [{"seed_key": f"s{n}", "id": n, "club_id": n, "position_id": n, "now_cost": 50} for n in (1, 2)], "seed_history": [seed_row], "seed_fixtures": [{"id": 99, "gameweek_id": 38, "home_club_id": 1, "away_club_id": 3, "finished": True, "finalized_at": "2024-05-20T00:00:00Z"}]}}
    source_digest = retain(entries, source)
    base["training_source_digests"] = [source_digest]
    value["authority_digest"] = retain(entries, base)
    for item in origin["sources"]:
        item["parent_manifest"] = value["authority_digest"]
    cap = require_input(value, entries, "2024-25", 1)
    authority = {"version": 2, "mode": "synthetic", "input_digest": cap.input_digest, "season": "2024-25", "gw": 1, "seed_identity": origin["seed_identity"], "source_digest": source_digest}
    authority_digest = retain(entries, authority)

    forecast_id, frame, hit = generate_forecast(tmp_path, cap, value, entries, authority_digest)
    assert hit is False

    # Corrupt a component in forecast.csv and update manifest forecast_sha256 so checksum matches
    table_path = tmp_path / "forecasts" / forecast_id / "forecast.csv"
    manifest_path = tmp_path / "forecasts" / forecast_id / "manifest.json"
    import pandas as pd
    df = pd.read_csv(table_path)
    # Corrupt component reconciliation: change xp_goals without changing projected_points
    df.loc[0, "xp_goals"] = df.loc[0, "xp_goals"] + 5.0
    new_csv = df.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode()
    table_path.write_bytes(new_csv)

    from backtesting.forecast_store import _hash
    manifest = json.loads(manifest_path.read_bytes())
    manifest["forecast_sha256"] = _hash(new_csv)
    manifest_path.write_bytes(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode())

    # Loading from cache must detect component reconciliation failure
    with pytest.raises(ValueError, match="reconciliation"):
        load_forecast_verified(tmp_path, forecast_id, cap, value, entries, authority_digest)

    with pytest.raises(ValueError, match="reconciliation"):
        generate_forecast(tmp_path, cap, value, entries, authority_digest)


    # Corrupt coverage report
    rep_path = tmp_path / "forecasts" / forecast_id / "coverage_report.json"
    rep_orig = rep_path.read_bytes()
    rep_path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Coverage report"):
        load_forecast_verified(tmp_path, forecast_id, cap, value, entries, authority_digest)
    rep_path.write_bytes(rep_orig)

    # Corrupt generator log
    log_path = tmp_path / "forecasts" / forecast_id / "generator_log.json"
    log_orig = log_path.read_bytes()
    log_path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Generator log"):
        load_forecast_verified(tmp_path, forecast_id, cap, value, entries, authority_digest)
    log_path.write_bytes(log_orig)


def test_pad_solver_csv_prohibited_in_evaluation(tmp_path) -> None:
    from projections.exporter import pad_solver_csv_horizon
    fake_csv = tmp_path / "projections.csv"
    fake_csv.write_text("ID,Name,1_Pts\n1,Player,5.0\n")
    with pytest.raises(ValueError, match="prohibited in backtesting and promotion evidence paths"):
        pad_solver_csv_horizon(fake_csv, 1, 6, forbid_padding=True)


def test_solver_csv_columns_and_contract(tmp_path) -> None:
    value = request()
    entries = catalog(value)
    origin = value["origins"][0]
    origin["season"] = "2024-25"
    origin["native_rules"] = "native-2024-25-v1"
    base = json.loads(entries[value["authority_digest"]])
    base.update({"version": 2, "season": "2024-25", "native_rules": origin["native_rules"]})
    event = {name: 0.0 for name, _ in EVENT_RATE_MAP}
    seed_row = {**event, "player_id": 1, "fixture_id": 99, "gameweek_id": 38, "kickoff_time": "2024-05-19T00:00:00Z", "minutes": 90, "total_points": 3, "starts": 1, "was_home": True, "opponent_club_id": 3}
    source = {"version": 2, "url": "synthetic://" + "a" * 40, "revision": "a" * 40, "parser_version": "1", "seed_season": "2023-24", "seed_registry_complete": True, "published_at": "2025-01-01T10:00:00Z", "captured_at": "2025-01-01T11:00:00Z", "timestamp_uncertainty_seconds": 0, "seed_mapping": base["seed_mapping"], "tables": {"clubs": [{"id": n, "strength": 1000, "short_name": f"C{n}"} for n in (1, 2, 3)], "player_metadata": [{"id": n, "web_name": f"Player {n}"} for n in (1, 2)], "target_fixtures": [{"id": f["id"], "gameweek_id": f["gw"], "home_club_id": f["home_club"], "away_club_id": f["away_club"], "team_h_difficulty": 3, "team_a_difficulty": 3} for f in origin["fixtures"]], "history": [], "history_fixtures": [], "seed_players": [{"seed_key": f"s{n}", "id": n, "club_id": n, "position_id": n, "now_cost": 50} for n in (1, 2)], "seed_history": [seed_row], "seed_fixtures": [{"id": 99, "gameweek_id": 38, "home_club_id": 1, "away_club_id": 3, "finished": True, "finalized_at": "2024-05-20T00:00:00Z"}]}}
    source_digest = retain(entries, source)
    base["training_source_digests"] = [source_digest]
    value["authority_digest"] = retain(entries, base)
    for item in origin["sources"]:
        item["parent_manifest"] = value["authority_digest"]
    cap = require_input(value, entries, "2024-25", 1)
    authority = {"version": 2, "mode": "synthetic", "input_digest": cap.input_digest, "season": "2024-25", "gw": 1, "seed_identity": origin["seed_identity"], "source_digest": source_digest}
    authority_digest = retain(entries, authority)

    forecast_id, _, _ = generate_forecast(tmp_path, cap, value, entries, authority_digest)
    path, manifest = export_solver_csv(tmp_path, forecast_id, cap, value, entries, authority_digest)

    import pandas as pd
    solver_df = pd.read_csv(path)
    expected_cols = ["ID", "Name", "Pos", "Price", "Team"] + [f"{gw}_Pts" for gw in range(1, 7)] + [f"{gw}_xMins" for gw in range(1, 7)]
    assert list(solver_df.columns) == expected_cols
    assert not solver_df.isna().any().any()
    # Check Price conversion: 50 -> 5.0
    assert solver_df.loc[solver_df.ID == 1, "Price"].iloc[0] == 5.0
    # Check Pos conversion: 1 -> G, 2 -> D
    assert solver_df.loc[solver_df.ID == 1, "Pos"].iloc[0] == "G"
    assert solver_df.loc[solver_df.ID == 2, "Pos"].iloc[0] == "D"
