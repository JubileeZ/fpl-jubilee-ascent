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
