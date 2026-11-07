import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from features.season_archive import LiveSeasonPin


@pytest.mark.asyncio
async def test_refresh_data_fetches_player_summaries():
    # Mock data
    mock_bootstrap = {
        "events": [{"id": 1, "is_current": True}],
        "elements": [
            {"id": 101, "web_name": "Player 1"},
            {"id": 102, "web_name": "Player 2"}
        ]
    }
    
    mock_fetch_bootstrap = AsyncMock(return_value=mock_bootstrap)
    mock_fetch_fixtures = AsyncMock(return_value=[])
    mock_fetch_summary = AsyncMock(return_value={"history": []})
    mock_get_jwt = AsyncMock(side_effect=Exception("No auth"))
    mock_process = patch("commands.refresh_data.process_directory")
    
    with patch("commands.refresh_data.fetch_bootstrap_static", mock_fetch_bootstrap), \
         patch("commands.refresh_data.fetch_gameweek_fixtures", mock_fetch_fixtures), \
         patch("commands.refresh_data.fetch_element_summary", mock_fetch_summary), \
         patch("commands.refresh_data.get_jwt_token", mock_get_jwt), \
         mock_process as mock_process_dir, \
         patch("commands.refresh_data.append_price_snapshot") as mock_price_snapshot, \
         patch("commands.refresh_data.prune_stale_element_summaries", return_value=0) as mock_prune, \
         patch("commands.refresh_data.pin_season_archive") as mock_pin:
        mock_pin.return_value = LiveSeasonPin(
            processed_dir=MagicMock(),
            content_hash="abc",
            changed=True,
        )
         
        from commands.refresh_data import main
        await main([])
        
        # Verify that bootstrap and fixtures were called
        mock_fetch_bootstrap.assert_called_once()
        mock_fetch_fixtures.assert_called_once()
        
        # Verify that fetch_element_summary was called for each player
        assert mock_fetch_summary.call_count == 2
        mock_fetch_summary.assert_any_call(mock_fetch_summary.call_args_list[0][0][0], 101, write_cache=True)
        mock_fetch_summary.assert_any_call(mock_fetch_summary.call_args_list[1][0][0], 102, write_cache=True)
        
        # Verify process_directory was called
        mock_process_dir.assert_called_once()
        mock_prune.assert_called_once_with(mock_process_dir.call_args.args[0])
        mock_price_snapshot.assert_called_once()
        mock_pin.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_data_logs_hash_and_does_not_invoke_git(caplog):
    source = Path("commands/refresh_data.py").read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "os.system" not in source
    mock_bootstrap = {"events": [{"id": 1, "is_current": True}], "elements": []}
    pin = LiveSeasonPin(processed_dir=MagicMock(name="processed"), content_hash="deadbeef", changed=False)
    with patch("commands.refresh_data.fetch_bootstrap_static", AsyncMock(return_value=mock_bootstrap)), \
         patch("commands.refresh_data.fetch_gameweek_fixtures", AsyncMock(return_value=[])), \
         patch("commands.refresh_data.get_jwt_token", AsyncMock(side_effect=Exception("No auth"))), \
         patch("commands.refresh_data.process_directory"), \
         patch("commands.refresh_data.append_price_snapshot"), \
         patch("commands.refresh_data.prune_stale_element_summaries", return_value=0), \
         patch("commands.refresh_data.pin_season_archive", return_value=pin), \
         caplog.at_level("INFO"):
        from commands.refresh_data import main
        await main([])
    assert "hash unchanged" in caplog.text
    assert "deadbeef" in caplog.text
    assert "Skip git commit" in caplog.text


@pytest.mark.asyncio
async def test_refresh_data_concurrency_and_milestones(caplog: pytest.LogCaptureFixture) -> None:
    mock_bootstrap = {
        "events": [{"id": 1, "is_current": True}],
        "elements": [{"id": i, "web_name": f"P{i}"} for i in range(1, 205)],
    }
    pin = LiveSeasonPin(processed_dir=MagicMock(name="processed"), content_hash="beef", changed=False)
    with patch("commands.refresh_data.fetch_bootstrap_static", AsyncMock(return_value=mock_bootstrap)), \
         patch("commands.refresh_data.fetch_gameweek_fixtures", AsyncMock(return_value=[])), \
         patch("commands.refresh_data.fetch_element_summary", AsyncMock(return_value={"history": []})) as mock_summary, \
         patch("commands.refresh_data.get_jwt_token", AsyncMock(side_effect=Exception("No auth"))), \
         patch("commands.refresh_data.process_directory"), \
         patch("commands.refresh_data.append_price_snapshot"), \
         patch("commands.refresh_data.prune_stale_element_summaries", return_value=0), \
         patch("commands.refresh_data.pin_season_archive", return_value=pin), \
         caplog.at_level("INFO"):
        from commands.refresh_data import main
        await main(["--concurrency", "25"])

    assert mock_summary.call_count == 204
    assert "concurrency limit = 25" in caplog.text
    assert "Progress: fetched 100/204" in caplog.text
    assert "Progress: fetched 200/204" in caplog.text
    assert "Progress: fetched 204/204" in caplog.text
    assert "Fetched 204 player summaries in" in caplog.text


