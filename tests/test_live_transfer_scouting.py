import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import pytest

from commands import injury_triage
from commands.transfer_scouting import POSITIONS, QUOTAS, load_events, recent_roles, review_queue


def test_sourced_replacement_enters_its_position_quota_with_zero_points() -> None:
    source_candidate = 199
    rows = [
        dict(id=position * 100 + i, position_id=position, projected_points=60 - i,
             club_id=position, web_name=f"player {position}-{i}", now_cost=45, status="a",
             next_minutes=70, next_gw=4, short=12)
        for position in QUOTAS for i in range(1, 14)
    ]
    rows.append({**rows[0], "id": source_candidate, "projected_points": 0, "next_minutes": 0})
    market = pd.DataFrame(rows).set_index("id")
    events = {source_candidate: [{"kind": "replacement", "detail": "Direct starter unavailable"}]}
    current = review_queue(market, pd.DataFrame(), events, position_quotas=True)
    baseline = review_queue(market, pd.DataFrame(), {}, position_quotas=False)
    assert len({row["player_id"] for row in current}) == 30
    assert len({row["player_id"] for row in baseline}) == 18
    assert {position: sum(row["position"] == position for row in current) for position in POSITIONS.values()} == {
        POSITIONS[pos]: n for pos, n in QUOTAS.items()
    }
    assert current[0]["player_id"] == source_candidate
    assert current[0]["reason"] == "role_evidence"
    assert current[0]["next_xmins"] == 0
    assert not any(row["player_id"] == source_candidate for row in baseline)


def test_role_receipts_require_published_and_relevant_evidence(tmp_path: Path) -> None:
    path = tmp_path / "role.json"
    event = dict(player_id=5, kind="replacement", source="https://example.test/team-news",
                 published_at="2026-11-20T10:00:00Z", first_gw=12, last_gw=12, detail="Fixture-scoped lead")
    path.write_text(json.dumps([
        event, {**event, "player_id": 6, "published_at": "2026-11-28T10:00:00Z"},
        {**event, "player_id": 7, "first_gw": 10, "last_gw": 11},
        {**event, "player_id": 8, "first_gw": 16, "last_gw": 17},
    ]), encoding="utf-8")
    cutoff = pd.Timestamp("2026-11-26T12:00:00Z")
    assert load_events(path, cutoff, 12, 4) == {5: [event]}
    path.write_text(json.dumps([{**event, "source": "file:///local"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid role receipt"):
        load_events(path, cutoff, 12, 4)
    for invalid_impact in (-1, 91, "30", True):
        path.write_text(json.dumps([{**event, "minutes_impact": invalid_impact}]), encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid role receipt"):
            load_events(path, cutoff, 12, 4)


def test_review_queue_prioritizes_sourced_minutes_impact_then_projection_order() -> None:
    market = pd.DataFrame([
        dict(id=pid, position_id=1, projected_points=points, club_id=1, web_name=f"GK {pid}",
             now_cost=45, status="a", next_minutes=0, next_gw=0, short=0)
        for pid, points in ((1, 12), (2, 10), (3, 8), (4, 0), (5, 0))
    ]).set_index("id")
    events = {
        5: [{"minutes_impact": 10}, {"minutes_impact": 75}],
        4: [{"minutes_impact": 45}],
        3: [{"minutes_impact": 45}],
    }
    result = review_queue(market, pd.DataFrame(), events, position_quotas=True)
    assert [row["player_id"] for row in result] == [5, 3, 4, 1]
    assert [row["reason"] for row in result] == ["role_evidence"] * 3 + ["points"]


def test_minutes_sensitivity_flags_a_first_start_for_review() -> None:
    history = pd.DataFrame([
        {"player_id": 5, "gameweek_id": week, "fixture_id": week, "kickoff_time": f"2026-11-{week}",
         "minutes": minutes, "starts": start}
        for week, minutes, start in ((8, 0, 0), (9, 15, 0), (10, 82, 1))
    ])
    roles = recent_roles(history, pd.Series({5: 30}), 11)
    assert roles.loc[5, "signal"] == "more_minutes"
    assert roles.loc[5, "recent_starts"] == 1
    assert roles.loc[5, "target"] == 82


def test_set_gw_keeps_other_weeks_sparse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[tuple[int, int], float] = {}
    pd.DataFrame({"id": [12]}).to_parquet(tmp_path / "gameweeks.parquet")

    def synthesize(**options: Any) -> Path:
        seen.update(options["targeted_overrides"])
        return options["output_path"]

    monkeypatch.setattr(injury_triage, "resolve_operational_processed_dir", lambda _: tmp_path)
    monkeypatch.setattr(injury_triage, "build_broad_pool_shield", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(injury_triage, "select_scouting_targets", lambda *_args, **_kwargs: {
        "squad_flagged": [], "squad_rotation_risk": [], "market_flagged_by_tier": {},
    })
    monkeypatch.setattr(injury_triage, "synthesize_xmins_override", synthesize)
    args = ["injury_triage", "--target_gw", "12", "--horizon", "4", "--set", "3:20,40",
            "--set-gw", "5:14:65", "--json"]
    monkeypatch.setattr(sys, "argv", args)
    injury_triage.main()
    assert seen == {(3, 12): 20, (3, 13): 40, (5, 14): 65}
    monkeypatch.setattr(sys, "argv", [*args, "--set-gw", "5:17:65"])
    with pytest.raises(SystemExit, match="2"):
        injury_triage.main()
