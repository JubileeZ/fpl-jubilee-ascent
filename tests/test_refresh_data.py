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
         patch("commands.refresh_data.pin_season_archive", return_value=pin), \
         caplog.at_level("INFO"):
        from commands.refresh_data import main
        await main([])
    assert "hash unchanged" in caplog.text
    assert "deadbeef" in caplog.text
    assert "Skip git commit" in caplog.text