@pytest.mark.asyncio
async def test_refresh_data_unauthenticated_with_entry_id(tmp_path: Path) -> None:
    mock_bootstrap = {
        "events": [{"id": 1, "is_current": True, "deadline_time": "2026-08-01T12:00:00Z", "finished": True}],
        "elements": [{"id": 10, "web_name": "Salah", "now_cost": 125}],
    }
    mock_entry_summary = {"player_first_name": "Test", "player_last_name": "User", "name": "Test Team"}
    mock_entry_history = {
        "chips": [{"name": "wildcard"}],
        "current": [{"event": 1, "event_transfers": 1, "event_transfers_cost": 0}],
    }
    mock_picks = {
        "picks": [{"element": 10, "position": 1, "multiplier": 1, "is_captain": True, "is_vice_captain": False}],
        "entry_history": {"bank": 15, "value": 1000},
    }
    mock_transfers = [{"element_in": 10, "element_in_cost": 120, "time": "2026-08-01T10:00:00Z"}]
    pin = LiveSeasonPin(processed_dir=MagicMock(), content_hash="abc", changed=False)

    with patch("commands.refresh_data.fetch_bootstrap_static", AsyncMock(return_value=mock_bootstrap)), \
         patch("commands.refresh_data.fetch_gameweek_fixtures", AsyncMock(return_value=[])), \
         patch("commands.refresh_data.fetch_element_summary", AsyncMock(return_value={"history": []})), \
         patch("commands.refresh_data.get_jwt_token", AsyncMock(side_effect=Exception("No auth"))), \
         patch("commands.refresh_data.fetch_entry_summary", AsyncMock(return_value=mock_entry_summary)) as mock_summary, \
         patch("commands.refresh_data.fetch_entry_history", AsyncMock(return_value=mock_entry_history)) as mock_hist, \
         patch("commands.refresh_data.fetch_gameweek_picks", AsyncMock(return_value=mock_picks)) as mock_pk, \
         patch("commands.refresh_data.fetch_entry_transfers", AsyncMock(return_value=mock_transfers)) as mock_tr, \
         patch("commands.refresh_data.process_directory"), \
         patch("commands.refresh_data.append_price_snapshot"), \
         patch("commands.refresh_data.prune_stale_element_summaries", return_value=0), \
         patch("commands.refresh_data.pin_season_archive", return_value=pin), \
         patch("commands.refresh_data.PROJECT_ROOT", tmp_path):
        from commands.refresh_data import main
        await main(["--entry-id", "9999"])

        mock_summary.assert_called_once()
        mock_hist.assert_called_once()
        mock_pk.assert_called_once()
        mock_tr.assert_called_once()

        team_file = tmp_path / "data" / "raw" / "my_team_9999.json"
        assert team_file.exists()


def test_reconstruct_public_team_payload_prices_chips_and_ft_bank() -> None:
    from commands.refresh_data import reconstruct_public_team_payload

    elements = {
        1: {"id": 1, "now_cost": 85, "cost_change_start": 5},  # Owned since GW1 (bought at 80, sell at 82)
        2: {"id": 2, "now_cost": 100, "cost_change_start": 10},  # Bought in transfer at 96 (sell at 98)
    }
    picks_data = {
        "picks": [
            {"element": 1, "position": 1, "multiplier": 1, "is_captain": False, "is_vice_captain": False},
            {"element": 2, "position": 2, "multiplier": 2, "is_captain": True, "is_vice_captain": False},
        ],
        "entry_history": {"bank": 10, "value": 1020},
    }
    history = {
        "chips": [{"name": "wildcard", "event": 3}],
        "current": [
            {"event": 1, "event_transfers": 0, "event_transfers_cost": 0},  # FT: 1 -> 2
            {"event": 2, "event_transfers": 0, "event_transfers_cost": 0},  # FT: 2 -> 3
            {"event": 3, "event_transfers": 8, "event_transfers_cost": 0},  # WC played! FT preserved at 3
        ],
    }
    transfers_history = [
        {"element_in": 2, "element_in_cost": 96, "time": "2026-09-01T10:00:00Z"},
    ]

    payload = reconstruct_public_team_payload(picks_data, history, transfers_history, elements)

    p1 = next(p for p in payload["picks"] if p["element"] == 1)
    assert p1["purchase_price"] == 80
    assert p1["selling_price"] == 82

    p2 = next(p for p in payload["picks"] if p["element"] == 2)
    assert p2["purchase_price"] == 96
    assert p2["selling_price"] == 98

    # FT bank preserved across WC in GW3 (remained 3)
    assert payload["transfers"]["limit"] == 3
    assert payload["transfers"]["bank"] == 10

    # Chips have both Set 1 (1-19) and Set 2 (20-38); WC played in Set 1, available in Set 2
    chips = payload["chips"]
    assert len(chips) == 8
    wc_set1 = next(c for c in chips if c["name"] == "wildcard" and c["chip_set"] == 1)
    wc_set2 = next(c for c in chips if c["name"] == "wildcard" and c["chip_set"] == 2)
    assert wc_set1["status"] == "played"
    assert wc_set2["status"] == "available"


