import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest

from backtesting.data_admission import require_input
from backtesting.forecast_adapter import predict_synthetic_issue
from backtesting.forecast_store import forecast_material, generate_forecast, load_forecast_verified
from backtesting.forecast_solver_export import export_solver_csv
from features.builder import EVENT_RATE_MAP
from models.selection import ModelSelection, save_model_selection
from test_data_admission import catalog, request
from test_forecast_inputs import retain


def test_admitted_issue_uses_real_model_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    config_path = tmp_path / "model_selection.json"
    champion, provisional = "club_def_prior_challenger", "def_xg_shrink_challenger"
    save_model_selection(ModelSelection(champion, (provisional,), provisional_active=provisional), config_path)
    monkeypatch.setattr("models.selection.DEFAULT_CONFIG_PATH", config_path)
    predictions, meta = predict_synthetic_issue(cap, value, entries, authority_digest, tmp_path)
    assert meta["model"] == champion
    _, override = predict_synthetic_issue(cap, value, entries, authority_digest, tmp_path, model_name=provisional)
    assert override["model"] == provisional
    assert forecast_material(cap, value, entries, authority_digest)["model"] == champion
    assert forecast_material(cap, value, entries, authority_digest, provisional)["model"] == provisional
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
    first_id, first, hit = generate_forecast(tmp_path, cap, value, entries, authority_digest)
    assert hit is False
    assert set(first["model"]) == {champion}
    gen_log = json.loads((tmp_path / "forecasts" / first_id / "generator_log.json").read_bytes())
    assert "runner_identity" in gen_log
    assert "python" in gen_log["runner_identity"] and "platform" in gen_log["runner_identity"]
    second_id, second, hit = generate_forecast(tmp_path, cap, changed, entries, authority_digest)
    assert hit is True and first_id == second_id and first.equals(second)
    save_model_selection(ModelSelection(provisional, ()), config_path)
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
        generate_forecast(tmp_path, cap, value, entries, authority_digest, model_name=champion)
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

    # Material must exclude OS/python specifics and bind portable serving closure
    assert "python" not in base_material and "platform" not in base_material
    assert "serving_model_closure_hash" in base_material
    assert "model_runtime_bindings" in base_material

    # Mutating serving closure changes forecast_id
    code_mutated = copy.deepcopy(base_material)
    code_mutated["serving_model_closure_hash"] = "ff" * 32
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


def test_solver_csv_columns_and_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    rename = os.rename
    calls = 0

    def rename_after_scanner_releases(source_path: Path, destination_path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            error = PermissionError("temporary Windows scanner lock")
            setattr(error, "winerror", 5)
            raise error
        rename(source_path, destination_path)

    monkeypatch.setattr(os, "rename", rename_after_scanner_releases)
    path, manifest = export_solver_csv(tmp_path, forecast_id, cap, value, entries, authority_digest)
    assert calls >= 2

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


def test_empirical_forecast_adapter_casts_strings_validates_finished_and_preserves_matchup_share(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib
    from backtesting.forecast_adapter import predict_issue
    from backtesting.forecast_inputs import verify_training_bundle
    from test_empirical_admission import _build_empirical_bundle

    req, cat, auth_map = _build_empirical_bundle(gws=(1, 2), seed_season="2024-25")
    cap = require_input(req, cat, "2025-26", 2)
    auth_obj = json.loads(cat[auth_map[2]].decode("utf-8"))
    src_obj = json.loads(cat[auth_obj["source_digest"]].decode("utf-8"))

    # 1. History fixtures without finished=True must fail verify_training_bundle
    bad_src = copy.deepcopy(src_obj)
    bad_src["tables"]["history_fixtures"][0].pop("finished", None)
    bad_src_bytes = json.dumps(bad_src, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    bad_src_digest = hashlib.sha256(bad_src_bytes).hexdigest()
    bad_cat = dict(cat)
    bad_cat[bad_src_digest] = bad_src_bytes
    bad_auth = {**auth_obj, "source_digest": bad_src_digest}
    bad_auth_bytes = json.dumps(bad_auth, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    bad_auth_digest = hashlib.sha256(bad_auth_bytes).hexdigest()
    bad_cat[bad_auth_digest] = bad_auth_bytes
    with pytest.raises(ValueError, match="finished"):
        verify_training_bundle(cap, req, bad_cat, bad_auth_digest)

    # 2. String numeric stats cast to float and expected_goals_conceded / Matchup-Share preserved
    str_req = copy.deepcopy(req)
    str_cat = dict(cat)
    hist_rows = json.loads(str_cat["history_gw2"].decode("utf-8"))
    for row in hist_rows:
        row["expected_goals"] = "0.42"
        row["expected_assists"] = "0.19"
        row["expected_goals_conceded"] = f"{0.5 + (row['player_id'] % 5) * 0.4:.2f}"
        row["expected_goal_involvements"] = "0.61"
        row["threat"] = "24.5"
        row["creativity"] = "18.0"
        row["influence"] = "21.0"
        row["ict_index"] = "6.3"
    hist_bytes = json.dumps(hist_rows, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    hist_sha = hashlib.sha256(hist_bytes).hexdigest()
    str_cat["history_gw2"] = hist_bytes
    str_req["origins"][1]["sources"]["history"]["blob_sha256"] = hist_sha
    str_req["origins"][1]["sources"]["history"]["decompressed_sha256"] = hist_sha
    str_cap = require_input(str_req, str_cat, "2025-26", 2)

    str_src = copy.deepcopy(src_obj)
    str_src["tables"]["history"] = hist_rows
    str_src_bytes = json.dumps(str_src, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    str_src_digest = hashlib.sha256(str_src_bytes).hexdigest()
    str_cat[str_src_digest] = str_src_bytes
    str_auth = {**auth_obj, "input_digest": str_cap.input_digest, "source_digest": str_src_digest}
    str_auth_bytes = json.dumps(str_auth, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    str_auth_digest = hashlib.sha256(str_auth_bytes).hexdigest()
    str_cat[str_auth_digest] = str_auth_bytes

    captured: dict[str, Any] = {}
    import features.builder as fb_mod
    real_overlay = fb_mod.apply_matchup_share_overlay

    def spy_overlay(df_feat: Any, df_hist: Any, df_fixtures: Any, **kwargs: Any) -> tuple[Any, bool]:
        captured["hist_columns"] = set(df_hist.columns)
        captured["xgc_dtype"] = str(df_hist["expected_goals_conceded"].dtype) if "expected_goals_conceded" in df_hist.columns else None
        captured["xgc_mean"] = float(df_hist["expected_goals_conceded"].mean()) if "expected_goals_conceded" in df_hist.columns else 0.0
        out_df, applied = real_overlay(df_feat, df_hist, df_fixtures, **kwargs)
        captured["matchup_applied"] = applied
        captured["features"] = out_df
        return out_df, applied

    monkeypatch.setattr(fb_mod, "apply_matchup_share_overlay", spy_overlay)
    preds, _ = predict_issue(str_cap, str_req, str_cat, str_auth_digest, tmp_path / "work", model_name="calibrated_matchup_hybrid")
    assert not preds.empty
    assert "expected_goals_conceded" in captured["hist_columns"]
    assert captured["xgc_dtype"].startswith("float")
    assert captured["xgc_mean"] > 1.0
    assert captured["matchup_applied"] is True
    feat_df = captured["features"]
    assert (feat_df["defence_multiplier"] == 1.0).all()
    assert feat_df["per90_goals_conceded"].nunique() > 1
