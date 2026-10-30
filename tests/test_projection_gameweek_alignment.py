"""Changed fixture calendars are scored against complete native target-GW sources."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backtesting.data_admission import require_admitted, require_input
from backtesting.forecast_store import generate_forecast
from backtesting.promotion_evidence import GUARD_SEMANTICS, finalized_gameweek_outcomes, group_projection_gameweeks
from promotion_evidence_fixture import CANDIDATE, _context
from test_data_admission import RETAINED, authorize, catalog, rehash
from test_forecast_inputs import retain


def _blank_target(context: tuple[dict[str, Any], dict[str, bytes], str], target: int) -> tuple[dict[str, Any], dict[str, bytes], str]:
    request, entries, training_authority = context
    origin = request["origins"][0]
    origin["fixtures"] = [fixture for fixture in origin["fixtures"] if fixture["gw"] != target]
    origin["fixture_events"] = [event for event in origin["fixture_events"] if event["gw"] != target]
    origin["outcomes"] = [outcome for outcome in origin["outcomes"] if outcome["gw"] != target]
    for row in origin["schedule"]:
        if row["gw"] == target:
            row.update(status="blank", fixture=None)
    RETAINED.update(entries)
    rehash(request)
    authorize(request)
    entries.update(catalog(request))
    authority = json.loads(entries[request["authority_digest"]])
    training_record = json.loads(entries[training_authority])
    training = json.loads(entries[training_record["source_digest"]])
    training["tables"]["target_fixtures"] = [fixture for fixture in training["tables"]["target_fixtures"] if fixture["gameweek_id"] != target]
    training_digest = retain(entries, training)
    authority["training_source_digests"] = [training_digest]
    request["authority_digest"] = retain(entries, authority)
    for source in origin["sources"]:
        source["parent_manifest"] = request["authority_digest"]
    capability = require_input(request, entries, origin["season"], origin["gw"])
    training_record.update(input_digest=capability.input_digest, source_digest=training_digest)
    training_authority = retain(entries, training_record)
    require_admitted(request, entries, origin["season"], origin["gw"])
    return request, entries, training_authority


@pytest.mark.parametrize("initial_blank", [True, False], ids=["introduced_after_known_blank", "postponed_after_known_fixture"])
def test_complete_target_gameweek_source_controls_guard_outcomes(tmp_path: Path, initial_blank: bool) -> None:
    issue_context = _context("2024-25", 1)
    target_context = _context("2024-25", 3)
    if initial_blank:
        issue_context = _blank_target(issue_context, 3)
    else:
        target_context = _blank_target(target_context, 3)
    request, entries, training_authority = issue_context
    capability = require_input(request, entries, "2024-25", 1)
    _, predictions, _ = generate_forecast(tmp_path / "forecast-cache", capability, request, entries, training_authority, CANDIDATE)
    target_request, target_entries, _ = target_context
    require_admitted(target_request, target_entries, "2024-25", 3)
    specification = {"guard_specs": {name: {"outcome_field": fields[1]} for name, fields in GUARD_SEMANTICS.items()}}
    observed = finalized_gameweek_outcomes(target_request["origins"][0], specification)
    target_predictions = pd.DataFrame(predictions.loc[predictions["gameweek_id"] == 3])
    rows = group_projection_gameweeks(target_predictions, "2024-25", 1, observed)
    assert len(rows) == 15
    if initial_blank:
        assert all(row["projected_points"] == 0.0 for row in rows)
        assert all(row["_observed"]["actual_points"] == 2.0 for row in rows)
    else:
        assert any(row["projected_points"] > 0.0 for row in rows)
        assert all(row["_observed"]["actual_points"] == 0.0 for row in rows)


def test_missing_target_player_evidence_never_becomes_zero() -> None:
    rows = [{"player_id": 1, "gameweek_id": 3, "projected_points": 0.0, "projected_minutes": 0.0, **{fields[0]: 0.0 for fields in GUARD_SEMANTICS.values() if fields[0].startswith("xp_")}}]
    with pytest.raises(ValueError, match="Missing complete finalized"):
        group_projection_gameweeks(pd.DataFrame(rows), "2024-25", 1, {})
