from pathlib import Path

import pandas as pd

from commands.snapshot_season import main
from features.vaastav_archive import process_vaastav_directory


def _write_vaastav_dir(root: Path) -> Path:
    gw = root / "gws"
    gw.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "id": 1,
                "code": 101,
                "first_name": "Bukayo",
                "second_name": "Saka",
                "web_name": "Saka",
                "team": 1,
                "element_type": 3,
                "now_cost": 100,
                "status": "a",
            }
        ]
    ).to_csv(root / "players_raw.csv", index=False)
    pd.DataFrame(
        [
            {
                "id": 1,
                "name": "Arsenal",
                "short_name": "ARS",
                "strength": 5,
                "strength_overall_home": 1350,
                "strength_overall_away": 1350,
                "strength_attack_home": 1390,
                "strength_attack_away": 1400,
                "strength_defence_home": 1310,
                "strength_defence_away": 1300,
            }
        ]
    ).to_csv(root / "teams.csv", index=False)
    pd.DataFrame(
        [
            {
                "id": 9,
                "event": 1,
                "kickoff_time": "2024-08-17T14:00:00Z",
                "team_h": 1,
                "team_a": 2,
                "finished": True,
                "started": True,
                "team_h_score": 2,
                "team_a_score": 0,
                "team_h_difficulty": 2,
                "team_a_difficulty": 4,
            }
        ]
    ).to_csv(root / "fixtures.csv", index=False)
    pd.DataFrame(
        [
            {
                "element": 1,
                "fixture": 9,
                "round": 1,
                "GW": 1,
                "opponent_team": 2,
                "was_home": True,
                "kickoff_time": "2024-08-17T14:00:00Z",
                "team_h_score": 2,
                "team_a_score": 0,
                "value": 100,
                "selected": 10,
                "transfers_balance": 0,
                "transfers_in": 0,
                "transfers_out": 0,
                "minutes": 90,
                "total_points": 8,
                "goals_scored": 1,
                "assists": 0,
                "clean_sheets": 1,
                "goals_conceded": 0,
                "own_goals": 0,
                "penalties_saved": 0,
                "penalties_missed": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "saves": 0,
                "bonus": 3,
                "bps": 30,
                "influence": 40.0,
                "creativity": 12.0,
                "threat": 20.0,
                "ict_index": 7.0,
                "starts": 1,
                "expected_goals": 0.4,
                "expected_assists": 0.1,
                "expected_goal_involvements": 0.5,
                "expected_goals_conceded": 0.8,
            }
        ]
    ).to_csv(gw / "merged_gw.csv", index=False)
    return root


def test_vaastav_dir_writes_seed_parquets(tmp_path: Path) -> None:
    src = _write_vaastav_dir(tmp_path / "vaastav")
    out = tmp_path / "processed"
    process_vaastav_directory(src, out)
    players = pd.read_parquet(out / "players.parquet")
    performances = pd.read_parquet(out / "player_performances.parquet")
    assert int(players.loc[0, "id"]) == 1
    assert int(players.loc[0, "code"]) == 101
    assert int(players.loc[0, "club_id"]) == 1
    assert int(players.loc[0, "position_id"]) == 3
    assert int(performances.loc[0, "player_id"]) == 1
    assert int(performances.loc[0, "fixture_id"]) == 9
    assert int(performances.loc[0, "gameweek_id"]) == 1
    assert int(performances.loc[0, "minutes"]) == 90
    assert int(performances.loc[0, "starts"]) == 1
    assert int(performances.loc[0, "price"]) == 100
    assert "defensive_contribution" not in performances.columns
    clubs = pd.read_parquet(out / "clubs.parquet")
    assert clubs.loc[0, "short_name"] == "ARS"
    fixtures = pd.read_parquet(out / "fixtures.parquet")
    assert int(fixtures.loc[0, "home_club_id"]) == 1


def test_cli_from_vaastav_dir(tmp_path: Path) -> None:
    src = _write_vaastav_dir(tmp_path / "vaastav")
    archive_root = tmp_path / "archive"
    assert main(
        ["--season", "2024-25", "--from-vaastav-dir", str(src), "--archive-root", str(archive_root)]
    ) == 0
    assert (archive_root / "2024-25" / "processed" / "player_performances.parquet").exists()
