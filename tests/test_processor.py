import json
from pathlib import Path
import pandas as pd
import pytest
from features.processor import process_directory

def test_process_directory(tmp_path):
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    input_dir.mkdir()
    
    # Mock bootstrap static data
    bootstrap_data = {
        "teams": [
            {"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}
        ],
        "events": [
            {"id": 1, "name": "Gameweek 1", "deadline_time": "2026-08-11T17:30:00Z", "finished": True, "is_current": True, "is_next": False}
        ],
        "elements": [
            {"id": 1, "code": 99, "first_name": "Martin", "second_name": "Odegaard", "web_name": "Odegaard", "team": 1, "element_type": 3, "now_cost": 85, "status": "a"}
        ]
    }
    with open(input_dir / "bootstrap_static.json", "w") as f:
        json.dump(bootstrap_data, f)
        
    # Mock fixtures data
    fixtures_data = [
        {"id": 1, "event": 1, "kickoff_time": "2026-08-11T19:00:00Z", "team_h": 1, "team_a": 2, "finished": True, "started": True, "team_h_score": 2, "team_a_score": 1, "team_h_difficulty": 3, "team_a_difficulty": 4}
    ]
    with open(input_dir / "fixtures_all.json", "w") as f:
        json.dump(fixtures_data, f)
        
    # Process
    process_directory(input_dir, output_dir)
    
    # Check outputs
    assert (output_dir / "clubs.parquet").exists()
    assert (output_dir / "gameweeks.parquet").exists()
    assert (output_dir / "players.parquet").exists()
    assert (output_dir / "fixtures.parquet").exists()
    
    # Verify contents
    df_clubs = pd.read_parquet(output_dir / "clubs.parquet")
    assert len(df_clubs) == 1
    assert df_clubs.loc[0, "name"] == "Arsenal"
    
    df_players = pd.read_parquet(output_dir / "players.parquet")
    assert len(df_players) == 1
    assert df_players.loc[0, "club_id"] == 1
    assert df_players.loc[0, "position_id"] == 3
    df_fix = pd.read_parquet(output_dir / "fixtures.parquet")
    assert bool(df_fix.loc[0, "finished"]) is True


def test_process_directory_skips_summaries_for_players_not_in_bootstrap(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw"
    input_dir.mkdir()
    bootstrap = {
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [{"id": 1, "name": "Gameweek 1", "finished": True, "is_current": True, "is_next": False}],
        "elements": [{"id": 1, "code": 99, "web_name": "Odegaard", "team": 1, "element_type": 3, "now_cost": 85, "status": "a"}],
    }
    (input_dir / "bootstrap_static.json").write_text(json.dumps(bootstrap))
    for player_id in (1, 900):
        history = [{"element": player_id, "fixture": 1, "round": 1, "opponent_team": 2, "minutes": 90, "total_points": 2}]
        (input_dir / f"element_summary_{player_id}.json").write_text(json.dumps({"history": history}))

    process_directory(input_dir, tmp_path / "processed")

    df_perf = pd.read_parquet(tmp_path / "processed" / "player_performances.parquet")
    assert df_perf["player_id"].tolist() == [1]


def test_process_directory_sorts_player_summaries_deterministically(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw"
    input_dir.mkdir()
    bootstrap = {
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [{"id": 1, "name": "Gameweek 1", "finished": True, "is_current": True, "is_next": False}],
        "elements": [
            {"id": pid, "code": pid, "web_name": f"P{pid}", "team": 1, "element_type": 3, "now_cost": 50, "status": "a"}
            for pid in (10, 2, 100, 1)
        ],
    }
    (input_dir / "bootstrap_static.json").write_text(json.dumps(bootstrap))
    for pid in (10, 2, 100, 1):
        history = [{"element": pid, "fixture": 1, "round": 1, "opponent_team": 2, "minutes": 90, "total_points": 2}]
        (input_dir / f"element_summary_{pid}.json").write_text(json.dumps({"history": history}))

    process_directory(input_dir, tmp_path / "processed")

    df_perf = pd.read_parquet(tmp_path / "processed" / "player_performances.parquet")
    assert df_perf["player_id"].tolist() == [1, 2, 10, 100]



def test_process_directory_writes_user_chips(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    input_dir.mkdir()
    with open(input_dir / "bootstrap_static.json", "w") as f:
        json.dump({
            "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
            "events": [{"id": 1, "name": "Gameweek 1", "deadline_time": "2026-08-11T17:30:00Z", "finished": True, "is_current": True, "is_next": False}],
            "elements": [{"id": 1, "code": 99, "first_name": "Martin", "second_name": "Odegaard", "web_name": "Odegaard", "team": 1, "element_type": 3, "now_cost": 85, "status": "a"}],
        }, f)
    with open(input_dir / "fixtures_all.json", "w") as f:
        json.dump([{
            "id": 1, "event": 1, "kickoff_time": "2026-08-11T19:00:00Z", "team_h": 1, "team_a": 2,
            "finished": True, "started": True, "team_h_score": 2, "team_a_score": 1,
            "team_h_difficulty": 3, "team_a_difficulty": 4,
        }], f)
    with open(input_dir / "my_team_123.json", "w") as f:
        json.dump({
            "picks": [{"element": 1, "position": 1, "multiplier": 1, "is_vice_captain": False, "purchase_price": 80, "selling_price": 80}],
            "transfers": {"bank": 10, "value": 1000, "limit": 1},
            "chips": [
                {"name": "wildcard", "status": "available", "start_event": 1, "stop_event": 19, "number": 1},
                {"name": "bboost", "status": "played", "start_event": 1, "stop_event": 19, "number": 1},
            ],
        }, f)
    process_directory(input_dir, output_dir)
    chips = pd.read_parquet(output_dir / "user_chips.parquet")
    assert set(chips["chip"]) == {"wc", "bb"}
    bb = chips.loc[chips["chip"] == "bb"].iloc[0]
    assert bb["status"] == "played"
    assert int(bb["chip_set"]) == 1


def test_process_directory_rejects_players_without_code(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    input_dir.mkdir()
    (input_dir / "bootstrap_static.json").write_text(json.dumps({
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [{"id": 1, "name": "Gameweek 1", "deadline_time": "2026-08-11T17:30:00Z", "finished": True, "is_current": True, "is_next": False}],
        "elements": [{"id": 1, "first_name": "A", "second_name": "B", "web_name": "AB", "team": 1, "element_type": 3, "now_cost": 50, "status": "a"}],
    }), encoding="utf-8")
    (input_dir / "fixtures_all.json").write_text(json.dumps([{
        "id": 1, "event": 1, "kickoff_time": "2026-08-11T19:00:00Z", "team_h": 1, "team_a": 2,
        "finished": True, "started": True, "team_h_score": 2, "team_a_score": 1,
        "team_h_difficulty": 3, "team_a_difficulty": 4,
    }]), encoding="utf-8")
    from features.contracts import ContractError
    with pytest.raises(ContractError, match="players missing columns: code"):
        process_directory(input_dir, output_dir)


def test_process_directory_keeps_player_code(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    input_dir.mkdir()
    (input_dir / "bootstrap_static.json").write_text(json.dumps({
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [{"id": 1, "name": "Gameweek 1", "deadline_time": "2026-08-11T17:30:00Z", "finished": True, "is_current": True, "is_next": False}],
        "elements": [{"id": 1, "code": 424242, "first_name": "A", "second_name": "B", "web_name": "AB", "team": 1, "element_type": 3, "now_cost": 50, "status": "a"}],
    }), encoding="utf-8")
    (input_dir / "fixtures_all.json").write_text(json.dumps([{
        "id": 1, "event": 1, "kickoff_time": "2026-08-11T19:00:00Z", "team_h": 1, "team_a": 2,
        "finished": True, "started": True, "team_h_score": 2, "team_a_score": 1,
        "team_h_difficulty": 3, "team_a_difficulty": 4,
    }]), encoding="utf-8")
    process_directory(input_dir, output_dir)
    players = pd.read_parquet(output_dir / "players.parquet")
    assert int(players.loc[0, "code"]) == 424242


def test_process_directory_reconstructs_active_chip_ft_and_stores_limit_made(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    input_dir.mkdir()
    (input_dir / "bootstrap_static.json").write_text(json.dumps({
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [{"id": 1, "name": "Gameweek 1", "deadline_time": "2026-08-11T17:30:00Z", "finished": True, "is_current": True, "is_next": False}],
        "elements": [{"id": 1, "code": 99, "first_name": "A", "second_name": "B", "web_name": "AB", "team": 1, "element_type": 3, "now_cost": 50, "status": "a"}],
    }), encoding="utf-8")
    (input_dir / "fixtures_all.json").write_text(json.dumps([{
        "id": 1, "event": 1, "kickoff_time": "2026-08-11T19:00:00Z", "team_h": 1, "team_a": 2,
        "finished": True, "started": True, "team_h_score": 2, "team_a_score": 1,
        "team_h_difficulty": 3, "team_a_difficulty": 4,
    }]), encoding="utf-8")
    (input_dir / "me.json").write_text(json.dumps({"player": {"entry": 123}}), encoding="utf-8")
    (input_dir / "entry_history_123.json").write_text(json.dumps({
        "chips": [],
        "current": [
            {"event": 1, "event_transfers": 0, "event_transfers_cost": 0},
            {"event": 2, "event_transfers": 0, "event_transfers_cost": 0},
        ],
    }), encoding="utf-8")
    (input_dir / "my_team_123.json").write_text(json.dumps({
        "picks": [{"element": 1, "position": 1, "multiplier": 1, "is_vice_captain": False, "purchase_price": 50, "selling_price": 50}],
        "transfers": {"bank": 10, "value": 1000, "limit": None, "made": 3},
        "chips": [{"name": "freehit", "status_for_entry": "active", "start_event": 1, "stop_event": 19, "number": 1}],
    }), encoding="utf-8")

    process_directory(input_dir, output_dir)
    state = pd.read_parquet(output_dir / "user_state.parquet").iloc[0]
    assert int(state["free_transfers"]) == 3
    assert int(state["free_transfers_limit"]) == 3
    assert int(state["transfers_made"]) == 0
    assert state["active_chip"] == "freehit"

    # Normal week with limit=2, made=1 preserves limit and made separately
    (input_dir / "my_team_123.json").write_text(json.dumps({
        "picks": [{"element": 1, "position": 1, "multiplier": 1, "is_vice_captain": False, "purchase_price": 50, "selling_price": 50}],
        "transfers": {"bank": 10, "value": 1000, "limit": 2, "made": 1},
        "chips": [],
    }), encoding="utf-8")
    process_directory(input_dir, output_dir)
    state_normal = pd.read_parquet(output_dir / "user_state.parquet").iloc[0]
    assert int(state_normal["free_transfers"]) == 1
    assert int(state_normal["free_transfers_limit"]) == 2
    assert int(state_normal["transfers_made"]) == 1


def test_process_directory_parses_status_for_entry_and_backfills_set_2(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    input_dir.mkdir()
    bs_chips = [
        {"name": "wildcard", "number": 1, "start_event": 2, "stop_event": 19},
        {"name": "freehit", "number": 1, "start_event": 2, "stop_event": 19},
        {"name": "wildcard", "number": 1, "start_event": 20, "stop_event": 38},
        {"name": "freehit", "number": 1, "start_event": 20, "stop_event": 38},
    ]
    (input_dir / "bootstrap_static.json").write_text(json.dumps({
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [{"id": 11, "name": "Gameweek 11", "deadline_time": "2026-11-21T11:00:00Z", "finished": True, "is_current": True, "is_next": False}],
        "elements": [{"id": 1, "code": 99, "first_name": "A", "second_name": "B", "web_name": "AB", "team": 1, "element_type": 3, "now_cost": 50, "status": "a"}],
        "chips": bs_chips,
    }), encoding="utf-8")
    (input_dir / "fixtures_all.json").write_text(json.dumps([{
        "id": 1, "event": 11, "kickoff_time": "2026-11-21T15:00:00Z", "team_h": 1, "team_a": 2,
        "finished": True, "started": True, "team_h_score": 1, "team_a_score": 0,
        "team_h_difficulty": 3, "team_a_difficulty": 4,
    }]), encoding="utf-8")
    (input_dir / "my_team_123.json").write_text(json.dumps({
        "picks": [{"element": 1, "position": 1, "multiplier": 1, "is_vice_captain": False, "purchase_price": 50, "selling_price": 50}],
        "transfers": {"bank": 10, "value": 1000, "limit": 1},
        "chips": [
            {"name": "wildcard", "status_for_entry": "played", "start_event": 2, "stop_event": 19, "number": 1},
            {"name": "freehit", "status_for_entry": "available", "start_event": 2, "stop_event": 19, "number": 1},
        ],
    }), encoding="utf-8")

    process_directory(input_dir, output_dir)
    chips = pd.read_parquet(output_dir / "user_chips.parquet")
    by_key = {(row["chip"], int(row["chip_set"])): row["status"] for _, row in chips.iterrows()}
    assert by_key[("wc", 1)] == "played"
    assert by_key[("fh", 1)] == "available"
    assert by_key[("wc", 2)] == "available"
    assert by_key[("fh", 2)] == "available"

    # In GW20+ (Set 2), do NOT backfill Set 2 chips from bootstrap if my_team omits them
    (input_dir / "bootstrap_static.json").write_text(json.dumps({
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [{"id": 20, "name": "Gameweek 20", "deadline_time": "2027-01-01T11:00:00Z", "finished": False, "is_current": True, "is_next": False}],
        "elements": [{"id": 1, "code": 99, "first_name": "A", "second_name": "B", "web_name": "AB", "team": 1, "element_type": 3, "now_cost": 50, "status": "a"}],
        "chips": bs_chips,
    }), encoding="utf-8")
    (input_dir / "my_team_123.json").write_text(json.dumps({
        "picks": [{"element": 1, "position": 1, "multiplier": 1, "is_vice_captain": False, "purchase_price": 50, "selling_price": 50}],
        "transfers": {"bank": 10, "value": 1000, "limit": 1},
        "chips": [
            {"name": "freehit", "status_for_entry": "played", "start_event": 20, "stop_event": 38, "number": 1},
        ],
    }), encoding="utf-8")
    process_directory(input_dir, output_dir)
    chips_gw20 = pd.read_parquet(output_dir / "user_chips.parquet")
    assert len(chips_gw20) == 1
    assert chips_gw20.iloc[0]["chip"] == "fh"
    assert int(chips_gw20.iloc[0]["chip_set"]) == 2
    assert chips_gw20.iloc[0]["status"] == "played"

    # Post-season (is_current absent, GW20+ finished=True) must NOT backfill Set 2 chips
    (input_dir / "bootstrap_static.json").write_text(json.dumps({
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 4}],
        "events": [
            {"id": 20, "name": "Gameweek 20", "deadline_time": "2027-01-01T11:00:00Z", "finished": True, "is_current": False, "is_next": False},
            {"id": 38, "name": "Gameweek 38", "deadline_time": "2027-05-25T15:00:00Z", "finished": True, "is_current": False, "is_next": False},
        ],
        "elements": [{"id": 1, "code": 99, "first_name": "A", "second_name": "B", "web_name": "AB", "team": 1, "element_type": 3, "now_cost": 50, "status": "a"}],
        "chips": bs_chips,
    }), encoding="utf-8")
    process_directory(input_dir, output_dir)
    chips_post = pd.read_parquet(output_dir / "user_chips.parquet")
    assert len(chips_post) == 1
    assert int(chips_post.iloc[0]["chip_set"]) == 2
    assert chips_post.iloc[0]["status"] == "played"
