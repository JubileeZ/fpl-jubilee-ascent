import pandas as pd
import pytest
from unittest.mock import patch
from commands.solve import build_my_data_from_parquet, main, validate_booked_chips
from solver.utils import load_settings

def test_build_my_data_from_parquet(tmp_path):
    # 1. Create mock processed tables
    df_picks = pd.DataFrame([
        {"player_id": 101, "purchase_price": 95, "selling_price": 98, "lineup_index": 1, "multiplier": 1, "is_captain": False, "is_vice_captain": False}
    ])
    df_picks.to_parquet(tmp_path / "user_picks.parquet")
    
    df_state = pd.DataFrame([
        {"entry_id": 12345, "bank": 15, "free_transfers": 2, "value": 1000, "active_chip": None}
    ])
    df_state.to_parquet(tmp_path / "user_state.parquet")
    
    df_players = pd.DataFrame([
        {"id": 101, "position_id": 3}
    ])
    df_players.to_parquet(tmp_path / "players.parquet")
    
    # 2. Build my_data dict
    my_data = build_my_data_from_parquet(tmp_path)
    
    assert my_data["team_id"] == 12345
    assert my_data["transfers"]["bank"] == 15
    assert my_data["transfers"]["limit"] == 2
    assert len(my_data["picks"]) == 1
    assert my_data["picks"][0]["element"] == 101
    assert my_data["picks"][0]["selling_price"] == 98
    assert my_data["picks"][0]["element_type"] == 3

def test_build_my_data_with_unlimited_transfers(tmp_path):
    # 1. Create mock processed tables
    df_picks = pd.DataFrame([
        {"player_id": 101, "purchase_price": 95, "selling_price": 98, "lineup_index": 1, "multiplier": 1, "is_captain": False, "is_vice_captain": False}
    ])
    df_picks.to_parquet(tmp_path / "user_picks.parquet")
    
    df_state = pd.DataFrame([
        {"entry_id": 12345, "bank": 15, "free_transfers": None, "value": 1000, "active_chip": None}
    ])
    df_state.to_parquet(tmp_path / "user_state.parquet")
    
    df_players = pd.DataFrame([
        {"id": 101, "position_id": 3}
    ])
    df_players.to_parquet(tmp_path / "players.parquet")
    
    # 2. Build my_data dict
    my_data = build_my_data_from_parquet(tmp_path)
    
    assert my_data["transfers"]["limit"] is None


def test_validate_booked_chips_accepts_one_chip_per_gameweek():
    validate_booked_chips(
        {"use_wc": [3], "use_bb": [4], "use_fh": [], "use_tc": []},
        next_gw=2,
        horizon=3,
    )


def test_validate_booked_chips_rejects_duplicate_chip():
    with pytest.raises(ValueError, match="booked more than once"):
        validate_booked_chips(
            {"use_wc": [3, 3], "use_bb": [], "use_fh": [], "use_tc": []},
            next_gw=2,
            horizon=3,
        )


def test_validate_booked_chips_rejects_conflict_and_out_of_horizon():
    with pytest.raises(ValueError, match="at most one chip"):
        validate_booked_chips(
            {"use_wc": [3], "use_bb": [3], "use_fh": [], "use_tc": []},
            next_gw=2,
            horizon=3,
        )
    with pytest.raises(ValueError, match="outside planning horizon"):
        validate_booked_chips(
            {"use_wc": [6], "use_bb": [], "use_fh": [], "use_tc": []},
            next_gw=2,
            horizon=3,
        )

def test_solve_cli_prints_summary(capsys):
    mock_settings = {"datasource": "linear_baseline", "horizon": 5, "preseason": True}
    mock_solutions = [{"summary": "Mock recommended transfers and lineups", "statistics": {}, "picks": pd.DataFrame()}]
    
    with patch("commands.solve.load_settings", return_value=mock_settings), \
         patch("commands.solve.prep_data", return_value={}), \
         patch("commands.solve.solve_multi_period_fpl", return_value=mock_solutions), \
         patch("sys.argv", ["commands.solve", "--preseason"]):
         
        main()
        
        captured = capsys.readouterr()
        assert "RECOMMENDED SQUAD & TRANSFER PLAN" in captured.out
        assert "Mock recommended transfers and lineups" in captured.out



def test_load_settings_uses_participation_state_as_default(tmp_path, monkeypatch):
    monkeypatch.setattr("solver.utils.DATA_DIR", tmp_path)

    assert load_settings()["datasource"] == "participation_state_hybrid"
