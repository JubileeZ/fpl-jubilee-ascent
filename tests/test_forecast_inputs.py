import hashlib
import json
from typing import Any

import pytest

from backtesting.data_admission import require_input
from backtesting.forecast_inputs import verify_training_bundle
from test_data_admission import catalog, request


def retain(entries: dict[str, bytes], value: dict[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    entries[digest] = raw
    return digest


def test_training_closure_rejects_future_history_and_changed_mapping() -> None:
    value = request()
    entries = catalog(value)
    base = json.loads(entries[value["authority_digest"]])
    source = {"version": 2, "url": "synthetic://" + "a" * 40, "revision": "a" * 40, "parser_version": "1", "seed_season": "synthetic-prior", "seed_registry_complete": True, "published_at": "2025-01-01T10:00:00Z", "captured_at": "2025-01-01T11:00:00Z", "timestamp_uncertainty_seconds": 0, "tables": {"clubs": [], "player_metadata": [], "target_fixtures": [], "history": [], "history_fixtures": [], "seed_players": [], "seed_history": [], "seed_fixtures": []}, "seed_mapping": base["seed_mapping"]}
    source["tables"]["target_fixtures"] = [{"id": f["id"], "gameweek_id": f["gw"], "home_club_id": f["home_club"], "away_club_id": f["away_club"], "team_h_difficulty": 3, "team_a_difficulty": 3} for f in value["origins"][0]["fixtures"]]
    source["tables"]["clubs"] = [{"id": n, "strength": 1000, "short_name": f"C{n}"} for n in (1, 2, 3)]
    source["tables"]["player_metadata"] = [{"id": n, "web_name": f"Player {n}"} for n in (1, 2)]
    source["tables"]["seed_players"] = [{"seed_key": f"s{n}", "id": n, "club_id": n, "position_id": n, "now_cost": 50} for n in (1, 2)]
    source["tables"]["seed_fixtures"] = [{"id": 99, "gameweek_id": 38, "finished": True, "finalized_at": "2024-05-20T00:00:00Z"}]
    source["tables"]["seed_history"] = [{"player_id": 1, "fixture_id": 99, "gameweek_id": 38, "kickoff_time": "2024-05-19T00:00:00Z", "minutes": 90, "total_points": 3}]
    def admit_source() -> tuple[Any, str]:
        source_digest = retain(entries, source)
        base["training_source_digests"] = [source_digest]
        value["authority_digest"] = retain(entries, base)
        for item in value["origins"][0]["sources"]:
            item["parent_manifest"] = value["authority_digest"]
        cap = require_input(value, entries, "test", 1)
        authority = {"version": 2, "mode": "synthetic", "input_digest": cap.input_digest, "season": "test", "gw": 1, "seed_identity": "synthetic-seed", "source_digest": source_digest}
        return cap, retain(entries, authority)

    cap, digest = admit_source()
    assert verify_training_bundle(cap, value, entries, digest) == source
    source["tables"]["history"] = [{"gameweek_id": 1}]
    cap, digest = admit_source()
    with pytest.raises(ValueError, match="History"):
        verify_training_bundle(cap, value, entries, digest)
    source["tables"]["history"] = []
    source["seed_mapping"] = {}
    cap, digest = admit_source()
    with pytest.raises(ValueError, match="mapping"):
        verify_training_bundle(cap, value, entries, digest)
    base["seed_mapping"] = {"1": "s1", "2": "absent:new-player"}
    source["seed_mapping"] = dict(base["seed_mapping"])
    cap, digest = admit_source()
    assert verify_training_bundle(cap, value, entries, digest)["seed_mapping"]["2"] == "absent:new-player"
    base["seed_mapping"]["2"] = "absent:s2"
    source["seed_mapping"] = dict(base["seed_mapping"])
    cap, digest = admit_source()
    with pytest.raises(ValueError, match="proven absent"):
        verify_training_bundle(cap, value, entries, digest)
